"""API users: the record, the store interface, and a short-lived lookup cache."""



import time
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    role: str
    is_active: bool
    key_hint: str | None = None


class UserStore(Protocol):
    async def get_by_key_hash(self, key_hash: str) -> UserRecord | None: ...

    async def ping(self) -> None:
        """Raise UserStoreError if the store cannot be reached."""

    async def close(self) -> None: ...


class CachedUserStore:
    """Wraps a store with a TTL cache, so a request does not hit Oracle every time.

    Misses are cached too, which stops a flood of random keys from reaching the
    database. The price: a key that is disabled (or newly created) is only noticed
    after ``ttl`` seconds. Set USER_CACHE_TTL_SECONDS=0 for no caching.
    """

    def __init__(
        self,
        store: UserStore,
        ttl_seconds: float,
        *,
        max_entries: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._store = store
        self._ttl = ttl_seconds
        self._max = max_entries
        self._clock = clock
        self._entries: dict[str, tuple[float, UserRecord | None]] = {}

    async def get_by_key_hash(self, key_hash: str) -> UserRecord | None:
        if self._ttl <= 0:
            return await self._store.get_by_key_hash(key_hash)
        now = self._clock()
        hit = self._entries.get(key_hash)
        if hit is not None and hit[0] > now:
            return hit[1]
        user = await self._store.get_by_key_hash(key_hash)  # errors are not cached
        if len(self._entries) >= self._max:
            self._entries = {k: v for k, v in self._entries.items() if v[0] > now}
            if len(self._entries) >= self._max:
                self._entries.clear()
        self._entries[key_hash] = (now + self._ttl, user)
        return user

    async def ping(self) -> None:
        await self._store.ping()

    async def close(self) -> None:
        await self._store.close()
