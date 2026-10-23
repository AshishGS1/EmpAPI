"""App factory and lifespan.

Startup order, each step failing fast with a clear message:
    1. logging
    2. signing key (a missing or weak key stops the app here)
    3. Oracle pool for the API-user table
    4. MCP client: connect, list_tools, check the expected tools exist
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from empapi.config import get_settings
from empapi.exceptions import ApiError
from empapi.handlers import register_exception_handlers
from empapi.db.user_store import OracleUserStore
from empapi.mcp.gateway import McpGateway
from empapi.mcp.tokens import TokenMinter
from empapi.middleware.logging import RequestLoggingMiddleware
from empapi.routers import departments, employees, health, tools
from empapi.security.users import CachedUserStore, UserStore
from empapi.utils.logging_config import configure_logging, get_logger

logger = get_logger("app")


def create_app() -> FastAPI:
    """create fastapi app, the store is Oracle and the gateway talks to the real MCP server."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings.log_level, settings.log_json)
        store: UserStore | None = None
        mcp_gateway: McpGateway | None = None
        try:
            minter = TokenMinter.from_settings(settings)
            oracle = OracleUserStore(settings)
            await oracle.connect()
            store = CachedUserStore(oracle, settings.user_cache_ttl_seconds)
            mcp_gateway = McpGateway(settings, minter)
            await mcp_gateway.start()
        except ApiError as exc:
            logger.critical(
                "Startup failed: [%s] %s", exc.code, exc.message,
                extra={"error_code": exc.code, "details": exc.details},
            )
            if store is not None:
                await store.close()
            raise

        app.state.settings = settings
        app.state.user_store = store
        app.state.gateway = mcp_gateway
        logger.info("EmpAPI ready", extra={"mcp_url": settings.mcp_url})
        try:
            yield
        finally:
            await mcp_gateway.stop()
            await store.close()
            logger.info("EmpAPI stopped")

    app = FastAPI(
        title="EmpAPI",
        version="0.1.0",
        description="Employee directory API. Send your key in the X-API-Key header.",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.add_middleware(RequestLoggingMiddleware)  # outermost: sees every request
    app.include_router(employees.router)
    app.include_router(departments.router)
    app.include_router(tools.router)
    app.include_router(health.router)
    return app
