"""API endpoints for Service Requests, intentionally independent of incidents."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_active_user
from src.database import get_db
from src.models.schemas import (
    ServiceCatalogResponse,
    ServiceRequestCreate,
    ServiceRequestListResponse,
    ServiceRequestResponse,
)
from src.models.user import User, UserRole
from src.services import auth_service
from src.services.service_request_service import (
    create_service_request,
    get_service_request,
    list_service_catalog,
    list_service_requests,
)

router = APIRouter(prefix="/service-requests", tags=["service-requests"])


@router.get("/catalog", response_model=ServiceCatalogResponse)
async def service_catalog(current_user: User = Depends(get_current_active_user)):
    """Read-only, employee-safe source of truth for the service catalog."""
    return ServiceCatalogResponse(items=list_service_catalog())


@router.post("", response_model=ServiceRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(payload: ServiceRequestCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    try:
        request = await create_service_request(
            db, service_name=payload.service_name, category=payload.category,
            form_data=payload.form_data, submitter_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ServiceRequestResponse.model_validate(request)


@router.get("/mine", response_model=ServiceRequestListResponse)
async def my_requests(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    items = await list_service_requests(db, current_user.id)
    return ServiceRequestListResponse(items=[ServiceRequestResponse.model_validate(item) for item in items])


@router.get("/{request_number}", response_model=ServiceRequestResponse)
async def request_detail(request_number: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    request = await get_service_request(db, request_number)
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy Service Request.")
    if request.submitter_id == current_user.id:
        return ServiceRequestResponse.model_validate(request)

    if current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem yêu cầu này.")

    submitter = await db.get(User, request.submitter_id)
    if not submitter or not auth_service.can_access_company_unit(current_user, submitter.company_unit):
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem yêu cầu này.")
    return ServiceRequestResponse.model_validate(request)
