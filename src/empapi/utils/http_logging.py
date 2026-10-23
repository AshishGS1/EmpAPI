"""One-line, grep-friendly request logs in key=value style (same idea as empmcp's).

These helpers only log; the middleware calls them once per request stage.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping


def log_request_started(
    log: logging.Logger,
    method: str,
    path: str,
    request_id: str,
    client: str,
    query: Mapping[str, Any],
) -> None:
    log.info(
        "Request called.",
        extra={
            "event": "request_started",
            "status": "CALLED",
            "request_id": request_id,
            "method": method,
            "path": path,
            "client": client,
            "query": dict(query),
        },
    )


def log_request_completed(
    log: logging.Logger,
    method: str,
    route: str,
    request_id: str,
    http_status: int,
    user: str,
    role: str,
    duration_ms: float,
) -> None:
    log.info(
        "Request complete.",
        extra={
            "event": "request_completed",
            "request_id": request_id,
            "method": method,
            "route": route,
            "status": "OK",
            "http_status": http_status,
            "user": user,
            "role": role,
            "duration_ms": duration_ms,
        },
    )


def log_request_failed(
    log: logging.Logger,
    method: str,
    route: str,
    request_id: str,
    http_status: int,
    user: str,
    role: str,
    duration_ms: float,
    *,
    code: str,
    message: str,
    exc: BaseException | None = None,
) -> None:
    """4xx is logged as WARNING (the caller's mistake), 5xx as ERROR. A traceback is
    attached only when ``exc`` is given (unexpected exceptions)."""
    level = logging.WARNING if http_status < 500 else logging.ERROR
    log.log(
        level,
        "Request FAILED.",
        extra={
            "event": "request_failed",
            "request_id": request_id,
            "method": method,
            "route": route,
            "status": "error",
            "http_status": http_status,
            "user": user,
            "role": role,
            "duration_ms": duration_ms,
            "error_code": code,
            "error_message": message,
        },
        exc_info=exc,
    )


