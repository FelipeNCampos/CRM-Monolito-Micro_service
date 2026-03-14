from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.activities.models import Activity, ActivityKind, ActivityStatus, ActivityType
from app.modules.auth.models import Role, User
from app.modules.opportunities.models import Opportunity, OpportunityStatus, PipelineStage
from app.modules.reports.schemas import (
    ActivitiesReportResponse,
    ActivityIndicators,
    ActivityReportFilters,
    ActivityVolumeRow,
    PipelineReportFilters,
    PipelineReportResponse,
    SalesDashboardFilters,
    SalesDashboardResponse,
    StageReportRow,
)

ZERO = Decimal("0.00")


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_sales_dashboard(
        self, filters: SalesDashboardFilters
    ) -> SalesDashboardResponse:
        team_user_ids = await self._get_team_user_ids(filters.team)
        active_opportunities = await self._list_opportunities(
            owner_id=filters.owner_id,
            team_user_ids=team_user_ids,
            status=OpportunityStatus.ACTIVE,
            from_date=filters.from_date,
            to_date=filters.to_date,
            use_closed_period=False,
        )
        won_opportunities = await self._list_opportunities(
            owner_id=filters.owner_id,
            team_user_ids=team_user_ids,
            status=OpportunityStatus.WON,
            from_date=filters.from_date,
            to_date=filters.to_date,
            use_closed_period=True,
        )
        lost_opportunities = await self._list_opportunities(
            owner_id=filters.owner_id,
            team_user_ids=team_user_ids,
            status=OpportunityStatus.LOST,
            from_date=filters.from_date,
            to_date=filters.to_date,
            use_closed_period=True,
        )

        stage_breakdown = self._build_stage_rows(
            stages=await self._list_active_stages(),
            opportunities=active_opportunities,
        )
        total_closed = len(won_opportunities) + len(lost_opportunities)
        conversion_rate = self._quantize(
            (Decimal(len(won_opportunities)) / Decimal(total_closed) * Decimal("100"))
            if total_closed
            else ZERO
        )

        return SalesDashboardResponse(
            generated_at=datetime.now(timezone.utc),
            filters=filters,
            active_opportunities_count=len(active_opportunities),
            active_opportunities_value=self._sum_values(active_opportunities),
            forecast_revenue=self._forecast_value(active_opportunities),
            won_deals_count=len(won_opportunities),
            won_deals_value=self._sum_values(won_opportunities),
            conversion_rate=conversion_rate,
            stage_breakdown=stage_breakdown,
        )

    async def get_pipeline_report(
        self, filters: PipelineReportFilters
    ) -> PipelineReportResponse:
        team_user_ids = await self._get_team_user_ids(filters.team)
        opportunities = await self._list_opportunities(
            owner_id=filters.owner_id,
            team_user_ids=team_user_ids,
            status=OpportunityStatus.ACTIVE,
            from_date=filters.from_date,
            to_date=filters.to_date,
            use_closed_period=False,
        )
        rows = self._build_stage_rows(
            stages=await self._list_active_stages(),
            opportunities=opportunities,
        )
        return PipelineReportResponse(
            generated_at=datetime.now(timezone.utc),
            filters=filters,
            total_count=sum(row.count for row in rows),
            total_value=self._quantize(sum(row.total_value for row in rows)),
            rows=rows,
        )

    async def export_pipeline_csv(self, filters: PipelineReportFilters) -> str:
        report = await self.get_pipeline_report(filters)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["stage_name", "count", "total_value"])
        for row in report.rows:
            writer.writerow([row.stage_name, row.count, f"{row.total_value:.2f}"])
        return output.getvalue()

    async def get_activities_report(
        self, filters: ActivityReportFilters
    ) -> ActivitiesReportResponse:
        team_user_ids = await self._get_team_user_ids(filters.team)
        activities = await self._list_activities(
            owner_id=filters.owner_id,
            team_user_ids=team_user_ids,
            activity_type_id=filters.activity_type_id,
            from_date=filters.from_date,
            to_date=filters.to_date,
        )
        owner_names = await self._get_owner_names(
            {activity.owner_id for activity in activities if activity.owner_id is not None}
        )

        grouped: dict[tuple[UUID | None, UUID], dict] = defaultdict(
            lambda: {
                "activities_count": 0,
                "tasks_count": 0,
                "completed_tasks_count": 0,
            }
        )
        for activity in activities:
            key = (activity.owner_id, activity.activity_type_id)
            grouped[key]["owner_id"] = activity.owner_id
            grouped[key]["owner_name"] = owner_names.get(activity.owner_id, "Sem responsável")
            grouped[key]["activity_type_id"] = activity.activity_type.id
            grouped[key]["activity_type_name"] = activity.activity_type.name
            grouped[key]["activities_count"] += 1
            if activity.kind == ActivityKind.TASK:
                grouped[key]["tasks_count"] += 1
                if activity.status == ActivityStatus.COMPLETED:
                    grouped[key]["completed_tasks_count"] += 1

        rows = [
            ActivityVolumeRow(**row)
            for row in sorted(
                grouped.values(),
                key=lambda item: (item["owner_name"], item["activity_type_name"]),
            )
        ]

        total_tasks = sum(1 for activity in activities if activity.kind == ActivityKind.TASK)
        completed_tasks = sum(
            1
            for activity in activities
            if activity.kind == ActivityKind.TASK
            and activity.status == ActivityStatus.COMPLETED
        )
        distinct_opportunities = {
            activity.opportunity_id for activity in activities if activity.opportunity_id is not None
        }
        activities_per_opportunity = self._quantize(
            (Decimal(len(activities)) / Decimal(len(distinct_opportunities)))
            if distinct_opportunities
            else ZERO
        )
        task_completion_rate = self._quantize(
            (Decimal(completed_tasks) / Decimal(total_tasks) * Decimal("100"))
            if total_tasks
            else ZERO
        )

        return ActivitiesReportResponse(
            generated_at=datetime.now(timezone.utc),
            filters=filters,
            indicators=ActivityIndicators(
                total_activities=len(activities),
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                task_completion_rate=task_completion_rate,
                activities_per_opportunity=activities_per_opportunity,
            ),
            rows=rows,
        )

    async def export_activities_csv(self, filters: ActivityReportFilters) -> str:
        report = await self.get_activities_report(filters)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "owner_name",
                "activity_type_name",
                "activities_count",
                "tasks_count",
                "completed_tasks_count",
            ]
        )
        for row in report.rows:
            writer.writerow(
                [
                    row.owner_name,
                    row.activity_type_name,
                    row.activities_count,
                    row.tasks_count,
                    row.completed_tasks_count,
                ]
            )
        return output.getvalue()

    async def _list_active_stages(self) -> list[PipelineStage]:
        result = await self.db.execute(
            select(PipelineStage)
            .where(PipelineStage.is_active == True)
            .order_by(PipelineStage.order, PipelineStage.name)
        )
        return result.scalars().all()

    async def _list_opportunities(
        self,
        *,
        owner_id: UUID | None,
        team_user_ids: set[UUID] | None,
        status: OpportunityStatus,
        from_date: date | None,
        to_date: date | None,
        use_closed_period: bool,
    ) -> list[Opportunity]:
        if team_user_ids == set():
            return []

        query = (
            select(Opportunity)
            .where(Opportunity.status == status)
            .options(selectinload(Opportunity.stage))
        )
        if owner_id is not None:
            query = query.where(Opportunity.owner_id == owner_id)
        if team_user_ids is not None:
            query = query.where(Opportunity.owner_id.in_(team_user_ids))

        if use_closed_period:
            if from_date is not None:
                query = query.where(Opportunity.closed_at >= self._start_of_day(from_date))
            if to_date is not None:
                query = query.where(Opportunity.closed_at <= self._end_of_day(to_date))
        else:
            if from_date is not None:
                query = query.where(Opportunity.close_date >= from_date)
            if to_date is not None:
                query = query.where(Opportunity.close_date <= to_date)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _list_activities(
        self,
        *,
        owner_id: UUID | None,
        team_user_ids: set[UUID] | None,
        activity_type_id: UUID | None,
        from_date: date | None,
        to_date: date | None,
    ) -> list[Activity]:
        if team_user_ids == set():
            return []

        reference_at = func.coalesce(
            Activity.completed_at,
            Activity.due_at,
            Activity.scheduled_at,
            Activity.created_at,
        )
        query = (
            select(Activity)
            .options(selectinload(Activity.activity_type))
            .order_by(Activity.created_at)
        )
        if owner_id is not None:
            query = query.where(Activity.owner_id == owner_id)
        if team_user_ids is not None:
            query = query.where(Activity.owner_id.in_(team_user_ids))
        if activity_type_id is not None:
            query = query.where(Activity.activity_type_id == activity_type_id)
        if from_date is not None:
            query = query.where(reference_at >= self._start_of_day(from_date))
        if to_date is not None:
            query = query.where(reference_at <= self._end_of_day(to_date))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _get_team_user_ids(self, team: str | None) -> set[UUID] | None:
        if not team:
            return None

        result = await self.db.execute(
            select(User.id)
            .join(User.roles)
            .where(Role.name == team, Role.is_active == True)
        )
        return set(result.scalars().all())

    async def _get_owner_names(self, owner_ids: set[UUID]) -> dict[UUID, str]:
        if not owner_ids:
            return {}
        result = await self.db.execute(select(User).where(User.id.in_(owner_ids)))
        return {user.id: user.name for user in result.scalars().all()}

    def _build_stage_rows(
        self, *, stages: list[PipelineStage], opportunities: list[Opportunity]
    ) -> list[StageReportRow]:
        grouped: dict[UUID, list[Opportunity]] = defaultdict(list)
        for opportunity in opportunities:
            grouped[opportunity.stage_id].append(opportunity)

        rows = []
        for stage in stages:
            stage_opportunities = grouped.get(stage.id, [])
            rows.append(
                StageReportRow(
                    stage_id=stage.id,
                    stage_name=stage.name,
                    count=len(stage_opportunities),
                    total_value=self._sum_values(stage_opportunities),
                )
            )
        return rows

    def _sum_values(self, opportunities: list[Opportunity]) -> Decimal:
        return self._quantize(sum((opportunity.value or Decimal("0")) for opportunity in opportunities))

    def _forecast_value(self, opportunities: list[Opportunity]) -> Decimal:
        total = Decimal("0")
        for opportunity in opportunities:
            value = opportunity.value or Decimal("0")
            probability = opportunity.probability or Decimal("0")
            total += value * probability / Decimal("100")
        return self._quantize(total)

    def _quantize(self, value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _start_of_day(self, value: date) -> datetime:
        return datetime.combine(value, time.min, tzinfo=timezone.utc)

    def _end_of_day(self, value: date) -> datetime:
        return datetime.combine(value, time.max, tzinfo=timezone.utc)
