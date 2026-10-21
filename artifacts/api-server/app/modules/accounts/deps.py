"""Who is calling? Every protected route depends on `User` (anyone signed in) or `Manager`."""

from typing import Annotated

from fastapi import Depends, Header

from app.core.db import DB
from app.core.errors import Forbidden, Unauthorized
from app.modules.accounts.service import user_for_token
from app.modules.people.models import Employee


def bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Please sign in.")
    return authorization[7:].strip()


def current_user(db: DB, token: Annotated[str, Depends(bearer_token)]) -> Employee:
    user = user_for_token(db, token)
    if user is None:
        raise Unauthorized("Your session has expired. Please sign in again.")
    return user


def require_manager(user: Annotated[Employee, Depends(current_user)]) -> Employee:
    if not user.is_manager:
        raise Forbidden("Only managers can do this.")
    return user


User = Annotated[Employee, Depends(current_user)]
Manager = Annotated[Employee, Depends(require_manager)]
Token = Annotated[str, Depends(bearer_token)]
