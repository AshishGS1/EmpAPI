"""Exception handlers: every failure leaves the API in the same JSON shape.
    {"error": {"code": "...", "message": "...", "request_id": "...", "details": {...}}}

Each handler also records the code and message on the RequestInfo, so the logging
middleware's single FAILED line carries them.
"""



from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from empapi.context import current_request_info, current_request_id
from empapi.exceptions import ApiError

_STATUS_CODES = {
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    422: "VALIDATION_ERROR",
}


def error_response(
    status: int,
    code: str,
    message: str,
    *,
    details: dict | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    info = current_request_info()
    if info is not None:
        info.error_code = code
        info.error_message = message
    body: dict = {
        "code": code,
        "message": message,
        "request_id": current_request_id(),
    }
    if details:
        body["details"] = details
    return JSONResponse({"error": body}, status_code=status, headers=headers)


async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
    return error_response(
        exc.status, exc.code, exc.message, details=exc.details, headers=exc.headers
    )


async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Only where and why: never echo the submitted values back
    problems = [
        {"field": ".".join(str(p) for p in err["loc"]), "problem": err["msg"]}
        for err in exc.errors()
    ]
    return error_response(
        422, "VALIDATION_ERROR", "The request parameters are invalid",
        details={"errors": problems},
    )


async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
    return error_response(
        exc.status_code, code, str(exc.detail), headers=getattr(exc, "headers", None)
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
