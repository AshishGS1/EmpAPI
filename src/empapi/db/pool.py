"""Oracle connection pool for the api_users table (python-oracledb, thin mode, async)."""



from contextlib import asynccontextmanager
from typing import AsyncIterator

import oracledb

from empapi.config import Settings
from empapi.exceptions import UserStoreError
from empapi.utils.logging_config import get_logger

logger = get_logger("db.pool")

_POOL_TIMEOUT_CODES = {"DPY-4005", "ORA-24459"}


def oracle_error_code(exc: oracledb.Error) -> str:
    error = exc.args[0] if exc.args else None
    return getattr(error, "full_code", "") or ""


class OraclePool:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pool: oracledb.AsyncConnectionPool | None = None

    async def connect(self) -> None:
        s = self._settings
        try:
            self._pool = oracledb.create_pool_async(
                user=s.oracle_user,
                password=s.oracle_password.get_secret_value(),
                dsn=s.oracle_dsn,
                getmode=oracledb.POOL_GETMODE_TIMEDWAIT,
                wait_timeout=s.oracle_pool_timeout_seconds * 1000,
            )
            async with self._pool.acquire() as connection:
                await connection.ping()
        except oracledb.Error as exc:
            self._pool = None
            code = oracle_error_code(exc)
            logger.error(
                "Failed to initialise Oracle pool",
                extra={"oracle_code": code, "dsn": s.oracle_dsn},
                exc_info=True,
            )
            raise UserStoreError(
                "Could not connect to the Oracle database", details={"oracle_code": code}
            ) from exc
        logger.info("Oracle pool ready", extra={"dsn": s.oracle_dsn})

    async def close(self) -> None:
        if self._pool is not None:
            try:
                await self._pool.close(force=True)
            except oracledb.Error:
                logger.warning("Error while closing Oracle pool", exc_info=True)
            finally:
                self._pool = None

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[oracledb.AsyncConnection]:
        if self._pool is None:
            raise UserStoreError("Database pool is not initialised")
        pool = self._pool
        try:
            connection = await pool.acquire()
        except oracledb.Error as exc:
            code = oracle_error_code(exc)
            logger.error("Could not acquire connection", extra={"oracle_code": code}, exc_info=True)
            message = (
                "No database connection became available in time"
                if code in _POOL_TIMEOUT_CODES
                else "Could not obtain a database connection"
            )
            raise UserStoreError(message, details={"oracle_code": code}) from exc
        try:
            yield connection
        finally:
            try:
                await pool.release(connection)
            except oracledb.Error:
                logger.warning("Error releasing connection to pool", exc_info=True)
