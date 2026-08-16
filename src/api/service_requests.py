"""API endpoints for the Service Request lifecycle, independent of incidents."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_active_user
from src.database import get_db
from src.models.schemas import (
    ServiceCatalogResponse,
    ServiceRequestApprovalDecision,
    ServiceRequestApprovalQueueResponse,
    ServiceRequestCreate,
    ServiceRequestDetailResponse,
    ServiceRequestListResponse,
    ServiceRequestRejectionDecision,
    ServiceRequestResponse,
    ServiceRequestTransition,
)
from src.models.user import User, UserRole
from src.services import auth_service
from src.services.service_request_service import (
    ServiceRequestAuthorizationError,
    ServiceRequestConflictError,
    approve_service_request,
    create_service_request,
    get_service_request,
    list_pending_service_request_approvals,
    list_service_catalog,
    list_service_requests,
    list_technician_queue,
    reject_service_request,
    serialize_service_request,
    take_service_request,
    transition_service_request,
)

router = APIRouter(prefix="/service-requests", tags=["service-requests"])


@router.get("/catalog", response_model=ServiceCatalogResponse)
async def service_catalog(current_user: User = Depends(get_current_active_user)):
    """Read-only, employee-safe source of truth for the service catalog."""
    return ServiceCatalogResponse(items=list_service_catalog())


@router.post("", response_model=ServiceRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: ServiceRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
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


def _technician_allowed(user: User) -> bool:
    return user.role in {UserRole.TECHNICIAN, UserRole.ADMIN}


def _approval_allowed(user: User) -> bool:
    """Service Request approval is a manager/admin business decision, not Incident HITL."""
    return user.role in {UserRole.MANAGER, UserRole.ADMIN}


async def _ensure_request_access(request, current_user: User, db: AsyncSession) -> None:
    if request.submitter_id == current_user.id:
        return
    if current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="You cannot access this Service Request.")
    submitter = await db.get(User, request.submitter_id)
    if not submitter or not auth_service.can_access_company_unit(current_user, submitter.company_unit):
        raise HTTPException(status_code=403, detail="You cannot access this Service Request.")


@router.get("/pending-approval", response_model=ServiceRequestApprovalQueueResponse)
async def pending_approval_queue(
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _approval_allowed(current_user):
        raise HTTPException(status_code=403, detail="Manager approval access is required.")
    items = await list_pending_service_request_approvals(db, current_user, limit=limit)
    return ServiceRequestApprovalQueueResponse(
        items=[ServiceRequestDetailResponse.model_validate(await serialize_service_request(db, item)) for item in items]
    )


@router.get("/technician/queue", response_model=ServiceRequestListResponse)
async def technician_queue(
    fulfillment_group: str | None = Query(None, min_length=1, max_length=100),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Authoritative Service Request queue, tenant scoped and stably ordered."""
    if not _technician_allowed(current_user):
        raise HTTPException(status_code=403, detail="Technician fulfillment access is required.")
    items = await list_technician_queue(
        db, current_user, fulfillment_group=fulfillment_group, limit=limit,
    )
    return ServiceRequestListResponse(items=[ServiceRequestResponse.model_validate(item) for item in items])


@router.get("/{request_number}", response_model=ServiceRequestDetailResponse)
async def request_detail(
    request_number: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    request = await get_service_request(db, request_number)
    if not request:
        raise HTTPException(status_code=404, detail="Service Request not found.")
    await _ensure_request_access(request, current_user, db)
    return ServiceRequestDetailResponse.model_validate(await serialize_service_request(db, request, include_activity=True))


@router.post("/{request_number}/takeover", response_model=ServiceRequestDetailResponse)
async def takeover_request(
    request_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _technician_allowed(current_user):
        raise HTTPException(status_code=403, detail="Technician fulfillment access is required.")
    request = await get_service_request(db, request_number)
    if not request:
        raise HTTPException(status_code=404, detail="Service Request not found.")
    await _ensure_request_access(request, current_user, db)
    try:
        request = await take_service_request(db, request=request, technician=current_user)
    except ServiceRequestAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ServiceRequestConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ServiceRequestDetailResponse.model_validate(await serialize_service_request(db, request, include_activity=True))


@router.post("/{request_number}/approve", response_model=ServiceRequestDetailResponse)
async def approve_request(
    request_number: str,
    payload: ServiceRequestApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _approval_allowed(current_user):
        raise HTTPException(status_code=403, detail="Manager approval access is required.")
    request = await get_service_request(db, request_number)
    if not request:
        raise HTTPException(status_code=404, detail="Service Request not found.")
    await _ensure_request_access(request, current_user, db)
    try:
        request = await approve_service_request(db, request=request, approver=current_user, comment=payload.comment)
    except ServiceRequestConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ServiceRequestDetailResponse.model_validate(await serialize_service_request(db, request, include_activity=True))


@router.post("/{request_number}/reject", response_model=ServiceRequestDetailResponse)
async def reject_request(
    request_number: str,
    payload: ServiceRequestRejectionDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _approval_allowed(current_user):
        raise HTTPException(status_code=403, detail="Manager approval access is required.")
    request = await get_service_request(db, request_number)
    if not request:
        raise HTTPException(status_code=404, detail="Service Request not found.")
    await _ensure_request_access(request, current_user, db)
    try:
        request = await reject_service_request(db, request=request, approver=current_user, reason=payload.reason)
    except ServiceRequestConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ServiceRequestDetailResponse.model_validate(await serialize_service_request(db, request, include_activity=True))


@router.post("/{request_number}/transition", response_model=ServiceRequestDetailResponse)
async def transition_request(
    request_number: str,
    payload: ServiceRequestTransition,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _technician_allowed(current_user):
        raise HTTPException(status_code=403, detail="Technician fulfillment access is required.")
    request = await get_service_request(db, request_number)
    if not request:
        raise HTTPException(status_code=404, detail="Service Request not found.")
    await _ensure_request_access(request, current_user, db)
    try:
        request = await transition_service_request(db, request=request, technician=current_user, target=payload.target_status)
    except ServiceRequestConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ServiceRequestDetailResponse.model_validate(await serialize_service_request(db, request, include_activity=True))
