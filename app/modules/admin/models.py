from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.base_model import TimestampMixin, UUIDMixin


class CustomFieldEntity(str, Enum):
    CONTACT = "contact"
    ACCOUNT = "account"
    OPPORTUNITY = "opportunity"


class CustomFieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    SELECT = "select"


class CustomFieldDefinition(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "custom_field_definitions"
    __table_args__ = (
        UniqueConstraint("entity_type", "key", name="uq_custom_field_entity_key"),
    )

    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    key: Mapped[str] = mapped_column(String(150), nullable=False)
    field_type: Mapped[str] = mapped_column(String(30), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_in_forms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_in_details: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_in_filters: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_in_reports: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    options: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    critical_report_refs: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )

