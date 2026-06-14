"""Testes dos endpoints de autenticacao."""

import uuid

from fastapi import HTTPException
from jose import jwt

from app.core.config import settings

TEST_ADMIN_EMAIL = "admin@gmail.com"
TEST_ADMIN_PASSWORD = "Coto1423"


async def test_login_success(client):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_returns_valid_jwt_payload(client):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    token = response.json()["access_token"]
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["type"] == "access"
    assert "sub" in payload
    assert "exp" in payload
    assert "email" in payload


async def test_login_wrong_password(client):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": TEST_ADMIN_EMAIL, "password": "WrongPass!1"},
    )
    assert response.status_code == 401


async def test_login_nonexistent_email(client):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "ghost_nobody@nowhere.com", "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 401


async def test_login_inactive_user(client, admin_headers):
    email = f"inactive_{uuid.uuid4().hex[:8]}@test.com"
    created = await client.post(
        "/api/v1/admin/users",
        json={"name": "Inactive", "email": email, "password": "Test@1234", "role_ids": []},
        headers=admin_headers,
    )
    user_id = created.json()["id"]
    await client.delete(f"/api/v1/admin/users/{user_id}", headers=admin_headers)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Test@1234"},
    )
    assert response.status_code in (401, 403)


async def test_login_requires_form_data_not_json(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 422


async def test_refresh_token_success(client, admin_refresh_token):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": admin_refresh_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_refresh_token_invalid(client):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401


async def test_refresh_using_access_token_fails(client, admin_headers):
    access_token = admin_headers["Authorization"].split(" ")[1]
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


async def test_forgot_password_known_email_returns_token_and_sends_email(client, monkeypatch):
    sent_email = {}

    async def fake_send_password_reset_email(self, recipient_email: str, reset_token: str):
        sent_email["recipient_email"] = recipient_email
        sent_email["reset_token"] = reset_token

    monkeypatch.setattr(
        "app.core.email.SMTPEmailService.send_password_reset_email",
        fake_send_password_reset_email,
    )

    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": TEST_ADMIN_EMAIL},
    )
    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert "dev_token" in body
    assert body["dev_token"] is not None
    assert sent_email["recipient_email"] == TEST_ADMIN_EMAIL
    assert sent_email["reset_token"] == body["dev_token"]


async def test_forgot_password_unknown_email_still_returns_200(client):
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "ghost_nobody_123@nowhere.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert body["dev_token"] is None


async def test_forgot_password_returns_503_when_smtp_fails(client, monkeypatch):
    async def fake_send_password_reset_email(self, recipient_email: str, reset_token: str):
        raise HTTPException(status_code=503, detail="Falha ao enviar email de recuperacao")

    monkeypatch.setattr(
        "app.core.email.SMTPEmailService.send_password_reset_email",
        fake_send_password_reset_email,
    )

    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": TEST_ADMIN_EMAIL},
    )
    assert response.status_code == 503


async def test_reset_password_success(client, monkeypatch):
    async def fake_send_password_reset_email(self, recipient_email: str, reset_token: str):
        return None

    monkeypatch.setattr(
        "app.core.email.SMTPEmailService.send_password_reset_email",
        fake_send_password_reset_email,
    )

    forgot = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": TEST_ADMIN_EMAIL},
    )
    reset_token = forgot.json()["dev_token"]

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "NewPass@99"},
    )
    assert response.status_code == 204

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": TEST_ADMIN_EMAIL, "password": "NewPass@99"},
    )
    assert login.status_code == 200


async def test_reset_password_invalid_token(client):
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "totally_invalid_token_xyz", "new_password": "NewPass@99"},
    )
    assert response.status_code in (400, 404)


async def test_reset_password_token_reuse_fails(client, monkeypatch):
    async def fake_send_password_reset_email(self, recipient_email: str, reset_token: str):
        return None

    monkeypatch.setattr(
        "app.core.email.SMTPEmailService.send_password_reset_email",
        fake_send_password_reset_email,
    )

    forgot = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": TEST_ADMIN_EMAIL},
    )
    token = forgot.json()["dev_token"]

    await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPass@99"},
    )
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherPass@88"},
    )
    assert response.status_code == 400


async def test_reset_password_weak_password_fails(client, monkeypatch):
    async def fake_send_password_reset_email(self, recipient_email: str, reset_token: str):
        return None

    monkeypatch.setattr(
        "app.core.email.SMTPEmailService.send_password_reset_email",
        fake_send_password_reset_email,
    )

    forgot = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": TEST_ADMIN_EMAIL},
    )
    token = forgot.json()["dev_token"]
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "weak"},
    )
    assert response.status_code == 422


async def test_get_me_authenticated(client, admin_headers):
    response = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == TEST_ADMIN_EMAIL
    assert "id" in body
    assert "roles" in body
    assert "admin" in body["roles"]


async def test_get_me_unauthenticated(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_get_me_invalid_token(client):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally.invalid.token"},
    )
    assert response.status_code == 401


async def test_get_me_malformed_header(client):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "NotBearer token"},
    )
    assert response.status_code == 401


async def test_change_password_success(client, admin_headers):
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_ADMIN_PASSWORD, "new_password": "Changed@1234"},
        headers=admin_headers,
    )
    assert response.status_code == 204


async def test_change_password_wrong_current(client, admin_headers):
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongPass!9", "new_password": "Changed@1234"},
        headers=admin_headers,
    )
    assert response.status_code == 400


async def test_change_password_unauthenticated(client):
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_ADMIN_PASSWORD, "new_password": "Changed@1234"},
    )
    assert response.status_code == 401


async def test_change_password_weak_new_password(client, admin_headers):
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_ADMIN_PASSWORD, "new_password": "weak"},
        headers=admin_headers,
    )
    assert response.status_code == 422
