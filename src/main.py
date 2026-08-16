"""
Help Desk AI Agent — FastAPI App Entry Point
Tự động: init DB, seed demo users, seed knowledge base vào ChromaDB
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.routes import router
from src.config import get_settings
from src.observability.telemetry import (
    configure_telemetry,
    instrument_sqlalchemy,
    reset_request_id,
    set_request_id,
    shutdown_telemetry,
)
from src.observability.tracing import current_trace_id, record_http_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


async def _seed_demo_users(db):
    """Tạo demo users nếu chưa có."""
    from sqlalchemy import select

    from src.models.technician_fulfillment_group import TechnicianFulfillmentGroup
    from src.models.user import CompanyUnit, UserRole
    from src.services.auth_service import create_user, get_user_by_username
    from src.services.service_request_service import canonical_fulfillment_groups

    demo_users = [
        {
            "username": "employee1",
            "email": "employee1@corp.example.com",
            "full_name": "Nguyễn Văn An",
            "password": "demo123",
            "role": UserRole.EMPLOYEE,
            "company_unit": CompanyUnit.REAL_ESTATE,
            "department": "Sales",
            "is_vip": False,
        },
        {
            "username": "employee_vip",
            "email": "director@corp.example.com",
            "full_name": "Trần Thị Bích (Giám đốc)",
            "password": "demo123",
            "role": UserRole.EMPLOYEE,
            "company_unit": CompanyUnit.CORPORATE,
            "department": "Executive",
            "is_vip": True,
        },
        {
            "username": "tech1",
            "email": "tech1@corp.example.com",
            "full_name": "Lê Minh Công",
            "password": "demo123",
            "role": UserRole.TECHNICIAN,
            "company_unit": CompanyUnit.CORPORATE,
            "department": "IT Support",
            "is_vip": False,
        },
        {
            "username": "manager1",
            "email": "manager1@corp.example.com",
            "full_name": "Phạm Thị Dung",
            "password": "demo123",
            "role": UserRole.MANAGER,
            "company_unit": CompanyUnit.CORPORATE,
            "department": "IT Management",
            "is_vip": False,
        },
        {
            "username": "admin",
            "email": "admin@corp.example.com",
            "full_name": "System Admin",
            "password": "admin123",
            "role": UserRole.ADMIN,
            "company_unit": CompanyUnit.CORPORATE,
            "department": "IT",
            "is_vip": False,
        },
        {
            "username": "employee_healthcare",
            "email": "nurse1@hospital.example.com",
            "full_name": "Điều dưỡng Hoa",
            "password": "demo123",
            "role": UserRole.EMPLOYEE,
            "company_unit": CompanyUnit.HEALTHCARE,
            "department": "ICU",
            "is_vip": False,
        },
        {
            "username": "employee_auto",
            "email": "sales1@xe.example.com",
            "full_name": "Nhân viên Kinh doanh Xe",
            "password": "demo123",
            "role": UserRole.EMPLOYEE,
            "company_unit": CompanyUnit.AUTOMOTIVE,
            "department": "Showroom",
            "is_vip": False,
        },
    ]

    seeded = 0
    for user_data in demo_users:
        existing = await get_user_by_username(db, user_data["username"])
        if not existing:
            await create_user(db, **user_data)
            seeded += 1

    # The demo technician is explicitly provisioned for every catalog group so
    # sample workflows retain a usable technician. This never grants groups to
    # any other existing or newly-created technician.
    demo_technician = await get_user_by_username(db, "tech1")
    if demo_technician:
        result = await db.execute(
            select(TechnicianFulfillmentGroup.fulfillment_group).where(
                TechnicianFulfillmentGroup.technician_id == demo_technician.id
            )
        )
        missing_groups = set(canonical_fulfillment_groups()) - set(result.scalars())
        db.add_all([
            TechnicianFulfillmentGroup(technician_id=demo_technician.id, fulfillment_group=group)
            for group in sorted(missing_groups)
        ])

    if seeded or demo_technician:
        await db.commit()
        logger.info(f"Seeded {seeded} demo users and explicit tech1 group memberships")


async def _seed_knowledge_base(db):
    """Đồng bộ các KB entry còn thiếu vào SQLite và ChromaDB."""
    from sqlalchemy import select

    from src.data.knowledge_base import get_all_kb_entries
    from src.data.service_request_kb import SERVICE_REQUEST_KB_ENTRY
    from src.models.knowledge_base import KnowledgeBaseEntry
    from src.services.rag_service import (
        get_collection_count,
        get_indexed_document_ids,
        index_document,
    )
    entries = list(get_all_kb_entries()) + [SERVICE_REQUEST_KB_ENTRY]
    indexed_ids = get_indexed_document_ids([entry["id"] for entry in entries])
    logger.info("Syncing %d KB entries; %d already indexed", len(entries), len(indexed_ids))

    for entry_data in entries:
        kb_id = entry_data["id"]
        result = await db.execute(
            select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.chroma_id == kb_id)
        )
        if result.scalar_one_or_none() is None:
            db.add(
                KnowledgeBaseEntry(
                    chroma_id=kb_id,
                    title=entry_data["title"],
                    content=entry_data["content"],
                    solution=entry_data.get("solution"),
                    runbook=entry_data.get("runbook"),
                    category=entry_data["category"],
                    tags=entry_data.get("tags", ""),
                    company_unit=entry_data.get("company_unit"),
                    department=entry_data.get("department"),
                    applicable_to_all=entry_data.get("applicable_to_all", True),
                )
            )

        if kb_id in indexed_ids:
            continue

        # Index vào ChromaDB
        content_for_embedding = f"{entry_data['title']}. {entry_data['content']}"
        if entry_data.get("solution"):
            content_for_embedding += f" Giải pháp: {entry_data['solution']}"

        index_document(
            doc_id=kb_id,
            content=content_for_embedding,
            metadata={
                "title": entry_data["title"],
                "category": entry_data["category"],
                "tags": entry_data.get("tags", ""),
                "solution": entry_data.get("solution", ""),
                "runbook": entry_data.get("runbook", ""),
                "company_unit": entry_data.get("company_unit", "all"),
                "department": entry_data.get("department", ""),
                "applicable_to_all": entry_data.get("applicable_to_all", True),
            },
        )

    await db.commit()
    logger.info(f"KB seeding complete. ChromaDB now has {get_collection_count()} documents")


async def _provision_initial_admin(
    db,
    email: str,
    username: str = "admin",
    password: str = "",
    full_name: str = "System Administrator",
):
    """Tạo tài khoản quản trị viên khởi tạo cho production nếu được cung cấp."""
    from src.models.user import CompanyUnit, UserRole
    from src.services.auth_service import create_user, get_user_by_email, get_user_by_username

    if not email or not password:
        return

    existing_user = await get_user_by_username(db, username)
    existing_email = await get_user_by_email(db, email.lower())
    if not existing_user and not existing_email:
        await create_user(
            db,
            username=username,
            email=email.lower(),
            full_name=full_name,
            password=password,
            role=UserRole.ADMIN,
            company_unit=CompanyUnit.CORPORATE,
            department="IT",
            is_vip=False,
        )
        await db.commit()
        logger.info("Provisioned initial production administrator '%s'", username)
    else:
        logger.info("Initial administrator '%s' already exists; skipping provisioning", username)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + seed data + LLM cache. Shutdown: cleanup."""
    logger.info(f"🚀 Starting {settings.app_name} [{settings.app_env}]")

    # Ensure data dir
    Path("./data").mkdir(exist_ok=True)

    # Init Redis LLM cache (trước khi init DB để cache sẵn sàng)
    from src.services.cache_service import init_llm_cache
    init_llm_cache()

    # Init DB tables
    from src.database import AsyncSessionLocal, engine, init_db
    instrument_sqlalchemy(engine)
    await init_db()
    logger.info("✅ Database initialized")

    # Seed data
    async with AsyncSessionLocal() as db:
        if settings.is_demo_seed_enabled:
            await _seed_demo_users(db)
        else:
            if settings.initial_admin_email and settings.initial_admin_password:
                await _provision_initial_admin(
                    db,
                    email=settings.initial_admin_email,
                    username=settings.initial_admin_username or "admin",
                    password=settings.initial_admin_password,
                    full_name=settings.initial_admin_full_name or "System Administrator",
                )
            else:
                logger.info(
                    "Demo user seeding is disabled (APP_ENV=%s, ENABLE_DEMO_SEED=%s)",
                    settings.app_env,
                    settings.enable_demo_seed,
                )
        await _seed_knowledge_base(db)
        # Reuse the RAG embedding backend to make legacy tickets discoverable for duplicate checks.
        from src.services.duplicate_detection_service import rebuild_ticket_duplicate_index
        await rebuild_ticket_duplicate_index(db)

    logger.info("✅ Ready to serve requests")
    yield
    logger.info("Shutting down Help Desk AI Agent...")
    shutdown_telemetry()


