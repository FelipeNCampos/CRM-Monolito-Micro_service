from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.activities.models import (
    Activity,
    ActivityKind,
    ActivityStatus,
    ActivityType,
)
from app.modules.activities.schemas import (
    ActivityComplete,
    ActivityCreate,
    ActivityFilters,
    ActivityTypeCreate,
    ActivityTypeUpdate,
    ActivityUpdate,
)
from app.modules.audit.service import AuditService
from app.shared.pagination import PaginationParams


DEFAULT_ACTIVITY_TYPES = (
    ("Ligação", 10),
    ("Reunião", 20),
    ("E-mail", 30),
    ("Follow-up", 40),
)


class ActivityService:
    def __init__(self, db: AsyncSession, audit: AuditService):
        self.db = db
        self.audit = audit

    async def seed_default_types(self) -> None:
        result = await self.db.execute(select(ActivityType))
        existing = {item.name: item for item in result.scalars().all()}

        for name, sort_order in DEFAULT_ACTIVITY_TYPES:
            activity_type = existing.get(name)
            if activity_type is None:
                self.db.add(
                    ActivityType(
                        id=uuid.uuid4(),
                        name=name,
                        sort_order=sort_order,
                        is_active=True,
                    )
                )
            else:
                activity_type.sort_order = sort_order
                activity_type.is_active = True

        await self.db.flush()

    async def list_types(self) -> list[ActivityType]:
        result = await self.db.execute(
            select(ActivityType)
            .where(ActivityType.is_active == True)
            .order_by(ActivityType.sort_order, ActivityType.name)
        )
        return result.scalars().all()

    async def get_type(self, activity_type_id: UUID) -> ActivityType:
        result = await self.db.execute(
            select(ActivityType).where(ActivityType.id == activity_type_id)
        )
        activity_type = result.scalar_one_or_none()
        if not activity_type:
            raise HTTPException(status_code=404, detail="Tipo de atividade não encontrado")
        return activity_type

    async def create_type(
        self, data: ActivityTypeCreate, creator_id: Optional[UUID] = None
    ) -> ActivityType:
        existing = await self.db.execute(select(ActivityType).where(ActivityType.name == data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Tipo de atividade já existe")

        activity_type = ActivityType(
            id=uuid.uuid4(),
            name=data.name,
            sort_order=data.sort_order,
            is_active=True,
        )
        self.db.add(activity_type)
        await self.db.flush()
        await self.audit.log(
            entity_type="activity_type",
            entity_id=activity_type.id,
            action="create",
            user_id=creator_id,
            new_values={"name": activity_type.name},
        )
        return activity_type

    async def update_type(
        self, activity_type_id: UUID, data: ActivityTypeUpdate, updater_id: Optional[UUID] = None
    ) -> ActivityType:
        activity_type = await self.get_type(activity_type_id)

        if data.name is not None:
            other = await self.db.execute(
                select(ActivityType).where(
                    ActivityType.name == data.name,
                    ActivityType.id != activity_type_id,
                )
            )
            if other.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Tipo de atividade já existe")
            activity_type.name = data.name
        if data.sort_order is not None:
            activity_type.sort_order = data.sort_order
        if data.is_active is not None:
            activity_type.is_active = data.is_active

        await self.db.flush()
        await self.audit.log(
            entity_type="activity_type",
            entity_id=activity_type.id,
            action="update",
            user_id=updater_id,
            new_values={
                "name": activity_type.name,
                "sort_order": activity_type.sort_order,
                "is_active": activity_type.is_active,
            },
        )
        return activity_type

    async def create(self, data: ActivityCreate, creator_id: Optional[UUID] = None) -> Activity:
        await self._validate_links(data)
        completed_at = datetime.now(timezone.utc) if data.status == ActivityStatus.COMPLETED else None
        activity = Activity(
            id=uuid.uuid4(),
            title=data.title,
            description=data.description,
            kind=data.kind,
            status=data.status,
            scheduled_at=data.scheduled_at,
            due_at=data.due_at,
            completed_at=completed_at,
            duration_minutes=data.duration_minutes,
            priority=data.priority,
            activity_type_id=data.activity_type_id,
            contact_id=data.contact_id,
            account_id=data.account_id,
            opportunity_id=data.opportunity_id,
            owner_id=data.owner_id or creator_id,
            created_by=creator_id,
            updated_by=creator_id,
        )
        self.db.add(activity)
        await self.db.flush()
        await self.audit.log(
            entity_type="activity",
            entity_id=activity.id,
            action="create",
            user_id=creator_id,
            new_values={"title": activity.title, "kind": activity.kind, "status": activity.status},
        )
        return await self.get(activity.id)

    async def get(self, activity_id: UUID) -> Activity:
        result = await self.db.execute(
            select(Activity)
            .where(Activity.id == activity_id)
            .options(
                selectinload(Activity.activity_type),
                selectinload(Activity.contact),
                selectinload(Activity.account),
                selectinload(Activity.opportunity),
            )
        )
        activity = result.scalar_one_or_none()
        if not activity:
            raise HTTPException(status_code=404, detail="Atividade não encontrada")
        return activity

    async def list(self, filters: ActivityFilters, pagination: PaginationParams):
        reference_at = func.coalesce(
            Activity.completed_at,
            Activity.due_at,
            Activity.scheduled_at,
            Activity.created_at,
        )
        q = select(Activity).options(
            selectinload(Activity.activity_type),
            selectinload(Activity.contact),
            selectinload(Activity.account),
            selectinload(Activity.opportunity),
        )
        if filters.activity_type_id:
            q = q.where(Activity.activity_type_id == filters.activity_type_id)
        if filters.kind:
            q = q.where(Activity.kind == filters.kind)
        if filters.status:
            q = q.where(Activity.status == filters.status)
        if filters.owner_id:
            q = q.where(Activity.owner_id == filters.owner_id)
        if filters.contact_id:
            q = q.where(Activity.contact_id == filters.contact_id)
        if filters.account_id:
            q = q.where(Activity.account_id == filters.account_id)
        if filters.opportunity_id:
            q = q.where(Activity.opportunity_id == filters.opportunity_id)
        if filters.due_from:
            q = q.where(Activity.due_at >= filters.due_from)
        if filters.due_to:
            q = q.where(Activity.due_at <= filters.due_to)
        if filters.overdue_only:
            q = q.where(
                Activity.kind == ActivityKind.TASK,
                Activity.status != ActivityStatus.COMPLETED,
                Activity.due_at.is_not(None),
                Activity.due_at < datetime.now(timezone.utc),
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        order_clause = reference_at.asc() if filters.sort_order == "asc" else reference_at.desc()
        q = q.order_by(order_clause, Activity.created_at.desc())
        q = q.offset(pagination.offset).limit(pagination.per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update(
        self, activity_id: UUID, data: ActivityUpdate, updater_id: Optional[UUID] = None
    ) -> Activity:
        activity = await self.get(activity_id)
        old = {"title": activity.title, "status": activity.status}

        if data.activity_type_id is not None:
            await self._ensure_active_type(data.activity_type_id)
            activity.activity_type_id = data.activity_type_id
        if data.title is not None:
            activity.title = data.title
        if data.description is not None:
            activity.description = data.description
        if data.scheduled_at is not None:
            activity.scheduled_at = data.scheduled_at
        if data.due_at is not None:
            activity.due_at = data.due_at
        if data.duration_minutes is not None:
            activity.duration_minutes = data.duration_minutes
        if data.priority is not None:
            activity.priority = data.priority
        if data.contact_id is not None:
            activity.contact_id = data.contact_id
        if data.account_id is not None:
            activity.account_id = data.account_id
        if data.opportunity_id is not None:
            activity.opportunity_id = data.opportunity_id
        if data.owner_id is not None:
            activity.owner_id = data.owner_id
        if data.status is not None:
            activity.status = data.status
            activity.completed_at = (
                datetime.now(timezone.utc) if data.status == ActivityStatus.COMPLETED else None
            )

        await self._validate_activity_instance(activity)
        activity.updated_by = updater_id
        await self.db.flush()
        await self.audit.log(
            entity_type="activity",
            entity_id=activity.id,
            action="update",
            user_id=updater_id,
            old_values=old,
            new_values={"title": activity.title, "status": activity.status},
        )
        return await self.get(activity.id)

    async def complete(
        self, activity_id: UUID, data: ActivityComplete, actor_id: Optional[UUID] = None
    ) -> Activity:
        activity = await self.get(activity_id)
        activity.status = ActivityStatus.COMPLETED
        activity.completed_at = data.completed_at or datetime.now(timezone.utc)
        activity.updated_by = actor_id
        await self.db.flush()
        await self.audit.log(
            entity_type="activity",
            entity_id=activity.id,
            action="complete",
            user_id=actor_id,
            new_values={"completed_at": activity.completed_at.isoformat()},
        )
        return await self.get(activity.id)

    async def _ensure_active_type(self, activity_type_id: UUID) -> ActivityType:
        activity_type = await self.get_type(activity_type_id)
        if not activity_type.is_active:
            raise HTTPException(status_code=400, detail="Tipo de atividade está inativo")
        return activity_type

    async def _validate_links(self, data: ActivityCreate) -> None:
        await self._ensure_active_type(data.activity_type_id)
        await self._validate_related_entities(
            contact_id=data.contact_id,
            account_id=data.account_id,
            opportunity_id=data.opportunity_id,
        )

    async def _validate_activity_instance(self, activity: Activity) -> None:
        if activity.kind == ActivityKind.ACTIVITY:
            if activity.contact_id is None:
                raise HTTPException(status_code=400, detail="Atividades exigem contato vinculado")
            if activity.scheduled_at is None:
                raise HTTPException(status_code=400, detail="Atividades exigem data/hora de registro")
        if activity.kind == ActivityKind.TASK:
            if activity.contact_id is None and activity.opportunity_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="Tarefas exigem contato ou oportunidade vinculada",
                )
            if activity.due_at is None:
                raise HTTPException(status_code=400, detail="Tarefas exigem data/hora de vencimento")

        await self._validate_related_entities(
            contact_id=activity.contact_id,
            account_id=activity.account_id,
            opportunity_id=activity.opportunity_id,
        )

    async def _validate_related_entities(
        self,
        *,
        contact_id: Optional[UUID],
        account_id: Optional[UUID],
        opportunity_id: Optional[UUID],
    ) -> None:
        contact = None
        account = None
        opportunity = None

        if contact_id:
            from app.modules.contacts.models import Contact

            contact = (
                await self.db.execute(
                    select(Contact).where(Contact.id == contact_id, Contact.is_active == True)
                )
            ).scalar_one_or_none()
            if not contact:
                raise HTTPException(status_code=404, detail="Contato não encontrado ou inativo")

        if account_id:
            from app.modules.accounts.models import Account

            account = (
                await self.db.execute(
                    select(Account).where(Account.id == account_id, Account.is_active == True)
                )
            ).scalar_one_or_none()
            if not account:
                raise HTTPException(status_code=404, detail="Conta não encontrada ou inativa")

        if opportunity_id:
            from app.modules.opportunities.models import Opportunity

            opportunity = (
                await self.db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
            ).scalar_one_or_none()
            if not opportunity:
                raise HTTPException(status_code=404, detail="Oportunidade não encontrada")

        if opportunity and contact and opportunity.contact_id != contact.id:
            raise HTTPException(
                status_code=400,
                detail="Contato informado não corresponde à oportunidade vinculada",
            )
        if opportunity and account and opportunity.account_id != account.id:
            raise HTTPException(
                status_code=400,
                detail="Conta informada não corresponde à oportunidade vinculada",
            )
