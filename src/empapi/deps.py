"""FastAPI dependencies: API-key authentication, scope checks, and shared services.

Order of checks for an authenticated endpoint:
    1. X-API-Key present and well-formed       -> else 401 (no database hit for garbage)
    2. key known and user active               -> else 401 INVALID_API_KEY
    3. role known, endpoint's scope held       -> else 403 (before any MCP call)
"""



from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader

from empapi.context import current_request_info
from empapi.exceptions import (
    AuthenticationRequiredError,
    InvalidApiKeyError,
    PermissionDeniedError,
)
from empapi.mcp.gateway import McpGateway
from empapi.security.api_keys import hash_api_key
from empapi.security.scopes import scopes_for_role
from empapi.security.users import UserStore
from empapi.utils.logging_config import get_logger

logger = get_logger("auth")

# auto_error=False so a missing key becomes our own 401 body, and the header still
# shows up as the "Authorize" button in /docs.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    role: str
    scopes: frozenset[str]


def get_gateway(request: Request) -> McpGateway:
    return request.app.state.gateway


async def get_current_user(
    request: Request, api_key: str | None = Depends(api_key_header)
) -> AuthenticatedUser:
    if not api_key:
        raise AuthenticationRequiredError()

    store: UserStore = request.app.state.user_store
    record = await store.get_by_key_hash(hash_api_key(api_key))
    if record is None or not record.is_active:
        raise InvalidApiKeyError()

    info = current_request_info()
    if info is not None:  # so the request log line names the user even on a 403/429
        info.user_id, info.role = record.user_id, record.role

    scopes = scopes_for_role(record.role)
    if scopes is None:
        logger.error(
            "User has a role this API does not know",
            extra={"user": record.user_id, "role": record.role},
        )
        raise PermissionDeniedError("Your account has no recognised role")
    return AuthenticatedUser(record.user_id, record.role, scopes)


def require_scopes(*needed: str) -> Callable[..., AuthenticatedUser]:
    """Dependency factory: the user must hold every scope in ``needed``."""
    needed_set = frozenset(needed)

    async def dependency(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        missing = needed_set - user.scopes
        if missing:
            raise PermissionDeniedError(
                f"Your role does not allow this: missing {', '.join(sorted(missing))}",
                details={"required_scopes": sorted(needed_set), "missing_scopes": sorted(missing)},
            )
        return user

    return dependency
