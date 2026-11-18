"""Login, logout, current-user, registration, and password-recovery routes."""

from fastapi import APIRouter, Depends, Response

from app.api.cookies import set_session_cookies
from app.api.dependencies import (
    CSRF_COOKIE_NAME,
    CurrentUser,
    MailerDep,
    Repos,
    SessionToken,
    SettingsDep,
    require_admin,
    require_csrf,
    require_password_reset_enabled,
    require_registration_enabled,
)
from app.api.schemas import (
    ConfirmRegistrationRequest,
    LoginRequest,
    RegisterRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
    UserOut,
)
from app.domain.models import User, UserId
from app.services import auth
from app.services.password_reset import request_password_reset, request_password_reset_for_user, reset_password
from app.services.registration import confirm_registration, request_registration

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
async def login(body: LoginRequest, response: Response, repos: Repos) -> User:
    session = await auth.login(repos, body.email, body.password)
    user = await repos.users.get_by_id(session.user_id)
    if user is None:
        raise RuntimeError(f"login() returned a session for an unknown user: {session.user_id}")

    set_session_cookies(response, session.token)
    return user


@router.post("/logout", dependencies=[Depends(require_csrf)])
async def logout(response: Response, token: SessionToken, repos: Repos) -> None:
    await auth.logout(repos, token)
    response.delete_cookie(auth.SESSION_COOKIE_NAME)
    response.delete_cookie(CSRF_COOKIE_NAME)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.post("/register", dependencies=[Depends(require_registration_enabled)])
async def register(body: RegisterRequest, repos: Repos, mailer: MailerDep, settings: SettingsDep) -> None:
    await request_registration(
        repos, mailer, body.name, body.email, body.password, frontend_origin=settings.frontend_origin
    )


@router.post("/register/confirm", response_model=UserOut, dependencies=[Depends(require_registration_enabled)])
async def register_confirm(body: ConfirmRegistrationRequest, response: Response, repos: Repos) -> User:
    result = await confirm_registration(repos, body.token)
    set_session_cookies(response, result.session.token)
    return result.user


@router.post("/password-recovery", dependencies=[Depends(require_password_reset_enabled)])
async def request_password_recovery(
    body: RequestPasswordResetRequest, repos: Repos, mailer: MailerDep, settings: SettingsDep
) -> None:
    await request_password_reset(repos, mailer, body.email, frontend_origin=settings.frontend_origin)


@router.post("/password-reset", dependencies=[Depends(require_password_reset_enabled)])
async def reset_password_route(body: ResetPasswordRequest, repos: Repos) -> None:
    await reset_password(repos, body.token, body.new_password)


@router.post("/admin/password-reset/{user_id}", dependencies=[Depends(require_admin), Depends(require_csrf)])
async def admin_trigger_password_reset(user_id: UserId, repos: Repos, mailer: MailerDep, settings: SettingsDep) -> None:
    await request_password_reset_for_user(repos, mailer, user_id, frontend_origin=settings.frontend_origin)