app = FastAPI(
    title="Help Desk AI Agent",
    description="Enterprise IT Help Desk AI Agent — LangGraph + RAG + HITL",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Request Size Hard Limit Guard
from src.guardrails.request_size_guard import RequestSizeLimitMiddleware
app.add_middleware(RequestSizeLimitMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trace ID Middleware. The header is for support/UI correlation only; W3C
# traceparent propagation and span creation are handled by OpenTelemetry.
@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    # Request ID is local support correlation only. W3C traceparent remains the
    # distributed identity and is created/continued by FastAPI instrumentation.
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    token = set_request_id(request_id[:128])
    started = perf_counter()
    try:
        response: Response = await call_next(request)
        trace_id = current_trace_id()
        if trace_id:
            request.state.trace_id = trace_id
            response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Request-ID"] = request_id[:128]
        return response
    finally:
        route = getattr(request.scope.get("route"), "path", None) or request.url.path
        status_code = locals().get("response", None)
        record_http_request(
            route=route,
            method=request.method,
            status_code=status_code.status_code if status_code is not None else 500,
            duration_ms=(perf_counter() - started) * 1000,
        )
        reset_request_id(token)

# Routes
app.include_router(router, prefix="/api/v1")

# Configure this after application middleware/routes are registered so the
# auto-instrumentor observes the complete ASGI application.
configure_telemetry(app, settings)


@app.get("/health")
async def health():
    from src.services.cache_service import get_cache_status
    from src.services.rag_service import get_collection_count
    return {
        "status": "ok",
        "env": settings.app_env,
        "kb_documents": get_collection_count(),
        "cache": get_cache_status(),
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    return {
        "app": "Help Desk AI Agent",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }
