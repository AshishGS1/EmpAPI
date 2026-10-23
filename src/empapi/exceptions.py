"""Custom exception hierarchy.

Every error the API raises on purpose is an ``ApiError`` carrying a stable ``code``
and an HTTP ``status``; one handler (handlers.py) turns it into the JSON error body
"""



from http import HTTPStatus
from typing import Any, Mapping


class ApiError(Exception):
    code: str = "API_ERROR"
    status: int = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int | None = None,
        details: dict[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status is not None:
            self.status = int(status)
        self.details = details or {}
        self.headers = dict(headers or {})


class ConfigurationError(ApiError):
    code = "CONFIGURATION_ERROR"


# caller's dependenies
class AuthenticationRequiredError(ApiError):
    code = "AUTHENTICATION_REQUIRED"
    status = HTTPStatus.UNAUTHORIZED

    def __init__(self, message: str = "Send your API key in the X-API-Key header", **kw):
        kw.setdefault("headers", {"WWW-Authenticate": "ApiKey"})
        super().__init__(message, **kw)


class InvalidApiKeyError(AuthenticationRequiredError):
    code = "INVALID_API_KEY"

    def __init__(self, **kw):
        super().__init__("The API key is invalid or has been disabled", **kw)


class PermissionDeniedError(ApiError):
    code = "PERMISSION_DENIED"
    status = HTTPStatus.FORBIDDEN


class InvalidRequestError(ApiError):
    code = "INVALID_REQUEST"
    status = HTTPStatus.BAD_REQUEST


# our dependencies
class UserStoreError(ApiError):
    """The Oracle table of API users could not be reached."""

    code = "USER_STORE_UNAVAILABLE"
    status = HTTPStatus.SERVICE_UNAVAILABLE


class McpToolError(ApiError):
    """The MCP tool ran and refused: not found, bad input, a database problem there.
    Code and status are taken from the MCP error message."""

    code = "MCP_TOOL_ERROR"


class UpstreamError(ApiError):
    """The MCP server answered, but not in a way we can pass on."""

    code = "UPSTREAM_ERROR"
    status = HTTPStatus.BAD_GATEWAY


class UpstreamUnavailableError(UpstreamError):
    code = "UPSTREAM_UNAVAILABLE"
    status = HTTPStatus.SERVICE_UNAVAILABLE


class UpstreamTimeoutError(UpstreamError):
    code = "UPSTREAM_TIMEOUT"
    status = HTTPStatus.GATEWAY_TIMEOUT
