"""
Suite de testes de integracao do CRM Backend.

Por padrao, a suite sobe/reutiliza um PostgreSQL temporario em Docker
para nao depender das credenciais definidas no `.env` local.

Se voce quiser apontar para um banco especifico, defina:

  TEST_POSTGRES_HOST
  TEST_POSTGRES_PORT
  TEST_POSTGRES_DB
  TEST_POSTGRES_USER
  TEST_POSTGRES_PASSWORD
"""

import os
import shutil
import subprocess
import time
import uuid
import asyncio
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _container_exists(name: str) -> bool:
    return _docker("inspect", name).returncode == 0


def _container_running(name: str) -> bool:
    result = _docker("inspect", "-f", "{{.State.Running}}", name)
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def _container_port(name: str) -> str | None:
    result = _docker("port", name, "5432/tcp")
    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            return line.rsplit(":", 1)[-1]
    return None


def _ensure_managed_test_database(
    *,
    db_name: str,
    user: str,
    password: str,
    container_name: str,
) -> tuple[str, str]:
    if not _docker_available():
        raise RuntimeError(
            "Docker nao esta disponivel e nenhum TEST_POSTGRES_* foi definido para os testes."
        )

    if _container_exists(container_name):
        if not _container_running(container_name):
            result = _docker("start", container_name)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    else:
        result = _docker(
            "run",
            "--name",
            container_name,
            "-e",
            f"POSTGRES_DB={db_name}",
            "-e",
            f"POSTGRES_USER={user}",
            "-e",
            f"POSTGRES_PASSWORD={password}",
            "-p",
            "127.0.0.1::5432",
            "-d",
            "postgres:16-alpine",
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    deadline = time.time() + 60
    while time.time() < deadline:
        port = _container_port(container_name)
        if port:
            ready = _docker("exec", container_name, "pg_isready", "-U", user, "-d", db_name)
            if ready.returncode == 0:
                return "127.0.0.1", port
        time.sleep(1)

    raise RuntimeError(f"Banco de teste Docker `{container_name}` nao ficou pronto a tempo.")


_load_dotenv()

test_db_name = os.getenv("TEST_POSTGRES_DB", "crm_test")
test_db_user = os.getenv("TEST_POSTGRES_USER", "crm_user")
test_db_password = os.getenv("TEST_POSTGRES_PASSWORD", "crm_strong_pass_2024")
test_db_container = os.getenv("TEST_POSTGRES_CONTAINER", "crm_test_db_pytest")
test_db_host = os.getenv("TEST_POSTGRES_HOST")
test_db_port = os.getenv("TEST_POSTGRES_PORT")

if not (test_db_host and test_db_port):
    test_db_host, test_db_port = _ensure_managed_test_database(
        db_name=test_db_name,
        user=test_db_user,
        password=test_db_password,
        container_name=test_db_container,
    )

os.environ["POSTGRES_DB"] = test_db_name
os.environ["POSTGRES_HOST"] = test_db_host
os.environ["POSTGRES_PORT"] = test_db_port
os.environ["POSTGRES_USER"] = test_db_user
os.environ["POSTGRES_PASSWORD"] = test_db_password
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ.setdefault("SECRET_KEY", "test-secret-key-change-me-32-chars")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.main import app

TEST_ADMIN_EMAIL = "admin@gmail.com"
TEST_ADMIN_PASSWORD = "Coto1423"


_test_engine = create_async_engine(settings.database_url, echo=False)
_test_db_lock = asyncio.Lock()

_TRUNCATE_ALL = text(
    """
    TRUNCATE TABLE
        audit_logs,
        activities,
        activity_types,
        contact_accounts,
        user_roles,
        permissions,
        password_reset_tokens,
        opportunities,
        contacts,
        accounts,
        pipeline_stages,
        users,
        roles
    RESTART IDENTITY CASCADE
    """
)


@pytest.fixture(scope="session")
async def setup_db():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest.fixture(autouse=True)
async def truncate(setup_db):
    async with _test_db_lock:
        async with _test_engine.begin() as conn:
            await conn.execute(_TRUNCATE_ALL)
        yield


@pytest.fixture
async def client(truncate):
    from app.main import _seed_initial_data

    await _seed_initial_data()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
async def admin_headers(client):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, f"Login do admin falhou: {response.text}"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def admin_refresh_token(client):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, f"Login do admin falhou: {response.text}"
    return response.json()["refresh_token"]


@pytest.fixture
async def no_perm_headers(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    email = f"noperm_{suffix}@test.com"

    role_resp = await client.post(
        "/api/v1/admin/roles",
        json={
            "name": f"empty_role_{suffix}",
            "description": "Papel sem permissoes",
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert role_resp.status_code == 201, role_resp.text
    role_id = role_resp.json()["id"]

    user_resp = await client.post(
        "/api/v1/admin/users",
        json={
            "name": "Sem Permissao",
            "email": email,
            "password": "Test@1234",
            "role_ids": [role_id],
        },
        headers=admin_headers,
    )
    assert user_resp.status_code == 201, user_resp.text

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Test@1234"},
    )
    assert login_resp.status_code == 200, login_resp.text
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
