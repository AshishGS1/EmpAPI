"""Turning an MCP tool failure into an API error.

The MCP server formats every deliberate error as ``[404 EMPLOYEE_NOT_FOUND] message``
(status, code, message), so the status is read from the text. 
"""



import re
from dataclasses import dataclass

from empapi.exceptions import ApiError, McpToolError, UpstreamError
from empapi.utils.logging_config import get_logger

logger = get_logger("mcp.errors")

_MCP_ERROR = re.compile(r"^\[(\d{3}) ([A-Z][A-Z0-9_]*)\] (.*)$", re.DOTALL)

_PASS_THROUGH = {400, 403, 404, 429, 502, 503}


@dataclass(frozen=True)
class McpErrorInfo:
    status: int
    code: str
    message: str


def parse_mcp_error(text: str) -> McpErrorInfo | None:
    match = _MCP_ERROR.match(text.strip())
    if match is None:
        return None
    return McpErrorInfo(int(match[1]), match[2], match[3])


def to_api_error(tool: str, text: str) -> ApiError:
    info = parse_mcp_error(text)
    if info is None:
        logger.error(
            "MCP tool failed with an unrecognised message",
            extra={"tool": tool, "mcp_text": text[:300]},
        )
        return UpstreamError("The service failed to process the request")

    if info.status == 401:
        logger.error(
            "MCP rejected our token: check the signing key, AUTH_ISSUER and AUTH_AUDIENCE",
            extra={"tool": tool, "mcp_code": info.code},
        )
        return UpstreamError(
            "The service could not authenticate this service",
            code="UPSTREAM_AUTH_ERROR",
        )

    if info.status in _PASS_THROUGH:
        if info.status == 403:
            logger.error(
                "MCP denied a call that FastAPI allowed: scope maps are out of sync",
                extra={"tool": tool, "mcp_message": info.message},
            )
        headers = {"Retry-After": "1"} if info.status == 429 else None
        return McpToolError(info.message, code=info.code, status=info.status, headers=headers)

    logger.error(
        "MCP tool failed with a server error",
        extra={"tool": tool, "mcp_status": info.status, "mcp_code": info.code},
    )
    return UpstreamError("The service failed to process the request")
