"""Per-request state shared by the logging middleware, dependencies and handlers"""



from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class RequestInfo:
    request_id: str
    user_id: str | None = None
    role: str | None = None
    error_code: str | None = None
    error_message: str | None = None


request_info_var: ContextVar[RequestInfo | None] = ContextVar("request_info", default=None)


def current_request_info() -> RequestInfo | None:
    return request_info_var.get()


def current_request_id() -> str:
    """The id of the request being handled; used as the MCP token's ``jti``."""
    info = request_info_var.get()
    return info.request_id if info else "-"
