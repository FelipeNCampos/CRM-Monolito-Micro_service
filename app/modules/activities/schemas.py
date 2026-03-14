from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from app.modules.activities.models import ActivityKind, ActivityStatus, TaskPriority


class ActivityTypeCreate(BaseModel):
    name: str
    sort_order: int = 0


class ActivityTypeUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ActivityTypeResponse(BaseModel):
    id: UUID
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityCreate(BaseModel):
    title: str
    activity_type_id: UUID
    kind: ActivityKind = ActivityKind.ACTIVITY
    description: Optional[str] = None
    status: ActivityStatus = ActivityStatus.PLANNED
    scheduled_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    priority: Optional[TaskPriority] = None
    contact_id: Optional[UUID] = None
    account_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Duração deve ser maior ou igual a zero")
        return value

    @model_validator(mode="after")
    def validate_links(self):
        if self.kind == ActivityKind.ACTIVITY:
            if self.contact_id is None:
                raise ValueError("Atividades exigem pelo menos um contato vinculado")
            if self.scheduled_at is None:
                raise ValueError("Atividades exigem data/hora de registro")

        if self.kind == ActivityKind.TASK:
            if self.contact_id is None and self.opportunity_id is None:
                raise ValueError("Tarefas exigem contato ou oportunidade vinculada")
            if self.due_at is None:
                raise ValueError("Tarefas exigem data/hora de vencimento")

        return self


class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    activity_type_id: Optional[UUID] = None
    description: Optional[str] = None
    status: Optional[ActivityStatus] = None
    scheduled_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    priority: Optional[TaskPriority] = None
    contact_id: Optional[UUID] = None
    account_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Duração deve ser maior ou igual a zero")
        return value


class ActivityComplete(BaseModel):
    completed_at: Optional[datetime] = None


class ActivityTypeSummary(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class ContactSummary(BaseModel):
    id: UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class AccountSummary(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class OpportunitySummary(BaseModel):
    id: UUID
    title: str
    status: str

    model_config = {"from_attributes": True}


class ActivityResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    kind: str
    status: str
    scheduled_at: Optional[datetime]
    due_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_minutes: Optional[int]
    priority: Optional[str]
    contact_id: Optional[UUID]
    account_id: Optional[UUID]
    opportunity_id: Optional[UUID]
    owner_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]
    updated_by: Optional[UUID]
    is_overdue: bool
    activity_type: ActivityTypeSummary
    contact: Optional[ContactSummary]
    account: Optional[AccountSummary]
    opportunity: Optional[OpportunitySummary]

    model_config = {"from_attributes": True}


class ActivityListResponse(BaseModel):
    id: UUID
    title: str
    kind: str
    status: str
    scheduled_at: Optional[datetime]
    due_at: Optional[datetime]
    completed_at: Optional[datetime]
    priority: Optional[str]
    owner_id: Optional[UUID]
    contact_id: Optional[UUID]
    opportunity_id: Optional[UUID]
    is_overdue: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityFilters(BaseModel):
    activity_type_id: Optional[UUID] = None
    kind: Optional[ActivityKind] = None
    status: Optional[ActivityStatus] = None
    owner_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    account_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    due_from: Optional[datetime] = None
    due_to: Optional[datetime] = None
    overdue_only: bool = False
    sort_order: str = "desc"
