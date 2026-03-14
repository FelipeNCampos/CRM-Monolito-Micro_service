from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SalesDashboardFilters(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    team: Optional[str] = None
    owner_id: Optional[UUID] = None
    refresh_interval_seconds: int = Field(60, ge=5, le=3600)


class PipelineReportFilters(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    team: Optional[str] = None
    owner_id: Optional[UUID] = None


class ActivityReportFilters(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    team: Optional[str] = None
    owner_id: Optional[UUID] = None
    activity_type_id: Optional[UUID] = None


class StageReportRow(BaseModel):
    stage_id: UUID
    stage_name: str
    count: int
    total_value: Decimal


class SalesDashboardResponse(BaseModel):
    generated_at: datetime
    filters: SalesDashboardFilters
    active_opportunities_count: int
    active_opportunities_value: Decimal
    forecast_revenue: Decimal
    won_deals_count: int
    won_deals_value: Decimal
    conversion_rate: Decimal
    stage_breakdown: list[StageReportRow]


class PipelineReportResponse(BaseModel):
    generated_at: datetime
    filters: PipelineReportFilters
    total_count: int
    total_value: Decimal
    rows: list[StageReportRow]


class ActivityVolumeRow(BaseModel):
    owner_id: Optional[UUID]
    owner_name: str
    activity_type_id: UUID
    activity_type_name: str
    activities_count: int
    tasks_count: int
    completed_tasks_count: int


class ActivityIndicators(BaseModel):
    total_activities: int
    total_tasks: int
    completed_tasks: int
    task_completion_rate: Decimal
    activities_per_opportunity: Decimal


class ActivitiesReportResponse(BaseModel):
    generated_at: datetime
    filters: ActivityReportFilters
    indicators: ActivityIndicators
    rows: list[ActivityVolumeRow]
