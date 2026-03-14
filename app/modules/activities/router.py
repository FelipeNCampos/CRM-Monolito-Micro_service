from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_permission
from app.modules.activities.models import ActivityKind, ActivityStatus
from app.modules.activities.schemas import (
    ActivityComplete,
    ActivityCreate,
    ActivityFilters,
    ActivityListResponse,
    ActivityResponse,
    ActivityTypeCreate,
    ActivityTypeResponse,
    ActivityTypeUpdate,
    ActivityUpdate,
)
from app.modules.activities.service import ActivityService
from app.modules.audit.service import AuditService
from app.shared.pagination import PaginatedResponse, PaginationParams

router = APIRouter(tags=["Atividades"])


def _svc(db: AsyncSession) -> ActivityService:
    return ActivityService(db, AuditService(db))


@router.post(
    "/activity-types",
    response_model=ActivityTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("activities", "create"))],
)
async def create_activity_type(
    data: ActivityTypeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).create_type(data, creator_id=current_user.id)


@router.get(
    "/activity-types",
    response_model=list[ActivityTypeResponse],
    dependencies=[Depends(require_permission("activities", "read"))],
)
async def list_activity_types(db: Annotated[AsyncSession, Depends(get_db)]):
    return await _svc(db).list_types()


@router.put(
    "/activity-types/{activity_type_id}",
    response_model=ActivityTypeResponse,
    dependencies=[Depends(require_permission("activities", "update"))],
)
async def update_activity_type(
    activity_type_id: UUID,
    data: ActivityTypeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).update_type(activity_type_id, data, updater_id=current_user.id)


@router.post(
    "/activities",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("activities", "create"))],
)
async def create_activity(
    data: ActivityCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).create(data, creator_id=current_user.id)


@router.get(
    "/activities",
    response_model=PaginatedResponse[ActivityListResponse],
    dependencies=[Depends(require_permission("activities", "read"))],
)
async def list_activities(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    activity_type_id: UUID | None = None,
    kind: ActivityKind | None = None,
    status: ActivityStatus | None = None,
    owner_id: UUID | None = None,
    contact_id: UUID | None = None,
    account_id: UUID | None = None,
    opportunity_id: UUID | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    overdue_only: bool = False,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    filters = ActivityFilters(
        activity_type_id=activity_type_id,
        kind=kind,
        status=status,
        owner_id=owner_id,
        contact_id=contact_id,
        account_id=account_id,
        opportunity_id=opportunity_id,
        due_from=due_from,
        due_to=due_to,
        overdue_only=overdue_only,
        sort_order=sort_order,
    )
    items, total = await _svc(db).list(filters, PaginationParams(page=page, per_page=per_page))
    return PaginatedResponse.build(items, total, page, per_page)


@router.get(
    "/activities/{activity_id}",
    response_model=ActivityResponse,
    dependencies=[Depends(require_permission("activities", "read"))],
)
async def get_activity(
    activity_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _svc(db).get(activity_id)


@router.put(
    "/activities/{activity_id}",
    response_model=ActivityResponse,
    dependencies=[Depends(require_permission("activities", "update"))],
)
async def update_activity(
    activity_id: UUID,
    data: ActivityUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).update(activity_id, data, updater_id=current_user.id)


@router.patch(
    "/activities/{activity_id}/complete",
    response_model=ActivityResponse,
    dependencies=[Depends(require_permission("activities", "update"))],
)
async def complete_activity(
    activity_id: UUID,
    data: ActivityComplete,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).complete(activity_id, data, actor_id=current_user.id)
