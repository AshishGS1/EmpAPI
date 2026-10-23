"""Request logging middleware: one CALLED line and one OK/FAILED line per request.

Written as plain ASGI middleware (not Starlette's BaseHTTPMiddleware) so the
ContextVars it sets reach the endpoint and everything that runs under it.
Each response gets an ``X-Request-ID`` header. A caller-supplied ``X-Request-ID`` is
honoured if it is short and plain, so a request can be followed across systems.
"""

from __future__ import annotations

import re
import time
import uuid
from urllib.parse import parse_qsl

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from empapi.context import RequestInfo, request_info_var
from empapi.utils.http_logging import (
    log_request_completed,
    log_request_failed,
    log_request_started,
)
from empapi.utils.logging_config import get_logger, request_id_var

logger = get_logger("http")

REQUEST_ID_HEADER = "X-Request-ID"
# Also the shape the MCP server accepts for a token's jti (1-64 of these characters)
_ACCEPTED_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{8,64}")


def pick_request_id(scope: Scope) -> str:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            if _ACCEPTED_REQUEST_ID.fullmatch(candidate):
                return candidate
            break
    return uuid.uuid4().hex[:16]


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = pick_request_id(scope)
        info = RequestInfo(request_id=request_id)
        info_token = request_info_var.set(info)
        id_token = request_id_var.set(request_id)

        method = scope["method"]
        path = scope["path"]
        client = scope["client"][0] if scope.get("client") else "-"
        started = time.perf_counter()
        response_status: int | None = None

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        def elapsed_ms() -> float:
            return round((time.perf_counter() - started) * 1000, 2)

        def who() -> tuple[str, str]:
            return info.user_id or "-", info.role or "-"

        query = dict(parse_qsl(scope.get("query_string", b"").decode("latin-1")))
        log_request_started(logger, method, path, request_id, client, query)
        try:
            try:
                await self.app(scope, receive, send_with_request_id)
            except Exception as exc:
                user, role = who()
                log_request_failed(
                    logger, method, _route_of(scope), request_id, 500, user, role,
                    elapsed_ms(),
                    code="UNEXPECTED_ERROR", message=f"{type(exc).__name__}: {exc}",
                    exc=exc,
                )
                if response_status is not None:
                    raise  # headers already sent: nothing sensible left to answer
                body = {"error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected server error",
                    "request_id": request_id,
                }}
                await JSONResponse(body, status_code=500)(
                    scope, receive, send_with_request_id
                )
                return

            status = response_status or 500
            user, role = who()
            route = _route_of(scope)
            if status >= 400:
                log_request_failed(
                    logger, method, route, request_id, status, user, role,
                    elapsed_ms(),
                    code=info.error_code or "HTTP_ERROR",
                    message=info.error_message or "",
                )
            else:
                log_request_completed(
                    logger, method, route, request_id, status, user, role,
                    elapsed_ms(),
                )
        finally:
            request_id_var.reset(id_token)
            request_info_var.reset(info_token)


def _route_of(scope: Scope) -> str:
    """The route template ('/employees/{employee_id}'), set once routing has matched.
    It keeps log lines groupable, unlike the concrete path."""
    route = scope.get("route")
    return getattr(route, "path", None) or scope["path"]
