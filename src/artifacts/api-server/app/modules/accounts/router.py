"""/auth: sign in, sign out, who am I, and self-service PIN and profile changes."""

from fastapi import APIRouter, Response

from app.core.db import DB
from app.modules.accounts import schemas, service
from app.modules.accounts.deps import Token, User

router = APIRouter(prefix="/auth", tags=["auth"])


def current_user_out(u) -> schemas.CurrentUser:
    return schemas.CurrentUser(id=u.id, name=u.name, email=u.email, phone=u.phone, access=u.access,
                               role_id=u.role_id, role_name=u.role.name if u.role else None)


@router.post("/login", response_model=schemas.LoginResult)
def login(data: schemas.LoginInput, db: DB):
    token, user = service.login(db, data.email, data.pin)
    return schemas.LoginResult(token=token, user=current_user_out(user))


@router.post("/logout", status_code=204)
def logout(db: DB, token: Token):
    service.logout(db, token)
    return Response(status_code=204)


@router.get("/me", response_model=schemas.CurrentUser)
def me(user: User):
    return current_user_out(user)


@router.put("/pin", status_code=204)
def change_pin(data: schemas.ChangePinInput, db: DB, user: User):
    service.change_pin(db, user, data.current_pin, data.new_pin)
    return Response(status_code=204)


@router.put("/profile", response_model=schemas.CurrentUser)
def update_profile(data: schemas.ProfileInput, db: DB, user: User):
    return current_user_out(service.update_profile(db, user, data))
