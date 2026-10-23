"""Models shared across endpoints: tools, health, errors."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolSchema(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any]


class ToolList(BaseModel):
    tools: list[ToolSchema]
    count: int


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthStatus(BaseModel):
    status: str
    checks: dict[str, str] | None = None
