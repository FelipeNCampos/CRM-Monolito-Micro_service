"""Testes do módulo de relatórios da fase 2."""

import csv
import io
import uuid
from datetime import date, timedelta
from decimal import Decimal


def _as_decimal(value) -> Decimal:
    return Decimal(str(value))


async def _get_role_id(client, admin_headers, name: str) -> str:
    response = await client.get("/api/v1/admin/roles", headers=admin_headers)
    assert response.status_code == 200, response.text
    role = next((item for item in response.json() if item["name"] == name), None)
    assert role is not None, f"Role `{name}` não encontrado"
    return role["id"]


async def _create_role(client, admin_headers, name: str) -> str:
    response = await client.post(
        "/api/v1/admin/roles",
        json={"name": name, "description": "Equipe de relatórios", "permissions": []},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_user(client, admin_headers, *, name: str, role_ids: list[str]) -> dict:
    suffix = uuid.uuid4().hex[:8]
    response = await client.post(
        "/api/v1/admin/users",
        json={
            "name": name,
            "email": f"user_{suffix}@test.com",
            "password": "Test@1234",
            "role_ids": role_ids,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _make_contact(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    response = await client.post(
        "/api/v1/contacts",
        json={"name": f"Rpt Contact {suffix}", "email": f"rpt_contact_{suffix}@test.com"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _make_account(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    response = await client.post(
        "/api/v1/accounts",
        json={"name": f"Rpt Account {suffix}"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _make_stage(client, admin_headers, *, order: int, probability: str = "50.00"):
    response = await client.post(
        "/api/v1/pipeline/stages",
        json={
            "name": f"Rpt Stage {uuid.uuid4().hex[:6]}",
            "order": order,
            "probability": probability,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _make_opportunity(
    client,
    admin_headers,
    *,
    stage_id: str,
    contact_id: str,
    account_id: str,
    owner_id: str,
    value: str,
    probability: str,
    close_date: str,
):
    response = await client.post(
        "/api/v1/opportunities",
        json={
            "title": f"Rpt Opp {uuid.uuid4().hex[:6]}",
            "stage_id": stage_id,
            "contact_id": contact_id,
            "account_id": account_id,
            "owner_id": owner_id,
            "value": value,
            "probability": probability,
            "close_date": close_date,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _close_opportunity(client, admin_headers, opp_id: str, status: str):
    payload = {"status": status}
    if status == "lost":
        payload["lost_reason"] = "Sem fit"
    response = await client.patch(
        f"/api/v1/opportunities/{opp_id}/close",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _get_activity_type_id(client, admin_headers, name: str) -> str:
    response = await client.get("/api/v1/activity-types", headers=admin_headers)
    assert response.status_code == 200, response.text
    activity_type = next((item for item in response.json() if item["name"] == name), None)
    assert activity_type is not None, f"Tipo `{name}` não encontrado"
    return activity_type["id"]


async def _create_activity(
    client,
    admin_headers,
    *,
    title: str,
    activity_type_id: str,
    kind: str,
    owner_id: str,
    contact_id: str,
    opportunity_id: str | None,
    scheduled_at: str | None = None,
    due_at: str | None = None,
):
    payload = {
        "title": title,
        "activity_type_id": activity_type_id,
        "kind": kind,
        "owner_id": owner_id,
        "contact_id": contact_id,
    }
    if opportunity_id is not None:
        payload["opportunity_id"] = opportunity_id
    if scheduled_at is not None:
        payload["scheduled_at"] = scheduled_at
    if due_at is not None:
        payload["due_at"] = due_at

    response = await client.post("/api/v1/activities", json=payload, headers=admin_headers)
    assert response.status_code == 201, response.text
    return response.json()


async def _complete_activity(client, admin_headers, activity_id: str):
    response = await client.patch(
        f"/api/v1/activities/{activity_id}/complete",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_sales_dashboard_reports_metrics_with_team_filter(client, admin_headers):
    seller_role_id = await _get_role_id(client, admin_headers, "seller")
    team_role_name = f"team_{uuid.uuid4().hex[:6]}"
    team_role_id = await _create_role(client, admin_headers, team_role_name)
    seller = await _create_user(
        client,
        admin_headers,
        name="Seller Report",
        role_ids=[seller_role_id, team_role_id],
    )
    other_seller = await _create_user(
        client,
        admin_headers,
        name="Other Seller",
        role_ids=[seller_role_id],
    )

    stage_a = await _make_stage(client, admin_headers, order=1, probability="50.00")
    stage_b = await _make_stage(client, admin_headers, order=2, probability="70.00")
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    period_start = date.today().replace(day=1)
    period_end = period_start + timedelta(days=27)

    await _make_opportunity(
        client,
        admin_headers,
        stage_id=stage_a["id"],
        contact_id=contact["id"],
        account_id=account["id"],
        owner_id=seller["id"],
        value="1000.00",
        probability="50.00",
        close_date=(period_start + timedelta(days=5)).isoformat(),
    )
    won_opp = await _make_opportunity(
        client,
        admin_headers,
        stage_id=stage_b["id"],
        contact_id=contact["id"],
        account_id=account["id"],
        owner_id=seller["id"],
        value="800.00",
        probability="70.00",
        close_date=(period_start + timedelta(days=8)).isoformat(),
    )
    lost_opp = await _make_opportunity(
        client,
        admin_headers,
        stage_id=stage_b["id"],
        contact_id=contact["id"],
        account_id=account["id"],
        owner_id=seller["id"],
        value="400.00",
        probability="20.00",
        close_date=(period_start + timedelta(days=10)).isoformat(),
    )
    await _make_opportunity(
        client,
        admin_headers,
        stage_id=stage_a["id"],
        contact_id=contact["id"],
        account_id=account["id"],
        owner_id=other_seller["id"],
        value="9999.00",
        probability="90.00",
        close_date=(period_start + timedelta(days=12)).isoformat(),
    )
    await _close_opportunity(client, admin_headers, won_opp["id"], "won")
    await _close_opportunity(client, admin_headers, lost_opp["id"], "lost")

    response = await client.get(
        (
            f"/api/v1/reports/sales-dashboard?team={team_role_name}"
            f"&from_date={period_start.isoformat()}&to_date={period_end.isoformat()}"
            "&refresh_interval_seconds=45"
        ),
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["filters"]["team"] == team_role_name
    assert body["filters"]["refresh_interval_seconds"] == 45
    assert body["active_opportunities_count"] == 1
    assert _as_decimal(body["active_opportunities_value"]) == Decimal("1000.00")
    assert _as_decimal(body["forecast_revenue"]) == Decimal("500.00")
    assert body["won_deals_count"] == 1
    assert _as_decimal(body["won_deals_value"]) == Decimal("800.00")
    assert _as_decimal(body["conversion_rate"]) == Decimal("50.00")
    assert any(
        row["stage_id"] == stage_a["id"] and row["count"] == 1
        for row in body["stage_breakdown"]
    )


async def test_sales_dashboard_with_unknown_team_returns_zero_metrics(client, admin_headers):
    response = await client.get(
        "/api/v1/reports/sales-dashboard?team=ghost_team",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["active_opportunities_count"] == 0
    assert _as_decimal(body["active_opportunities_value"]) == Decimal("0.00")
    assert _as_decimal(body["forecast_revenue"]) == Decimal("0.00")
    assert body["won_deals_count"] == 0
    assert _as_decimal(body["won_deals_value"]) == Decimal("0.00")
    assert _as_decimal(body["conversion_rate"]) == Decimal("0.00")


async def test_pipeline_report_and_csv_export(client, admin_headers):
    seller_role_id = await _get_role_id(client, admin_headers, "seller")
    seller = await _create_user(
        client,
        admin_headers,
        name="Pipeline Seller",
        role_ids=[seller_role_id],
    )
    stage_a = await _make_stage(client, admin_headers, order=1, probability="20.00")
    stage_b = await _make_stage(client, admin_headers, order=2, probability="60.00")
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    close_date = (date.today() + timedelta(days=15)).isoformat()

    await _make_opportunity(
        client,
        admin_headers,
        stage_id=stage_a["id"],
        contact_id=contact["id"],
        account_id=account["id"],
        owner_id=seller["id"],
        value="1200.00",
        probability="20.00",
        close_date=close_date,
    )
    await _make_opportunity(
        client,
        admin_headers,
        stage_id=stage_b["id"],
        contact_id=contact["id"],
        account_id=account["id"],
        owner_id=seller["id"],
        value="800.00",
        probability="60.00",
        close_date=close_date,
    )

    report = await client.get(
        f"/api/v1/reports/pipeline?owner_id={seller['id']}",
        headers=admin_headers,
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["total_count"] == 2
    assert _as_decimal(body["total_value"]) == Decimal("2000.00")
    assert any(row["stage_id"] == stage_a["id"] and row["count"] == 1 for row in body["rows"])
    assert any(row["stage_id"] == stage_b["id"] and row["count"] == 1 for row in body["rows"])

    export = await client.get(
        f"/api/v1/reports/pipeline/export?owner_id={seller['id']}",
        headers=admin_headers,
    )
    assert export.status_code == 200
    assert export.headers["content-disposition"] == 'attachment; filename="pipeline-report.csv"'
    rows = list(csv.reader(io.StringIO(export.text)))
    assert rows[0] == ["stage_name", "count", "total_value"]
    assert any(row[0] == stage_a["name"] and row[1] == "1" for row in rows[1:])
    assert any(row[0] == stage_b["name"] and row[1] == "1" for row in rows[1:])


async def test_activities_report_and_csv_export(client, admin_headers):
    seller_role_id = await _get_role_id(client, admin_headers, "seller")
    team_role_name = f"team_{uuid.uuid4().hex[:6]}"
    team_role_id = await _create_role(client, admin_headers, team_role_name)
    seller = await _create_user(
        client,
        admin_headers,
        name="Activity Seller",
        role_ids=[seller_role_id, team_role_id],
    )
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    stage = await _make_stage(client, admin_headers, order=1)
    opportunity = await _make_opportunity(
        client,
        admin_headers,
        stage_id=stage["id"],
        contact_id=contact["id"],
        account_id=account["id"],
        owner_id=seller["id"],
        value="600.00",
        probability="50.00",
        close_date=(date.today() + timedelta(days=7)).isoformat(),
    )
    call_type_id = await _get_activity_type_id(client, admin_headers, "Ligação")
    follow_up_type_id = await _get_activity_type_id(client, admin_headers, "Follow-up")

    await _create_activity(
        client,
        admin_headers,
        title="Call",
        activity_type_id=call_type_id,
        kind="activity",
        owner_id=seller["id"],
        contact_id=contact["id"],
        opportunity_id=opportunity["id"],
        scheduled_at="2026-03-14T10:00:00Z",
    )
    completed_task = await _create_activity(
        client,
        admin_headers,
        title="Done follow-up",
        activity_type_id=follow_up_type_id,
        kind="task",
        owner_id=seller["id"],
        contact_id=contact["id"],
        opportunity_id=opportunity["id"],
        due_at="2026-03-20T10:00:00Z",
    )
    await _create_activity(
        client,
        admin_headers,
        title="Pending follow-up",
        activity_type_id=follow_up_type_id,
        kind="task",
        owner_id=seller["id"],
        contact_id=contact["id"],
        opportunity_id=opportunity["id"],
        due_at="2026-03-22T10:00:00Z",
    )
    await _complete_activity(client, admin_headers, completed_task["id"])

    report = await client.get(
        f"/api/v1/reports/activities?team={team_role_name}",
        headers=admin_headers,
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["indicators"]["total_activities"] == 3
    assert body["indicators"]["total_tasks"] == 2
    assert body["indicators"]["completed_tasks"] == 1
    assert _as_decimal(body["indicators"]["task_completion_rate"]) == Decimal("50.00")
    assert _as_decimal(body["indicators"]["activities_per_opportunity"]) == Decimal("3.00")
    assert any(
        row["owner_name"] == "Activity Seller"
        and row["activity_type_name"] == "Ligação"
        and row["activities_count"] == 1
        for row in body["rows"]
    )
    assert any(
        row["owner_name"] == "Activity Seller"
        and row["activity_type_name"] == "Follow-up"
        and row["tasks_count"] == 2
        and row["completed_tasks_count"] == 1
        for row in body["rows"]
    )

    export = await client.get(
        f"/api/v1/reports/activities/export?team={team_role_name}&activity_type_id={follow_up_type_id}",
        headers=admin_headers,
    )
    assert export.status_code == 200
    assert export.headers["content-disposition"] == 'attachment; filename="activities-report.csv"'
    rows = list(csv.reader(io.StringIO(export.text)))
    assert rows[0] == [
        "owner_name",
        "activity_type_name",
        "activities_count",
        "tasks_count",
        "completed_tasks_count",
    ]
    assert any(row[0] == "Activity Seller" and row[1] == "Follow-up" for row in rows[1:])


async def test_reports_require_authentication_and_permission(client, no_perm_headers):
    no_auth = await client.get("/api/v1/reports/pipeline")
    assert no_auth.status_code == 401

    no_perm = await client.get("/api/v1/reports/activities", headers=no_perm_headers)
    assert no_perm.status_code == 403
