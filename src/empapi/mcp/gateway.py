"""The MCP gateway: one shared MCP client, with the caller's token chosen per call.

Why shared: opening a client per request costs ~87 ms (connect + MCP handshake) against
~13 ms for a warm shared one. Why safe: every request sets its token in a ContextVar and
ContextBearerAuth reads it when the HTTP request is made, so concurrent users never
see each other's token. 
"""

from __future__ import annotations

import asyncio
import contextvars
import time
from dataclasses import dataclass
from typing import Any, Iterable

from fastmcp import Client
from fastmcp.client.auth.bearer import BearerAuth
from mcp.shared.exceptions import MCPError

from empapi.config import Settings
from empapi.context import current_request_id
from empapi.exceptions import (
    UpstreamError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from empapi.mcp.errors import to_api_error
from empapi.mcp.tokens import TokenMinter
from empapi.security.scopes import SCOPE_SALARY_READ
from empapi.utils.logging_config import get_logger

logger = get_logger("mcp")

_call_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "mcp_call_token", default=None
)


class ContextBearerAuth(BearerAuth):
    """Sends the token set for the current call; without one, a no-scope bootstrap token."""

    def __init__(self, minter: TokenMinter) -> None:
        super().__init__("unused")
        self._minter = minter

    def auth_flow(self, request):
        token = _call_token.get() or self._minter.mint_bootstrap()
        request.headers["Authorization"] = f"Bearer {token}"
        yield request


@dataclass(frozen=True)
class ToolInfo:
    name: str
    description: str | None
    input_schema: dict[str, Any]


class McpGateway:
    def __init__(self, settings: Settings, minter: TokenMinter) -> None:
        self._settings = settings
        self._minter = minter
        self._client: Client | None = None
        self._tools: list[ToolInfo] = []

    # lifecycle
    async def start(self) -> None:
        """Connect to mcp server."""
        await self._connect()
        logger.info(
            "MCP gateway ready",
            extra={"mcp_url": self._settings.mcp_url, "tools": [t.name for t in self._tools]},
        )

    async def stop(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            await _close_quietly(client)

    @property
    def tools(self) -> list[ToolInfo]:
        return list(self._tools)

    async def ping(self) -> bool:
        """Is the MCP server reachable and answering?"""
        client = self._client
        if client is None:
            return False
        try:
            async with asyncio.timeout(self._settings.mcp_connect_timeout_seconds):
                await client.list_tools()
            return True
        except Exception:
            return False

    async def call_tool(
        self,
        tool: str,
        arguments: dict[str, Any],
        *,
        user_id: str,
        user_scopes: frozenset[str],
        required_scopes: Iterable[str],
    ) -> dict[str, Any]:
        """Call one tool as ``user_id`` and return its structured result.

        The token carries ``required_scopes`` (what this call needs) plus salary:read
        if the user holds it, never the user's other scopes.
        """
        scopes = set(required_scopes)
        if SCOPE_SALARY_READ in user_scopes:
            scopes.add(SCOPE_SALARY_READ)
        token = self._minter.mint(sub=user_id, scopes=scopes, jti=current_request_id())

        ctx_token = _call_token.set(token)
        try:
            result = await self._call_once(tool, arguments)
        finally:
            _call_token.reset(ctx_token)
        if result.is_error:
            text = result.content[0].text if result.content else ""
            raise to_api_error(tool, text)
        if not isinstance(result.structured_content, dict):
            logger.error("MCP tool returned no structured content", extra={"tool": tool})
            raise UpstreamError("The employee service returned an unexpected response")
        return result.structured_content

    async def _call_once(self, tool: str, arguments: dict[str, Any]):
        """One attempt, any failure is reported to the caller."""
        client = self._client
        if client is None:
            raise UpstreamUnavailableError("The service is unavailable")
        try:
            async with asyncio.timeout(self._settings.mcp_call_timeout_seconds):
                return await client.call_tool(tool, arguments, raise_on_error=False)
        except TimeoutError as exc:
            logger.error(
                "MCP call timed out",
                extra={"tool": tool, "timeout_s": self._settings.mcp_call_timeout_seconds},
            )
            raise UpstreamTimeoutError("The service took too long to respond") from exc
        except MCPError as exc:
            if "Connection closed" not in str(exc):
                logger.error(
                    "MCP answered with a protocol error",
                    extra={"tool": tool, "mcp_error": str(exc)},
                )
                raise UpstreamError(
                    "The service rejected the request",
                    code="UPSTREAM_REJECTED",
                ) from exc
            failure: BaseException = exc
        except Exception as exc:  # ConnectError, "not connected", ExceptionGroup, ...
            failure = exc

        logger.warning(
            "MCP transport failure",
            extra={"tool": tool, "error_type": type(failure).__name__},
        )
        raise UpstreamUnavailableError("The service is unavailable") from failure

    async def _connect(self) -> None:
        """Open the client and discover the tools. Called once, from start()."""
        client = Client(
            self._settings.mcp_url,
            auth=ContextBearerAuth(self._minter),
            init_timeout=self._settings.mcp_connect_timeout_seconds,
        )
        # The handshake belongs to no user: do not let a caller's token leak into it
        ctx_token = _call_token.set(None)
        try:
            async with asyncio.timeout(self._settings.mcp_connect_timeout_seconds + 1):
                await client.__aenter__()
                tools = await client.list_tools()
        except Exception as exc:
            await _close_quietly(client)
            logger.error(
                "Cannot connect to the MCP server",
                extra={"mcp_url": self._settings.mcp_url, "error_type": type(exc).__name__},
            )
            raise UpstreamUnavailableError("The service is unavailable") from exc
        finally:
            _call_token.reset(ctx_token)

        self._tools = [
            ToolInfo(t.name, t.description, dict(t.input_schema or {})) for t in tools
        ]
        self._client = client
        logger.info("Connected to the MCP server")


async def _close_quietly(client: Client) -> None:
    try:
        await asyncio.wait_for(client.close(), 2)
    except BaseException as exc:  # a dead connection often fails to close cleanly
        if isinstance(exc, asyncio.CancelledError):
            raise
        logger.debug("Ignored error while closing MCP client: %s", type(exc).__name__)
