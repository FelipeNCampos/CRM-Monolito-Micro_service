"""
CRM Backend - Monolito com estrutura para migração a microserviços
Fase 1 MVP: Autenticação, Contatos, Contas, Oportunidades, Pipeline
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.docs import (
    build_postman_collection,
    build_redoc_page,
    build_swagger_ui_with_postman_button,
)

from app.core.config import settings

logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description=(
        "CRM Backend · MVP Fase 1\n\n"
        "## Módulos disponíveis\n"
        "- **Autenticação & RBAC** — Login JWT, recuperação de senha, perfis de acesso\n"
        "- **Contatos** — CRUD de pessoas físicas / prospects\n"
        "- **Contas** — Gestão de empresas com hierarquia matriz/filial\n"
        "- **Oportunidades & Pipeline** — Funil de vendas com visualização Kanban\n"
        "- **Auditoria** — Rastreabilidade de operações críticas (NFR-003)\n"
    ),
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# ──────────────── CORS ────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────── Routers ────────────────
from app.modules.auth.router import router as auth_router
from app.modules.contacts.router import router as contacts_router
from app.modules.accounts.router import router as accounts_router
from app.modules.activities.router import router as activities_router
from app.modules.opportunities.router import router as opportunities_router
from app.modules.audit.router import router as audit_router

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(contacts_router, prefix=settings.api_prefix)
app.include_router(accounts_router, prefix=settings.api_prefix)
app.include_router(activities_router, prefix=settings.api_prefix)
app.include_router(opportunities_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)


# ──────────────── Health Check ────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "0.1.0", "env": settings.app_env}


@app.get("/docs", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url=f"{settings.api_prefix}/docs")


@app.get(f"{settings.api_prefix}/docs", include_in_schema=False)
async def custom_swagger_docs(request: Request):
    return build_swagger_ui_with_postman_button(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        postman_collection_url=str(request.url_for("download_postman_collection")),
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_redirect():
    return RedirectResponse(url=f"{settings.api_prefix}/redoc")


@app.get(f"{settings.api_prefix}/redoc", include_in_schema=False)
async def custom_redoc():
    return build_redoc_page(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
    )


@app.get("/openapi.json", include_in_schema=False)
async def openapi_redirect():
    return RedirectResponse(url=f"{settings.api_prefix}/openapi.json")


@app.get(
    f"{settings.api_prefix}/postman-collection.json",
    include_in_schema=False,
    name="download_postman_collection",
)
async def download_postman_collection(request: Request):
    collection = build_postman_collection(
        openapi_schema=app.openapi(),
        base_url=str(request.base_url).rstrip("/"),
    )
    return JSONResponse(
        content=collection,
        headers={
            "Content-Disposition": 'attachment; filename="crm-backend-postman-collection.json"'
        },
    )


@app.get(f"{settings.api_prefix}/health", tags=["Health"])
async def health_check_v1():
    return {"status": "ok", "version": "0.1.0", "env": settings.app_env}


# ──────────────── Startup ────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("Iniciando CRM Backend...")
    await _seed_initial_data()
    logger.info("CRM Backend pronto.")


async def _seed_initial_data():
    """Cria papéis padrão e usuário admin inicial se necessário."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.modules.auth.models import User, Role, RoleName
    from app.modules.auth.service import AuthService
    from app.modules.auth.schemas import UserCreate
    from app.modules.activities.service import ActivityService
    from app.modules.audit.service import AuditService

    async with AsyncSessionLocal() as db:
        try:
            audit = AuditService(db)
            auth = AuthService(db, audit)
            activities = ActivityService(db, audit)

            # Seed default roles
            await auth.seed_default_roles()
            await activities.seed_default_types()

            # Create initial admin user if no users exist
            result = await db.execute(select(User))
            if not result.scalar_one_or_none():
                admin_role = (
                    await db.execute(select(Role).where(Role.name == RoleName.ADMIN))
                ).scalar_one_or_none()

                admin_role_id = [admin_role.id] if admin_role else []
                await auth.create_user(
                    UserCreate(
                        name="Administrador",
                        email="admin@gmail.com",
                        password="Coto1423",
                        role_ids=admin_role_id,
                    )
                )
                logger.info(
                    "Usuário admin padrão criado: admin@gmail.com / Coto1423 "
                    "— TROQUE A SENHA em produção!"
                )

            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.warning(f"Seed falhou (pode ser normal em primeira execução): {exc}")
