"""Self-service account profile routes - the caller changing their own account's own fields."""

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, Repos
from app.api.schemas import UpdateNameRequest, UserOut
from app.domain.models import User
from app.services.profile import update_my_name

router = APIRouter(tags=["profile"])


@router.put("/users/me/name", response_model=UserOut)
async def put_name(body: UpdateNameRequest, user: CurrentUser, repos: Repos) -> User:
    return await update_my_name(repos, user.id, body.name)
