import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.email import SMTPEmailService
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
    hash_password,
    verify_password,
)
from app.modules.audit.service import AuditService
from app.modules.auth.models import PasswordResetToken, Permission, Role, RoleName, User
from app.modules.auth.schemas import (
    LoginRequest,
    RoleCreate,
    RoleUpdate,
    TokenResponse,
    UserCreate,
    UserUpdate,
)


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        audit: AuditService,
        email_service: SMTPEmailService | None = None,
    ):
        self.db = db
        self.audit = audit
        self.email_service = email_service or SMTPEmailService()

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    async def login(
        self,
        data: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        result = await self.db.execute(
            select(User)
            .where(User.email == self._normalize_email(data.email))
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            entity_id = user.id if user else uuid.uuid4()
            await self.audit.log(
                entity_type="user",
                entity_id=entity_id,
                action="login_failed",
                ip_address=ip_address,
                user_agent=user_agent,
                new_values={"email": data.email},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail ou senha invalidos",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inativo",
            )

        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="login",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        token_data = {"sub": str(user.id), "email": user.email}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresh invalido ou expirado",
        )
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise credentials_exception
            user_id: str = payload.get("sub")
            if not user_id:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        result = await self.db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise credentials_exception

        token_data = {"sub": str(user.id), "email": user.email}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

    async def forgot_password(self, email: str) -> str | None:
        result = await self.db.execute(
            select(User).where(User.email == self._normalize_email(email))
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None

        token_str = generate_reset_token()
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_rate_limit_minutes
        )
        reset_token = PasswordResetToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token=token_str,
            expires_at=expires,
        )
        self.db.add(reset_token)
        await self.db.flush()

        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="password_reset_requested",
            new_values={"email": email},
        )
        await self.email_service.send_password_reset_email(user.email, token_str)

        if settings.app_env.lower() != "production":
            return token_str
        return None

    async def reset_password(self, token: str, new_password: str) -> None:
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token or reset_token.used_at is not None:
            raise HTTPException(status_code=400, detail="Token invalido ou ja utilizado")

        if reset_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Token expirado")

        result = await self.db.execute(select(User).where(User.id == reset_token.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        user.password_hash = hash_password(new_password)
        reset_token.used_at = datetime.now(timezone.utc)

        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="password_reset",
        )

    async def create_user(self, data: UserCreate, creator_id: Optional[UUID] = None) -> User:
        normalized_email = self._normalize_email(data.email)
        result = await self.db.execute(select(User).where(User.email == normalized_email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="E-mail ja cadastrado")

        user = User(
            id=uuid.uuid4(),
            name=data.name,
            email=normalized_email,
            password_hash=hash_password(data.password),
        )
        if data.role_ids:
            roles_result = await self.db.execute(
                select(Role).where(Role.id.in_(data.role_ids), Role.is_active == True)
            )
            user.roles = list(roles_result.scalars().all())
        else:
            user.roles = []

        self.db.add(user)
        await self.db.flush()

        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="create",
            user_id=creator_id,
            new_values={"name": user.name, "email": user.email},
        )
        return user

    async def get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        return user

    async def list_users(self, page: int = 1, per_page: int = 20):
        from app.shared.pagination import PaginationParams

        params = PaginationParams(page=page, per_page=per_page)
        query = select(User).options(selectinload(User.roles))
        count = (
            await self.db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()
        query = query.offset(params.offset).limit(params.per_page)
        result = await self.db.execute(query)
        return result.scalars().all(), count

    async def update_user(
        self, user_id: UUID, data: UserUpdate, updater_id: Optional[UUID] = None
    ) -> User:
        user = await self.get_user(user_id)
        old = {"name": user.name, "email": user.email, "is_active": user.is_active}

        if data.name is not None:
            user.name = data.name
        if data.email is not None:
            normalized_email = self._normalize_email(data.email)
            result = await self.db.execute(
                select(User).where(User.email == normalized_email, User.id != user_id)
            )
            if result.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="E-mail ja cadastrado")
            user.email = normalized_email
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.role_ids is not None:
            roles_result = await self.db.execute(
                select(Role).where(Role.id.in_(data.role_ids), Role.is_active == True)
            )
            user.roles = list(roles_result.scalars().all())

        await self.db.flush()
        await self.db.refresh(user)
        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="update",
            user_id=updater_id,
            old_values=old,
            new_values={"name": user.name, "email": user.email, "is_active": user.is_active},
        )
        return user

    async def deactivate_user(self, user_id: UUID, actor_id: Optional[UUID] = None) -> None:
        user = await self.get_user(user_id)
        user.is_active = False
        await self.audit.log(
            entity_type="user",
            entity_id=user.id,
            action="delete",
            user_id=actor_id,
        )

    async def create_role(self, data: RoleCreate, creator_id: Optional[UUID] = None) -> Role:
        result = await self.db.execute(select(Role).where(Role.name == data.name))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Papel ja existe")

        role = Role(id=uuid.uuid4(), name=data.name, description=data.description)
        role.permissions = [
            Permission(
                id=uuid.uuid4(),
                role_id=role.id,
                module=permission.module,
                can_create=permission.can_create,
                can_read=permission.can_read,
                can_update=permission.can_update,
                can_delete=permission.can_delete,
            )
            for permission in data.permissions
        ]
        self.db.add(role)
        await self.db.flush()
        await self.audit.log(
            entity_type="role",
            entity_id=role.id,
            action="create",
            user_id=creator_id,
            new_values={"name": role.name},
        )
        return role

    async def list_roles(self):
        result = await self.db.execute(
            select(Role).where(Role.is_active == True).options(selectinload(Role.permissions))
        )
        return result.scalars().all()

    async def get_role(self, role_id: UUID) -> Role:
        result = await self.db.execute(
            select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
        )
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Papel nao encontrado")
        return role

    async def update_role(
        self, role_id: UUID, data: RoleUpdate, updater_id: Optional[UUID] = None
    ) -> Role:
        role = await self.get_role(role_id)
        old_name = role.name

        if data.name is not None:
            role.name = data.name
        if data.description is not None:
            role.description = data.description
        if data.is_active is not None:
            role.is_active = data.is_active
        if data.permissions is not None:
            for permission in role.permissions:
                await self.db.delete(permission)
            role.permissions = [
                Permission(
                    id=uuid.uuid4(),
                    role_id=role.id,
                    module=permission.module,
                    can_create=permission.can_create,
                    can_read=permission.can_read,
                    can_update=permission.can_update,
                    can_delete=permission.can_delete,
                )
                for permission in data.permissions
            ]

        await self.db.flush()
        await self.db.refresh(role)
        await self.audit.log(
            entity_type="role",
            entity_id=role.id,
            action="update",
            user_id=updater_id,
            old_values={"name": old_name},
            new_values={"name": role.name},
        )
        return role

    async def delete_role(self, role_id: UUID, actor_id: Optional[UUID] = None) -> None:
        role = await self.get_role(role_id)
        role.is_active = False
        await self.audit.log(
            entity_type="role",
            entity_id=role.id,
            action="delete",
            user_id=actor_id,
        )

    async def seed_default_roles(self) -> None:
        modules = [
            "contacts",
            "accounts",
            "activities",
            "opportunities",
            "pipeline",
            "reports",
            "admin",
            "audit",
        ]

        default_roles = [
            {
                "name": RoleName.ADMIN,
                "description": "Administrador com acesso total",
                "perms": {module: (True, True, True, True) for module in modules},
            },
            {
                "name": RoleName.MANAGER,
                "description": "Gestor comercial",
                "perms": {
                    "contacts": (True, True, True, False),
                    "accounts": (True, True, True, False),
                    "activities": (True, True, True, False),
                    "opportunities": (True, True, True, False),
                    "pipeline": (True, True, True, False),
                    "reports": (False, True, False, False),
                    "admin": (False, True, False, False),
                    "audit": (False, True, False, False),
                },
            },
            {
                "name": RoleName.SELLER,
                "description": "Vendedor",
                "perms": {
                    "contacts": (True, True, True, False),
                    "accounts": (True, True, True, False),
                    "activities": (True, True, True, False),
                    "opportunities": (True, True, True, False),
                    "pipeline": (False, True, True, False),
                    "reports": (False, True, False, False),
                    "admin": (False, False, False, False),
                    "audit": (False, False, False, False),
                },
            },
            {
                "name": RoleName.VIEWER,
                "description": "Visualizador (somente leitura)",
                "perms": {module: (False, True, False, False) for module in modules},
            },
        ]

        for role_def in default_roles:
            role_result = await self.db.execute(select(Role).where(Role.name == role_def["name"]))
            role = role_result.scalar_one_or_none()

            if role is None:
                role = Role(
                    id=uuid.uuid4(),
                    name=role_def["name"],
                    description=role_def["description"],
                )
                self.db.add(role)
            else:
                role.description = role_def["description"]

            permissions_result = await self.db.execute(
                select(Permission).where(Permission.role_id == role.id)
            )
            existing_permissions = {
                permission.module: permission for permission in permissions_result.scalars().all()
            }

            for module, permissions in role_def["perms"].items():
                permission = existing_permissions.get(module)
                if permission is None:
                    permission = Permission(
                        id=uuid.uuid4(),
                        role_id=role.id,
                        module=module,
                    )
                    self.db.add(permission)
                    existing_permissions[module] = permission

                permission.can_create = permissions[0]
                permission.can_read = permissions[1]
                permission.can_update = permissions[2]
                permission.can_delete = permissions[3]

        await self.db.flush()
