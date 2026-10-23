"""Oracle-backed store of API users (table ``api_users``, see ../EmpMCP/sql/03_api_users.sql)."""

from __future__ import annotations

import oracledb

from empapi.config import Settings
from empapi.db.pool import OraclePool, oracle_error_code
from empapi.exceptions import InvalidRequestError, UserStoreError
from empapi.security.users import UserRecord
from empapi.utils.logging_config import get_logger

logger = get_logger("db.users")


class OracleUserStore:
    def __init__(self, settings: Settings) -> None:
        self._pool = OraclePool(settings)

    async def connect(self) -> None:
        await self._pool.connect()

    async def close(self) -> None:
        await self._pool.close()

    async def ping(self) -> None:
        async with self._pool.acquire() as connection:
            try:
                await connection.ping()
            except oracledb.Error as exc:
                raise UserStoreError(
                    "Database ping failed", details={"oracle_code": oracle_error_code(exc)}
                ) from exc

    # read path (every authenticated request)
    async def get_by_key_hash(self, key_hash: str) -> UserRecord | None:
        rows = await self._query(
            "SELECT user_id, role, is_active, key_hint FROM api_users "
            "WHERE key_hash = :key_hash",
            {"key_hash": key_hash},
        )
        if not rows:
            return None
        user_id, role, is_active, hint = rows[0]
        return UserRecord(user_id, role, bool(is_active), hint)

    # admin path
    async def list_users(self) -> list[UserRecord]:
        rows = await self._query(
            "SELECT user_id, role, is_active, key_hint FROM api_users ORDER BY user_id"
        )
        return [UserRecord(u, r, bool(a), h) for u, r, a, h in rows]

    async def create_user(self, user_id: str, role: str, key_hash: str, hint: str) -> None:
        try:
            await self._execute(
                "INSERT INTO api_users (user_id, key_hash, key_hint, role) "
                "VALUES (:user_id, :key_hash, :hint, :role)",
                {"user_id": user_id, "key_hash": key_hash, "hint": hint, "role": role},
            )
        except _Duplicate as exc:
            raise InvalidRequestError(f"User '{user_id}' already exists") from exc

    async def set_active(self, user_id: str, active: bool) -> bool:
        return await self._execute(
            "UPDATE api_users SET is_active = :active WHERE user_id = :user_id",
            {"user_id": user_id, "active": int(active)},
        )

    # helpers
    async def _query(self, sql: str, params: dict | None = None) -> list[tuple]:
        async with self._pool.acquire() as connection:
            try:
                with connection.cursor() as cursor:
                    await cursor.execute(sql, params or {})
                    return await cursor.fetchall()
            except oracledb.Error as exc:
                raise self._wrap(exc) from exc

    async def _execute(self, sql: str, params: dict) -> bool:
        """Run a write and commit; True if at least one row was affected."""
        async with self._pool.acquire() as connection:
            try:
                with connection.cursor() as cursor:
                    await cursor.execute(sql, params)
                    affected = cursor.rowcount
                await connection.commit()
                return affected > 0
            except oracledb.Error as exc:
                if oracle_error_code(exc) == "ORA-00001":  # unique constraint
                    raise _Duplicate() from exc
                raise self._wrap(exc) from exc

    @staticmethod
    def _wrap(exc: oracledb.Error) -> UserStoreError:
        code = oracle_error_code(exc)
        logger.error("User store query failed", extra={"oracle_code": code}, exc_info=True)
        return UserStoreError("User lookup failed", details={"oracle_code": code})


class _Duplicate(Exception):
    pass
