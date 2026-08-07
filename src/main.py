"""
Help Desk AI Agent — FastAPI App Entry Point
Tự động: init DB, seed demo users, seed knowledge base vào ChromaDB
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


async def _seed_demo_users(db):
    """Tạo demo users nếu chưa có."""
    from src.models.user import CompanyUnit, UserRole
    from src.services.auth_service import create_user, get_user_by_username

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

    if seeded:
        await db.commit()
        logger.info(f"Seeded {seeded} demo users")


async def _seed_knowledge_base(db):
    """Đồng bộ các KB entry còn thiếu vào SQLite và ChromaDB."""
    from sqlalchemy import select

    from src.data.knowledge_base import get_all_kb_entries
    from src.models.knowledge_base import KnowledgeBaseEntry
    from src.services.rag_service import (
        get_collection_count,
        get_indexed_document_ids,
        index_document,
    )
    entries = get_all_kb_entries()
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
    from src.database import AsyncSessionLocal, init_db
    await init_db()
    logger.info("✅ Database initialized")

    # Seed demo data
    async with AsyncSessionLocal() as db:
        await _seed_demo_users(db)
        await _seed_knowledge_base(db)

    logger.info("✅ Ready to serve requests")
    yield
    logger.info("Shutting down Help Desk AI Agent...")


app = FastAPI(
    title="Help Desk AI Agent",
    description="Enterprise IT Help Desk AI Agent — LangGraph + RAG + HITL",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trace ID Middleware
import uuid
from starlette.requests import Request
from starlette.responses import Response

@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())[:8]
    request.state.trace_id = trace_id
    response: Response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response

# Routes
app.include_router(router, prefix="/api/v1")


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
