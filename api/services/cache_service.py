"""
FAB Order Cache Service

Provides in-memory caching for /orders/fabs responses with:
- Configurable TTL (default 30 minutes)
- LRU eviction (max 7 dates)
- Request coalescing to prevent thundering herd
- Thread-safe operations

The cache stores full FAB order responses by date, benefiting all clients
that query the same date within the TTL window.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any


@dataclass
class CacheEntry:
    """A cached FAB order response"""

    data: list[dict[str, Any]]
    created_at: datetime
    hits: int = 0


@dataclass
class CacheStats:
    """Cache statistics"""

    enabled: bool
    entries: int
    total_hits: int
    total_misses: int
    oldest_entry: str | None
    newest_entry: str | None
    cached_dates: list[str]


@dataclass
class FabOrderCache:
    """
    In-memory cache for FAB order queries with request coalescing.

    Thread-safe LRU cache that prevents thundering herd on cache miss
    by coalescing concurrent requests for the same date.
    """

    ttl_minutes: int = 30
    max_entries: int = 7

    # Internal state
    _cache: dict[str, CacheEntry] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)
    _pending: dict[str, asyncio.Future] = field(default_factory=dict)
    _pending_lock: Lock = field(default_factory=Lock)
    _total_hits: int = 0
    _total_misses: int = 0

    def get(self, date: str) -> list[dict[str, Any]] | None:
        """
        Get cached data for a date.

        Returns None if not cached or expired.
        """
        with self._lock:
            entry = self._cache.get(date)
            if entry is None:
                return None

            # Check if expired
            age_seconds = (datetime.now(UTC) - entry.created_at).total_seconds()
            if age_seconds > self.ttl_minutes * 60:
                # Expired - remove and return None
                del self._cache[date]
                return None

            # Cache hit
            entry.hits += 1
            self._total_hits += 1
            return entry.data

    def set(self, date: str, data: list[dict[str, Any]]) -> None:
        """
        Cache data for a date.

        Evicts oldest entry if at capacity.
        """
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self.max_entries and date not in self._cache:
                self._evict_oldest()

            self._cache[date] = CacheEntry(
                data=data,
                created_at=datetime.now(UTC),
                hits=0,
            )

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry (LRU)"""
        if not self._cache:
            return

        oldest_date = min(
            self._cache.keys(),
            key=lambda d: self._cache[d].created_at,
        )
        del self._cache[oldest_date]

    def invalidate(self, date: str) -> bool:
        """
        Invalidate cache for a specific date.

        Returns True if entry was removed, False if not found.
        """
        with self._lock:
            if date in self._cache:
                del self._cache[date]
                return True
            return False

    def clear_all(self) -> int:
        """
        Clear all cached entries.

        Returns number of entries cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        with self._lock:
            cached_dates = list(self._cache.keys())
            oldest = None
            newest = None

            if self._cache:
                oldest = min(cached_dates, key=lambda d: self._cache[d].created_at)
                newest = max(cached_dates, key=lambda d: self._cache[d].created_at)

            return CacheStats(
                enabled=True,
                entries=len(self._cache),
                total_hits=self._total_hits,
                total_misses=self._total_misses,
                oldest_entry=oldest,
                newest_entry=newest,
                cached_dates=cached_dates,
            )

    async def get_or_fetch(
        self,
        date: str,
        fetch_fn: Callable[[], Any],
    ) -> list[dict[str, Any]]:
        """
        Get from cache or fetch with request coalescing.

        If multiple requests arrive for the same uncached date simultaneously,
        only ONE will query the database while others wait for its result.

        Args:
            date: The date key to fetch
            fetch_fn: Async function to call on cache miss

        Returns:
            Cached or freshly fetched data
        """
        # Fast path: check cache first
        cached = self.get(date)
        if cached is not None:
            return cached

        # Track miss
        with self._lock:
            self._total_misses += 1

        # Slow path: need to fetch
        # Check if another request is already fetching this date
        with self._pending_lock:
            if date in self._pending:
                # Another request is fetching - wait for its result
                future = self._pending[date]
            else:
                # We're the first - create a future and start fetching
                loop = asyncio.get_event_loop()
                future = loop.create_future()
                self._pending[date] = future

                # Start the fetch in a task (store reference to prevent GC)
                task = asyncio.create_task(self._do_fetch(date, fetch_fn, future))
                # Suppress "task was never awaited" warning - we await the future instead
                task.add_done_callback(lambda _: None)

        # Wait for result (either ours or another request's)
        result = await future
        return result

    async def _do_fetch(
        self,
        date: str,
        fetch_fn: Callable[[], Any],
        future: asyncio.Future,
    ) -> None:
        """Execute the actual fetch and resolve the future"""
        try:
            # Call the fetch function
            result = await fetch_fn()

            # Cache the result
            self.set(date, result)

            # Resolve the future
            future.set_result(result)
        except Exception as e:
            # Propagate error to all waiters
            future.set_exception(e)
        finally:
            # Clean up pending
            with self._pending_lock:
                self._pending.pop(date, None)


# Global cache instance
_fab_cache: FabOrderCache | None = None


def get_fab_cache() -> FabOrderCache:
    """Get or create the global FAB order cache"""
    global _fab_cache
    if _fab_cache is None:
        _fab_cache = FabOrderCache()
    return _fab_cache


def configure_fab_cache(ttl_minutes: int = 30, max_entries: int = 7) -> FabOrderCache:
    """Configure and return the global FAB order cache"""
    global _fab_cache
    _fab_cache = FabOrderCache(ttl_minutes=ttl_minutes, max_entries=max_entries)
    return _fab_cache
