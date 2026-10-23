"""Validate what MCP returned against our response model."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from empapi.exceptions import UpstreamError
from empapi.utils.logging_config import get_logger

logger = get_logger("services")

M = TypeVar("M", bound=BaseModel)


def parse_result(model: type[M], tool: str, payload: dict[str, Any]) -> M:
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        # The MCP server and this API disagree about a response shape: our bug to fix,
        # not the caller's. Log the fields at fault (never the values: they may be salaries).
        logger.error(
            "MCP result does not match the response model",
            extra={"tool": tool, "problems": [list(e["loc"]) for e in exc.errors()]},
        )
        raise UpstreamError(
            "The employee service returned an unexpected response",
            code="UPSTREAM_CONTRACT_ERROR",
        ) from exc
