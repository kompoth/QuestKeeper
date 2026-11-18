"""Admin-only runtime settings and user management routes."""

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUser, MailerDep, Repos, SettingsDep, require_admin, require_csrf
from app.api.schemas import (
    CreateUserRequest,
    RoleUpdate,
    RuntimeSettingsOut,
    RuntimeSettingsUpdate,
    StatusUpdate,
    UserListOut,
    UserOut,
)
from app.domain.models import User, UserId
from app.services.settings import get_runtime_settings, update_runtime_settings
from app.services.users import change_user_role, change_user_status, create_user, list_users

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

DEFAULT_PAGE_SIZE = 20


@router.get("/settings", response_model=RuntimeSettingsOut)
async def get_settings_route(repos: Repos) -> RuntimeSettingsOut:
    settings = await get_runtime_settings(repos)
    return RuntimeSettingsOut.from_settings(settings)


@router.put("/settings", response_model=RuntimeSettingsOut, dependencies=[Depends(require_csrf)])
async def update_settings_route(body: RuntimeSettingsUpdate, repos: Repos) -> RuntimeSettingsOut:
    settings = await update_runtime_settings(repos, body.to_settings())
    return RuntimeSettingsOut.from_settings(settings)


@router.get("/users", response_model=UserListOut)
async def list_users_route(
    repos: Repos, offset: int = 0, limit: int = DEFAULT_PAGE_SIZE, search: str | None = None
) -> UserListOut:
    users, total = await list_users(repos, offset, limit, search)
    return UserListOut(
        users=[
            UserOut(id=u.id, name=u.name, email=u.email, role=u.role, status=u.status, joined_at=u.joined_at)
            for u in users
        ],
        total=total,
    )


@router.put("/users/{user_id}/role", response_model=UserOut, dependencies=[Depends(require_csrf)])
async def change_role_route(user_id: UserId, body: RoleUpdate, repos: Repos, current_user: CurrentUser) -> User:
    return await change_user_role(repos, current_user.id, user_id, body.role)


@router.put("/users/{user_id}/status", response_model=UserOut, dependencies=[Depends(require_csrf)])
async def change_status_route(user_id: UserId, body: StatusUpdate, repos: Repos, current_user: CurrentUser) -> User:
    return await change_user_status(repos, current_user.id, user_id, body.status)


@router.post("/users", response_model=UserOut, dependencies=[Depends(require_csrf)])
async def create_user_route(body: CreateUserRequest, repos: Repos, mailer: MailerDep, settings: SettingsDep) -> User:
    return await create_user(repos, mailer, body.name, body.email, body.role, frontend_origin=settings.frontend_origin)
