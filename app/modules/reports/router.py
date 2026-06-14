from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.modules.reports.schemas import (
    ActivitiesReportResponse,
    ActivityReportFilters,
    PipelineReportFilters,
    PipelineReportResponse,
    SalesDashboardFilters,
    SalesDashboardResponse,
)
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["Relatórios"])


def _svc(db: AsyncSession) -> ReportService:
    return ReportService(db)


@router.get(
    "/sales-dashboard",
    response_model=SalesDashboardResponse,
    dependencies=[Depends(require_permission("reports", "read"))],
)
async def get_sales_dashboard(
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: date | None = None,
    to_date: date | None = None,
    team: str | None = Query(
        None,
        description="Papel do responsável usado como proxy de equipe nesta fase.",
    ),
    owner_id: UUID | None = None,
    refresh_interval_seconds: int = Query(60, ge=5, le=3600),
):
    filters = SalesDashboardFilters(
        from_date=from_date,
        to_date=to_date,
        team=team,
        owner_id=owner_id,
        refresh_interval_seconds=refresh_interval_seconds,
    )
    return await _svc(db).get_sales_dashboard(filters)


@router.get(
    "/pipeline",
    response_model=PipelineReportResponse,
    dependencies=[Depends(require_permission("reports", "read"))],
)
async def get_pipeline_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: date | None = None,
    to_date: date | None = None,
    team: str | None = Query(
        None,
        description="Papel do responsável usado como proxy de equipe nesta fase.",
    ),
    owner_id: UUID | None = None,
):
    filters = PipelineReportFilters(
        from_date=from_date,
        to_date=to_date,
        team=team,
        owner_id=owner_id,
    )
    return await _svc(db).get_pipeline_report(filters)


@router.get(
    "/pipeline/export",
    dependencies=[Depends(require_permission("reports", "read"))],
)
async def export_pipeline_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: date | None = None,
    to_date: date | None = None,
    team: str | None = Query(
        None,
        description="Papel do responsável usado como proxy de equipe nesta fase.",
    ),
    owner_id: UUID | None = None,
):
    filters = PipelineReportFilters(
        from_date=from_date,
        to_date=to_date,
        team=team,
        owner_id=owner_id,
    )
    content = await _svc(db).export_pipeline_csv(filters)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pipeline-report.csv"'},
    )


@router.get(
    "/activities",
    response_model=ActivitiesReportResponse,
    dependencies=[Depends(require_permission("reports", "read"))],
)
async def get_activities_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: date | None = None,
    to_date: date | None = None,
    team: str | None = Query(
        None,
        description="Papel do responsável usado como proxy de equipe nesta fase.",
    ),
    owner_id: UUID | None = None,
    activity_type_id: UUID | None = None,
):
    filters = ActivityReportFilters(
        from_date=from_date,
        to_date=to_date,
        team=team,
        owner_id=owner_id,
        activity_type_id=activity_type_id,
    )
    return await _svc(db).get_activities_report(filters)


@router.get(
    "/activities/export",
    dependencies=[Depends(require_permission("reports", "read"))],
)
async def export_activities_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: date | None = None,
    to_date: date | None = None,
    team: str | None = Query(
        None,
        description="Papel do responsável usado como proxy de equipe nesta fase.",
    ),
    owner_id: UUID | None = None,
    activity_type_id: UUID | None = None,
):
    filters = ActivityReportFilters(
        from_date=from_date,
        to_date=to_date,
        team=team,
        owner_id=owner_id,
        activity_type_id=activity_type_id,
    )
    content = await _svc(db).export_activities_csv(filters)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="activities-report.csv"'},
    )
