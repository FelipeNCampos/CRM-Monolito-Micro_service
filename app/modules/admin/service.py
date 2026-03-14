from __future__ import annotations

import uuid
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts.models import Account
from app.modules.admin.models import (
    CustomFieldDefinition,
    CustomFieldEntity,
    CustomFieldType,
)
from app.modules.admin.schemas import (
    CustomFieldCatalogResponse,
    CustomFieldCreate,
    CustomFieldImpactResponse,
    CustomFieldResponse,
    CustomFieldUpdate,
    normalize_custom_field_key,
    normalize_custom_field_value,
)
from app.modules.audit.service import AuditService
from app.modules.contacts.models import Contact
from app.modules.opportunities.models import Opportunity


class AdminService:
    def __init__(self, db: AsyncSession, audit: AuditService):
        self.db = db
        self.audit = audit

    async def create_custom_field(
        self, data: CustomFieldCreate, creator_id: Optional[UUID] = None
    ) -> CustomFieldDefinition:
        key = normalize_custom_field_key(data.key or data.name)
        await self._ensure_unique_field(data.entity_type, key)

        field = CustomFieldDefinition(
            id=uuid.uuid4(),
            entity_type=data.entity_type.value,
            name=data.name,
            key=key,
            field_type=data.field_type.value,
            is_required=data.is_required,
            is_active=True,
            show_in_forms=data.show_in_forms,
            show_in_details=data.show_in_details,
            allow_in_filters=data.allow_in_filters,
            allow_in_reports=data.allow_in_reports,
            options=data.options,
            critical_report_refs=data.critical_report_refs,
        )
        self.db.add(field)
        await self.db.flush()

        await self.audit.log(
            entity_type="custom_field",
            entity_id=field.id,
            action="create",
            user_id=creator_id,
            new_values={"entity_type": field.entity_type, "key": field.key},
        )
        return field

    async def list_custom_fields(
        self,
        entity_type: CustomFieldEntity | None = None,
        *,
        active_only: bool = False,
    ) -> list[CustomFieldDefinition]:
        query = select(CustomFieldDefinition).order_by(
            CustomFieldDefinition.entity_type,
            CustomFieldDefinition.name,
        )
        if entity_type is not None:
            query = query.where(CustomFieldDefinition.entity_type == entity_type.value)
        if active_only:
            query = query.where(CustomFieldDefinition.is_active == True)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_custom_field(self, field_id: UUID) -> CustomFieldDefinition:
        result = await self.db.execute(
            select(CustomFieldDefinition).where(CustomFieldDefinition.id == field_id)
        )
        field = result.scalar_one_or_none()
        if field is None:
            raise HTTPException(status_code=404, detail="Campo personalizado nao encontrado")
        return field

    async def update_custom_field(
        self, field_id: UUID, data: CustomFieldUpdate, updater_id: Optional[UUID] = None
    ) -> CustomFieldDefinition:
        field = await self.get_custom_field(field_id)
        impact = await self.get_custom_field_impact(field_id)

        next_key = normalize_custom_field_key(data.key) if data.key is not None else field.key
        next_type = data.field_type.value if data.field_type is not None else field.field_type
        if impact.records_with_value and (next_key != field.key or next_type != field.field_type):
            raise HTTPException(
                status_code=409,
                detail="Campo em uso nao pode ter chave ou tipo alterados",
            )

        if next_key != field.key:
            await self._ensure_unique_field(
                CustomFieldEntity(field.entity_type),
                next_key,
                exclude_id=field.id,
            )

        old_values = {
            "name": field.name,
            "key": field.key,
            "field_type": field.field_type,
            "is_active": field.is_active,
        }

        if data.name is not None:
            field.name = data.name
        if data.key is not None:
            field.key = next_key
        if data.field_type is not None:
            field.field_type = next_type
        if data.is_required is not None:
            field.is_required = data.is_required
        if data.is_active is not None:
            field.is_active = data.is_active
        if data.show_in_forms is not None:
            field.show_in_forms = data.show_in_forms
        if data.show_in_details is not None:
            field.show_in_details = data.show_in_details
        if data.allow_in_filters is not None:
            field.allow_in_filters = data.allow_in_filters
        if data.allow_in_reports is not None:
            field.allow_in_reports = data.allow_in_reports
        if data.options is not None:
            if (data.field_type is None and field.field_type != CustomFieldType.SELECT.value) or (
                data.field_type is not None and data.field_type != CustomFieldType.SELECT
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Somente campos select podem possuir opcoes",
                )
            field.options = data.options
        if data.critical_report_refs is not None:
            field.critical_report_refs = data.critical_report_refs

        await self.db.flush()
        await self.db.refresh(field)
        await self.audit.log(
            entity_type="custom_field",
            entity_id=field.id,
            action="update",
            user_id=updater_id,
            old_values=old_values,
            new_values={
                "name": field.name,
                "key": field.key,
                "field_type": field.field_type,
                "is_active": field.is_active,
            },
        )
        return field

    async def get_custom_field_catalog(
        self, entity_type: CustomFieldEntity
    ) -> CustomFieldCatalogResponse:
        fields = await self.list_custom_fields(entity_type, active_only=True)
        responses = [CustomFieldResponse.model_validate(field) for field in fields]
        return CustomFieldCatalogResponse(
            entity_type=entity_type,
            form_fields=[field for field in responses if field.show_in_forms],
            detail_fields=[field for field in responses if field.show_in_details],
            filter_fields=[field for field in responses if field.allow_in_filters],
            report_fields=[field for field in responses if field.allow_in_reports],
        )

    async def get_custom_field_impact(self, field_id: UUID) -> CustomFieldImpactResponse:
        field = await self.get_custom_field(field_id)
        records_with_value = await self._count_records_using_field(field)
        critical_report_refs = list(field.critical_report_refs or [])
        return CustomFieldImpactResponse(
            field=CustomFieldResponse.model_validate(field),
            records_with_value=records_with_value,
            critical_report_refs=critical_report_refs,
            can_delete=not critical_report_refs,
            requires_force=records_with_value > 0,
        )

    async def delete_custom_field(
        self, field_id: UUID, actor_id: Optional[UUID] = None, *, force: bool = False
    ) -> None:
        field = await self.get_custom_field(field_id)
        impact = await self.get_custom_field_impact(field_id)
        if impact.critical_report_refs:
            raise HTTPException(
                status_code=409,
                detail="Campo referenciado por relatorios criticos nao pode ser removido",
            )
        if impact.records_with_value > 0 and not force:
            raise HTTPException(
                status_code=409,
                detail="Campo possui valores salvos. Refaca com force=true apos validar o impacto.",
            )

        field.is_active = False
        await self.db.flush()
        await self.audit.log(
            entity_type="custom_field",
            entity_id=field.id,
            action="delete",
            user_id=actor_id,
            old_values={"is_active": True},
            new_values={"is_active": False},
        )

    async def validate_custom_field_values(
        self,
        entity_type: CustomFieldEntity,
        values: dict[str, Any] | None,
        *,
        existing_values: dict[str, Any] | None = None,
        require_all_required: bool = True,
    ) -> dict[str, Any]:
        definitions = await self.list_custom_fields(entity_type, active_only=True)
        definitions_by_key = {definition.key: definition for definition in definitions}

        merged = dict(existing_values or {})
        for key, raw_value in (values or {}).items():
            definition = definitions_by_key.get(key)
            if definition is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Campo personalizado `{key}` nao esta configurado para {entity_type.value}",
                )
            try:
                normalized = normalize_custom_field_value(
                    CustomFieldType(definition.field_type),
                    raw_value,
                    definition.options,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"{key}: {exc}") from exc

            if normalized in (None, ""):
                merged.pop(key, None)
            else:
                merged[key] = normalized

        if require_all_required:
            missing_required = [
                definition.key
                for definition in definitions
                if definition.is_required and merged.get(definition.key) in (None, "", [], {})
            ]
            if missing_required:
                raise HTTPException(
                    status_code=400,
                    detail=f"Campos personalizados obrigatorios ausentes: {', '.join(missing_required)}",
                )

        return merged

    async def _ensure_unique_field(
        self,
        entity_type: CustomFieldEntity,
        key: str,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        query = select(CustomFieldDefinition).where(
            CustomFieldDefinition.entity_type == entity_type.value,
            CustomFieldDefinition.key == key,
        )
        if exclude_id is not None:
            query = query.where(CustomFieldDefinition.id != exclude_id)
        result = await self.db.execute(query)
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail="Ja existe um campo personalizado com esta chave para a entidade",
            )

    async def _count_records_using_field(self, field: CustomFieldDefinition) -> int:
        model = self._model_for_entity(CustomFieldEntity(field.entity_type))
        query = select(func.count()).select_from(model).where(model.custom_fields.has_key(field.key))
        result = await self.db.execute(query)
        return result.scalar_one()

    def _model_for_entity(self, entity_type: CustomFieldEntity):
        if entity_type == CustomFieldEntity.CONTACT:
            return Contact
        if entity_type == CustomFieldEntity.ACCOUNT:
            return Account
        return Opportunity
