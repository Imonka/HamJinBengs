"""Sign-in and self-service account shapes."""

from __future__ import annotations

from typing import Literal

from app.core.schema import Model, StrictInput


Access = Literal["manager", "staff"]


class LoginInput(Model):
    email: str
    pin: str


class CurrentUser(Model):
    id: int
    name: str
    email: str
    phone: str | None
    access: Access
    role_id: int | None
    role_name: str | None


class LoginResult(Model):
    token: str
    user: CurrentUser


class ChangePinInput(Model):
    current_pin: str
    new_pin: str


class ProfileInput(StrictInput):
    """The signed-in person's own details. The current PIN is required to change the email,
    because the email is what they sign in with."""

    name: str
    email: str
    phone: str | None = None
    current_pin: str | None = None
