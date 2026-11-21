"""Self-service account profile updates - the caller changing their own account's own fields.

No separate `actor_id`/target distinction, unlike app.services.users - there's no "change someone
else's name" here. Admin-driven changes to another user's fields stay in app.services.users.
"""

from app.domain.models import User, UserId
from app.domain.repositories import Repositories
from app.services.errors import UserNotFoundError


async def update_my_name(repos: Repositories, user_id: UserId, name: str) -> User:
    user = await repos.users.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError(user_id)

    await repos.users.update_name(user_id, name)
    return user.model_copy(update={"name": name})
