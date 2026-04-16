"""
Simple thread-safe in-memory cache with TTL and in-flight request dedup.

Goals:
- Stop the Azure/M365 API call storm caused by the frontend double-firing,
  multiple pages querying the same endpoints, and StrictMode.
- Dedup in-flight requests: if two callers ask for the same key at the same
  time, only one real fetch happens; the second waits for the first.

This is intentionally minimal - no external deps, no distributed cache, no
persistence. Restarting the server clears the cache.
"""

import logging
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """Thread-safe cache where each entry has its own TTL."""

    def __init__(self, default_ttl: float = 60.0) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, tuple[float, Any]] = {}
        # Per-key locks for in-flight dedup
        self._locks: dict[str, threading.Lock] = {}
        # Global lock for _locks / _store bookkeeping
        self._meta_lock = threading.Lock()

    def _get_lock(self, key: str) -> threading.Lock:
        with self._meta_lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    def get(self, key: str) -> Optional[Any]:
        """Returns cached value if present and fresh, else None."""
        with self._meta_lock:
            entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            with self._meta_lock:
                # Double-check under lock
                cur = self._store.get(key)
                if cur is not None and cur[0] <= time.monotonic():
                    self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        ttl_val = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + ttl_val
        with self._meta_lock:
            self._store[key] = (expires_at, value)

    def invalidate(self, key: str) -> None:
        with self._meta_lock:
            self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._meta_lock:
            to_remove = [k for k in self._store if k.startswith(prefix)]
            for k in to_remove:
                self._store.pop(k, None)

    def get_or_compute(
        self,
        key: str,
        compute: Callable[[], Any],
        ttl: Optional[float] = None,
    ) -> Any:
        """
        Returns cached value if fresh. Otherwise runs `compute()` while holding
        a per-key lock so concurrent callers for the same key wait on one
        execution instead of all racing to Azure.
        """
        cached = self.get(key)
        if cached is not None:
            logger.debug("Cache HIT: %s", key)
            return cached

        lock = self._get_lock(key)
        with lock:
            # Re-check under lock - another caller may have populated it
            cached = self.get(key)
            if cached is not None:
                logger.debug("Cache HIT (after wait): %s", key)
                return cached

            logger.info("Cache MISS: %s - fetching", key)
            value = compute()
            # Only cache successful / non-error values by default - let callers
            # decide. Here we always cache because errors are wrapped into the
            # data_status fields and we don't want to hammer Azure on failure.
            self.set(key, value, ttl=ttl)
            return value


# Module-level singleton
_cache = TTLCache()


def get_cache() -> TTLCache:
    return _cache