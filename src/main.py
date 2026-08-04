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
    """Index KB entries vào ChromaDB nếu chưa có."""
    from src.data.knowledge_base import get_all_kb_entries
    from src.models.knowledge_base import KnowledgeBaseEntry
    from src.services.rag_service import get_collection_count, index_document
    from sqlalchemy import select

    existing_count = get_collection_count()
    if existing_count > 0:
        logger.info(f"KB already indexed: {existing_count} documents in ChromaDB")
        return

    entries = get_all_kb_entries()
    logger.info(f"Seeding {len(entries)} KB entries into ChromaDB...")

    for entry_data in entries:
        # Save to SQLite
        kb_id = entry_data["id"]
        db_entry = KnowledgeBaseEntry(
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
        db.add(db_entry)

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
    """Startup: init DB + seed data. Shutdown: cleanup."""
    logger.info(f"🚀 Starting {settings.app_name} [{settings.app_env}]")

    # Ensure data dir
    Path("./data").mkdir(exist_ok=True)

    # Init DB tables
    from src.database import init_db, AsyncSessionLocal
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

# Routes
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    from src.services.rag_service import get_collection_count
    return {
        "status": "ok",
        "env": settings.app_env,
        "kb_documents": get_collection_count(),
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
