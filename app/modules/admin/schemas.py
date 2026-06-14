from __future__ import annotations

import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.admin.models import CustomFieldEntity, CustomFieldType


def normalize_custom_field_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not normalized:
        raise ValueError("Campo precisa gerar uma chave valida")
    return normalized


class CustomFieldBase(BaseModel):
    entity_type: CustomFieldEntity
    name: str = Field(min_length=1, max_length=150)
    key: Optional[str] = Field(default=None, max_length=150)
    field_type: CustomFieldType
    is_required: bool = False
    show_in_forms: bool = True
    show_in_details: bool = True
    allow_in_filters: bool = False
    allow_in_reports: bool = False
    options: Optional[list[str]] = None
    critical_report_refs: list[str] = Field(default_factory=list)

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_custom_field_key(value)

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Opcoes do campo nao podem se repetir")
        return cleaned

    @field_validator("critical_report_refs")
    @classmethod
    def validate_critical_report_refs(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]

    @model_validator(mode="after")
    def validate_select_options(self):
        if self.field_type == CustomFieldType.SELECT and not self.options:
            raise ValueError("Campos do tipo select exigem opcoes")
        if self.field_type != CustomFieldType.SELECT and self.options:
            raise ValueError("Apenas campos do tipo select aceitam opcoes")
        return self


class CustomFieldCreate(CustomFieldBase):
    pass


class CustomFieldUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    key: Optional[str] = Field(default=None, max_length=150)
    field_type: Optional[CustomFieldType] = None
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None
    show_in_forms: Optional[bool] = None
    show_in_details: Optional[bool] = None
    allow_in_filters: Optional[bool] = None
    allow_in_reports: Optional[bool] = None
    options: Optional[list[str]] = None
    critical_report_refs: Optional[list[str]] = None

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_custom_field_key(value)

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Opcoes do campo nao podem se repetir")
        return cleaned

    @field_validator("critical_report_refs")
    @classmethod
    def validate_critical_report_refs(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return [item.strip() for item in value if item and item.strip()]

    @model_validator(mode="after")
    def validate_select_options(self):
        if self.field_type == CustomFieldType.SELECT and self.options == []:
            raise ValueError("Campos do tipo select exigem opcoes")
        if self.field_type and self.field_type != CustomFieldType.SELECT and self.options:
            raise ValueError("Apenas campos do tipo select aceitam opcoes")
        return self


class CustomFieldResponse(BaseModel):
    id: UUID
    entity_type: CustomFieldEntity
    name: str
    key: str
    field_type: CustomFieldType
    is_required: bool
    is_active: bool
    show_in_forms: bool
    show_in_details: bool
    allow_in_filters: bool
    allow_in_reports: bool
    options: Optional[list[str]]
    critical_report_refs: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomFieldCatalogResponse(BaseModel):
    entity_type: CustomFieldEntity
    form_fields: list[CustomFieldResponse]
    detail_fields: list[CustomFieldResponse]
    filter_fields: list[CustomFieldResponse]
    report_fields: list[CustomFieldResponse]


class CustomFieldImpactResponse(BaseModel):
    field: CustomFieldResponse
    records_with_value: int
    critical_report_refs: list[str]
    can_delete: bool
    requires_force: bool


class CustomFieldValueValidationRequest(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    existing_values: Optional[dict[str, Any]] = None
    require_all_required: bool = True


class CustomFieldValueValidationResponse(BaseModel):
    entity_type: CustomFieldEntity
    values: dict[str, Any]


def normalize_custom_field_value(field_type: CustomFieldType, value: Any, options: list[str] | None) -> Any:
    if value is None:
        return None

    if field_type == CustomFieldType.TEXT:
        return str(value).strip()

    if field_type == CustomFieldType.NUMBER:
        try:
            normalized = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Valor numerico invalido") from exc
        return int(normalized) if normalized == normalized.to_integral() else float(normalized)

    if field_type == CustomFieldType.DATE:
        if isinstance(value, date):
            return value.isoformat()
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError as exc:
            raise ValueError("Valor de data invalido") from exc

    if field_type == CustomFieldType.BOOLEAN:
        if isinstance(value, bool):
            return value
        lowered = str(value).strip().lower()
        if lowered in {"true", "1", "sim", "yes"}:
            return True
        if lowered in {"false", "0", "nao", "no"}:
            return False
        raise ValueError("Valor booleano invalido")

    if field_type == CustomFieldType.SELECT:
        normalized = str(value).strip()
        if not options or normalized not in options:
            raise ValueError("Opcao invalida para campo select")
        return normalized

    raise ValueError("Tipo de campo nao suportado")

