"""Validate what MCP returned against our response model."""



from typing import Any

from pydantic import BaseModel, ValidationError

from empapi.exceptions import UpstreamError
from empapi.utils.logging_config import get_logger

logger = get_logger("services")

def parse_result(model: type[BaseModel], tool: str, payload: dict[str, Any]) -> BaseModel:
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        # The MCP server and this API disagree about a response shape: our bug to fix
        logger.error(
            "MCP result does not match the response model",
            extra={"tool": tool, "problems": [list(e["loc"]) for e in exc.errors()]},
        )
        raise UpstreamError(
            "The service returned an unexpected response",
            code="UPSTREAM_CONTRACT_ERROR",
        ) from exc
