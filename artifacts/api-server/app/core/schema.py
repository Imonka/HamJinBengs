"""Base classes for API request/response shapes (camelCase JSON), plus the few shared ones.
Each module keeps its own shapes in its schemas.py; together they match lib/api-spec/openapi.yaml."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StrictInput(Model):
    """Request bodies that must reject unknown fields, so a client can't slip in a field
    (like `access` or `pin`) that the caller isn't allowed to change."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class RowError(Model):
    row: int
    message: str


class HealthStatus(Model):
    status: str
