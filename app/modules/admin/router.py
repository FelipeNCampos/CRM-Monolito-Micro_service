from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_permission
from app.modules.admin.models import CustomFieldEntity
from app.modules.admin.schemas import (
    CustomFieldCatalogResponse,
    CustomFieldCreate,
    CustomFieldImpactResponse,
    CustomFieldResponse,
    CustomFieldUpdate,
    CustomFieldValueValidationRequest,
    CustomFieldValueValidationResponse,
)
from app.modules.admin.service import AdminService
from app.modules.audit.service import AuditService

router = APIRouter(prefix="/admin/custom-fields", tags=["Administracao - Campos"])


def _svc(db: AsyncSession) -> AdminService:
    return AdminService(db, AuditService(db))


@router.post(
    "",
    response_model=CustomFieldResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin", "create"))],
)
async def create_custom_field(
    data: CustomFieldCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).create_custom_field(data, creator_id=current_user.id)


@router.get(
    "",
    response_model=list[CustomFieldResponse],
    dependencies=[Depends(require_permission("admin", "read"))],
)
async def list_custom_fields(
    db: Annotated[AsyncSession, Depends(get_db)],
    entity_type: CustomFieldEntity | None = None,
    active_only: bool = Query(False),
):
    return await _svc(db).list_custom_fields(entity_type, active_only=active_only)


@router.get(
    "/catalog/{entity_type}",
    response_model=CustomFieldCatalogResponse,
    dependencies=[Depends(require_permission("admin", "read"))],
)
async def get_custom_field_catalog(
    entity_type: CustomFieldEntity,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _svc(db).get_custom_field_catalog(entity_type)


@router.post(
    "/catalog/{entity_type}/validate",
    response_model=CustomFieldValueValidationResponse,
    dependencies=[Depends(require_permission("admin", "read"))],
)
async def validate_custom_field_values(
    entity_type: CustomFieldEntity,
    data: CustomFieldValueValidationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    values = await _svc(db).validate_custom_field_values(
        entity_type,
        data.values,
        existing_values=data.existing_values,
        require_all_required=data.require_all_required,
    )
    return CustomFieldValueValidationResponse(entity_type=entity_type, values=values)


@router.get(
    "/{field_id}",
    response_model=CustomFieldResponse,
    dependencies=[Depends(require_permission("admin", "read"))],
)
async def get_custom_field(
    field_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _svc(db).get_custom_field(field_id)


@router.get(
    "/{field_id}/impact",
    response_model=CustomFieldImpactResponse,
    dependencies=[Depends(require_permission("admin", "read"))],
)
async def get_custom_field_impact(
    field_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _svc(db).get_custom_field_impact(field_id)


@router.put(
    "/{field_id}",
    response_model=CustomFieldResponse,
    dependencies=[Depends(require_permission("admin", "update"))],
)
async def update_custom_field(
    field_id: UUID,
    data: CustomFieldUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
):
    return await _svc(db).update_custom_field(field_id, data, updater_id=current_user.id)


@router.delete(
    "/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("admin", "delete"))],
)
async def delete_custom_field(
    field_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_active_user),
    force: bool = Query(False),
):
    await _svc(db).delete_custom_field(field_id, actor_id=current_user.id, force=force)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
