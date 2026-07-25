"""
Intelligent Wikipedia cache with TTL namespaces and request deduplication.

If many callers request the same key concurrently, only one upstream fetch
runs; the rest await the shared Future.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional


@dataclass
class _CacheEntry:
    data: Any
    expires_at: float


class WikiCache:
    """In-memory cache + optional /tmp file mirror for warm serverless instances."""

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._store: Dict[str, _CacheEntry] = {}
        self._inflight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        if persist_path is None:
            persist_path = (
                "/tmp/wiki_cache.json"
                if os.environ.get("VERCEL") or os.name != "nt"
                else "wiki_cache.json"
            )
        self._persist_path = persist_path
        self._load_disk()

    # ------------------------------------------------------------------
    # Disk helpers (best-effort; never block correctness)
    # ------------------------------------------------------------------

    def _load_disk(self) -> None:
        if not os.path.exists(self._persist_path):
            return
        try:
            with open(self._persist_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            now = time.time()
            for key, entry in raw.items():
                expires = float(entry.get("expires_at", 0))
                if expires > now:
                    self._store[key] = _CacheEntry(
                        data=entry["data"], expires_at=expires
                    )
        except Exception as exc:  # noqa: BLE001
            print(f"Wiki cache disk load error: {exc}")

    def _save_disk(self) -> None:
        try:
            payload = {
                key: {"data": entry.data, "expires_at": entry.expires_at}
                for key, entry in self._store.items()
                if entry.expires_at > time.time()
            }
            with open(self._persist_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except Exception as exc:  # noqa: BLE001
            print(f"Wiki cache disk write error: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, *, allow_expired: bool = False) -> Any | None:
        """Return cached value or None."""
        entry = self._store.get(key)
        if not entry:
            return None
        if entry.expires_at >= time.time() or allow_expired:
            return entry.data
        return None

    def set(self, key: str, data: Any, ttl_seconds: int) -> None:
        """Store value with TTL and mirror to disk."""
        self._store[key] = _CacheEntry(
            data=data, expires_at=time.time() + max(1, ttl_seconds)
        )
        self._save_disk()

    async def get_or_fetch(
        self,
        key: str,
        ttl_seconds: int,
        factory: Callable[[], Awaitable[Any]],
        *,
        stale_on_error: bool = True,
    ) -> Any:
        """
        Return cached data or run factory once.

        Concurrent callers for the same key share one in-flight Future
        (request deduplication).
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        async with self._lock:
            cached = self.get(key)
            if cached is not None:
                return cached

            existing = self._inflight.get(key)
            if existing is not None:
                waiter = existing
            else:
                loop = asyncio.get_running_loop()
                waiter = loop.create_future()
                self._inflight[key] = waiter
                owner = True
            if existing is not None:
                owner = False

        if not owner:
            return await waiter

        try:
            result = await factory()
            self.set(key, result, ttl_seconds)
            if not waiter.done():
                waiter.set_result(result)
            return result
        except Exception as exc:  # noqa: BLE001
            stale = self.get(key, allow_expired=True) if stale_on_error else None
            if stale is not None:
                if not waiter.done():
                    waiter.set_result(stale)
                return stale
            if not waiter.done():
                waiter.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

    @staticmethod
    def article_key(title: str) -> str:
        """Full article detail cache key."""
        return f"article:{_normalize_title(title)}"

    @staticmethod
    def card_key(title: str) -> str:
        """Compact card cache key (does not block full article fetch)."""
        return f"card:{_normalize_title(title)}"

    @staticmethod
    def topic_key(topic: str, continue_token: Optional[str] = None) -> str:
        token = continue_token or "start"
        return f"topic:{topic.lower()}:{token}"

    @staticmethod
    def search_key(query: str) -> str:
        return f"search:{query.strip().lower()}"

    @staticmethod
    def home_key() -> str:
        return "home:v1"

    @staticmethod
    def category_home_key(topic: str) -> str:
        return f"home_section:{topic.lower()}"


def _normalize_title(title: str) -> str:
    return title.strip().replace(" ", "_").lower()


wiki_cache = WikiCache()
