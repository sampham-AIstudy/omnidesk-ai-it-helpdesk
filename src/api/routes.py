"""API routes — Aggregate all routers."""
from fastapi import APIRouter

from src.api.admin import router as admin_router
from src.api.analytics import router as analytics_router
from src.api.auth import router as auth_router
from src.api.chat import router as chat_router
from src.api.policies import router as policies_router
from src.api.policies_admin import router as policies_admin_router
from src.api.service_requests import router as service_requests_router
from src.api.tickets import router as tickets_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(tickets_router)
router.include_router(service_requests_router)
router.include_router(analytics_router)
router.include_router(admin_router)
router.include_router(policies_admin_router)
router.include_router(policies_router)
router.include_router(chat_router)
