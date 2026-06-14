"""Testes dos endpoints de atividades e follow-ups."""

import uuid
from datetime import date, datetime, timedelta, timezone


async def _get_activity_type_id(client, admin_headers, name: str) -> str:
    response = await client.get("/api/v1/activity-types", headers=admin_headers)
    assert response.status_code == 200, response.text
    activity_type = next((item for item in response.json() if item["name"] == name), None)
    assert activity_type is not None, f"Tipo `{name}` não encontrado"
    return activity_type["id"]


async def _make_contact(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    response = await client.post(
        "/api/v1/contacts",
        json={"name": f"Act Contact {suffix}", "email": f"act_contact_{suffix}@test.com"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _make_account(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    response = await client.post(
        "/api/v1/accounts",
        json={"name": f"Act Account {suffix}"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _make_stage(client, admin_headers, order=1):
    response = await client.post(
        "/api/v1/pipeline/stages",
        json={
            "name": f"Act Stage {uuid.uuid4().hex[:6]}",
            "order": order,
            "probability": "35.00",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _make_opportunity(client, admin_headers, stage_id: str, contact_id: str, account_id: str):
    response = await client.post(
        "/api/v1/opportunities",
        json={
            "title": f"Act Opp {uuid.uuid4().hex[:6]}",
            "stage_id": stage_id,
            "contact_id": contact_id,
            "account_id": account_id,
            "value": "2000.00",
            "close_date": (date.today() + timedelta(days=15)).isoformat(),
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_list_default_activity_types(client, admin_headers):
    response = await client.get("/api/v1/activity-types", headers=admin_headers)
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert {"Ligação", "Reunião", "E-mail", "Follow-up"}.issubset(names)


async def test_create_activity_with_history_links(client, admin_headers):
    activity_type_id = await _get_activity_type_id(client, admin_headers, "Ligação")
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    stage = await _make_stage(client, admin_headers)
    opportunity = await _make_opportunity(
        client, admin_headers, stage["id"], contact["id"], account["id"]
    )

    response = await client.post(
        "/api/v1/activities",
        json={
            "title": "Ligação de diagnóstico",
            "activity_type_id": activity_type_id,
            "kind": "activity",
            "contact_id": contact["id"],
            "account_id": account["id"],
            "opportunity_id": opportunity["id"],
            "scheduled_at": "2026-03-14T10:00:00Z",
            "duration_minutes": 25,
            "description": "Alinhamento inicial do escopo",
        },
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Ligação de diagnóstico"
    assert body["contact"]["id"] == contact["id"]
    assert body["account"]["id"] == account["id"]
    assert body["opportunity"]["id"] == opportunity["id"]
    assert body["activity_type"]["name"] == "Ligação"


async def test_list_activities_in_chronological_order(client, admin_headers):
    activity_type_id = await _get_activity_type_id(client, admin_headers, "Reunião")
    contact = await _make_contact(client, admin_headers)

    older = await client.post(
        "/api/v1/activities",
        json={
            "title": "Reunião 1",
            "activity_type_id": activity_type_id,
            "kind": "activity",
            "contact_id": contact["id"],
            "scheduled_at": "2026-03-10T09:00:00Z",
        },
        headers=admin_headers,
    )
    newer = await client.post(
        "/api/v1/activities",
        json={
            "title": "Reunião 2",
            "activity_type_id": activity_type_id,
            "kind": "activity",
            "contact_id": contact["id"],
            "scheduled_at": "2026-03-11T09:00:00Z",
        },
        headers=admin_headers,
    )
    assert older.status_code == 201, older.text
    assert newer.status_code == 201, newer.text

    response = await client.get(
        f"/api/v1/activities?contact_id={contact['id']}&sort_order=asc",
        headers=admin_headers,
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert titles[:2] == ["Reunião 1", "Reunião 2"]


async def test_overdue_follow_up_is_highlighted(client, admin_headers):
    activity_type_id = await _get_activity_type_id(client, admin_headers, "Follow-up")
    contact = await _make_contact(client, admin_headers)
    due_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    response = await client.post(
        "/api/v1/activities",
        json={
            "title": "Retornar proposta",
            "activity_type_id": activity_type_id,
            "kind": "task",
            "contact_id": contact["id"],
            "due_at": due_at,
            "priority": "high",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text

    listing = await client.get(
        "/api/v1/activities?kind=task&overdue_only=true",
        headers=admin_headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1
    assert any(item["is_overdue"] is True for item in listing.json()["items"])


async def test_complete_follow_up_records_completion_time(client, admin_headers):
    activity_type_id = await _get_activity_type_id(client, admin_headers, "Follow-up")
    contact = await _make_contact(client, admin_headers)
    create_response = await client.post(
        "/api/v1/activities",
        json={
            "title": "Enviar retorno",
            "activity_type_id": activity_type_id,
            "kind": "task",
            "contact_id": contact["id"],
            "due_at": "2026-03-20T14:00:00Z",
            "priority": "medium",
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201, create_response.text
    activity_id = create_response.json()["id"]

    complete_response = await client.patch(
        f"/api/v1/activities/{activity_id}/complete",
        json={},
        headers=admin_headers,
    )
    assert complete_response.status_code == 200
    body = complete_response.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    assert body["is_overdue"] is False


async def test_create_activity_no_permission(client, no_perm_headers):
    response = await client.get("/api/v1/activity-types", headers=no_perm_headers)
    assert response.status_code == 403
