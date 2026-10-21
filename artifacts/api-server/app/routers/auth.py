from fastapi import APIRouter, Response

from .. import schemas
from ..deps import DB, Token, User
from ..services import auth

router = APIRouter(tags=["auth"])


def current_user_out(u) -> schemas.CurrentUser:
    return schemas.CurrentUser(id=u.id, name=u.name, email=u.email, access=u.access, role_id=u.role_id,
                               role_name=u.role.name if u.role else None)


@router.get("/healthz", response_model=schemas.HealthStatus, tags=["health"])
def health():
    return {"status": "ok"}


@router.post("/auth/login", response_model=schemas.LoginResult)
def login(data: schemas.LoginInput, db: DB):
    token, user = auth.login(db, data.email, data.pin)
    return schemas.LoginResult(token=token, user=current_user_out(user))


@router.post("/auth/logout", status_code=204)
def logout(db: DB, token: Token):
    auth.logout(db, token)
    return Response(status_code=204)


@router.get("/auth/me", response_model=schemas.CurrentUser)
def me(user: User):
    return current_user_out(user)


@router.put("/auth/pin", status_code=204)
def change_pin(data: schemas.ChangePinInput, db: DB, user: User):
    auth.change_pin(db, user, data.current_pin, data.new_pin)
    return Response(status_code=204)
