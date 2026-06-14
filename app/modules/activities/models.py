import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.base_model import AuditUserMixin, TimestampMixin, UUIDMixin


class ActivityKind(str, Enum):
    ACTIVITY = "activity"
    TASK = "task"


class ActivityStatus(str, Enum):
    PLANNED = "planned"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActivityType(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "activity_types"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="activity_type")


class Activity(Base, UUIDMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "activities"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    activity_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activity_types.id", ondelete="RESTRICT"), nullable=False
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    activity_type: Mapped["ActivityType"] = relationship("ActivityType", back_populates="activities")
    contact: Mapped[Optional["Contact"]] = relationship("Contact")  # noqa: F821
    account: Mapped[Optional["Account"]] = relationship("Account")  # noqa: F821
    opportunity: Mapped[Optional["Opportunity"]] = relationship("Opportunity")  # noqa: F821

    @property
    def reference_at(self) -> datetime:
        return self.completed_at or self.due_at or self.scheduled_at or self.created_at

    @property
    def is_overdue(self) -> bool:
        if self.kind != ActivityKind.TASK or self.status == ActivityStatus.COMPLETED:
            return False
        if self.due_at is None:
            return False
        due_at = self.due_at
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        return due_at < datetime.now(timezone.utc)
