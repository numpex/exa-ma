"""
Caching layer for software data.

Provides disk-based caching with TTL support to avoid repeated
fetches from Google Sheets or slow data sources.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SoftwareCollection


class CacheEntry:
    """A single cache entry with metadata."""

    def __init__(
        self,
        data: dict,
        created_at: datetime,
        source: str,
        ttl_seconds: int,
    ):
        self.data = data
        self.created_at = created_at
        self.source = source
        self.ttl_seconds = ttl_seconds

    @property
    def expires_at(self) -> datetime:
        """Get expiration timestamp."""
        return self.created_at + timedelta(seconds=self.ttl_seconds)

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return datetime.now() > self.expires_at

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CacheEntry:
        """Deserialize from dictionary."""
        return cls(
            data=d["data"],
            created_at=datetime.fromisoformat(d["created_at"]),
            source=d["source"],
            ttl_seconds=d["ttl_seconds"],
        )


class SoftwareCache:
    """Disk-based cache for software data.

    Caches SoftwareCollection objects as JSON files with TTL support.
    """

    DEFAULT_TTL = 3600  # 1 hour
    CACHE_VERSION = "1"

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        ttl_seconds: int = DEFAULT_TTL,
    ):
        """Initialize cache.

        Args:
            cache_dir: Directory to store cache files.
                       Defaults to ~/.cache/exa-ma/software/
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "exa-ma" / "software"
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, source: str) -> str:
        """Generate a cache key from source identifier."""
        # Use hash to handle long paths/URLs
        hash_input = f"{self.CACHE_VERSION}:{source}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _get_cache_path(self, source: str) -> Path:
        """Get the cache file path for a source."""
        key = self._get_cache_key(source)
        return self.cache_dir / f"{key}.json"

    def get(self, source: str) -> SoftwareCollection | None:
        """Retrieve cached data if available and not expired.

        Args:
            source: The data source identifier (file path or sheet ID)

        Returns:
            SoftwareCollection if cache hit and valid, None otherwise
        """
        cache_path = self._get_cache_path(source)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                entry = CacheEntry.from_dict(json.load(f))

            if entry.is_expired:
                # Remove expired entry
                cache_path.unlink(missing_ok=True)
                return None

            # Reconstruct SoftwareCollection from cached data
            from .models import SoftwareCollection

            return SoftwareCollection.model_validate(entry.data)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Invalid cache entry, remove it
            print(f"Warning: Invalid cache entry, removing: {e}")
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, source: str, collection: SoftwareCollection) -> None:
        """Store data in cache.

        Args:
            source: The data source identifier
            collection: The SoftwareCollection to cache
        """
        cache_path = self._get_cache_path(source)

        entry = CacheEntry(
            data=collection.model_dump(mode="json"),
            created_at=datetime.now(),
            source=source,
            ttl_seconds=self.ttl_seconds,
        )

        with open(cache_path, "w") as f:
            json.dump(entry.to_dict(), f, indent=2, default=str)

    def invalidate(self, source: str) -> bool:
        """Invalidate (remove) a cache entry.

        Args:
            source: The data source identifier

        Returns:
            True if entry was removed, False if not found
        """
        cache_path = self._get_cache_path(source)
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries removed
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        entries = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in entries)

        expired = 0
        valid = 0

        for entry_path in entries:
            try:
                with open(entry_path) as f:
                    entry = CacheEntry.from_dict(json.load(f))
                if entry.is_expired:
                    expired += 1
                else:
                    valid += 1
            except Exception:
                expired += 1

        return {
            "total_entries": len(entries),
            "valid_entries": valid,
            "expired_entries": expired,
            "total_size_bytes": total_size,
            "cache_dir": str(self.cache_dir),
        }


class CachedFetcher:
    """Wrapper that adds caching to any SoftwareDataSource."""

    def __init__(
        self,
        fetcher,  # SoftwareDataSource
        cache: SoftwareCache | None = None,
        cache_key: str | None = None,
    ):
        """Initialize cached fetcher.

        Args:
            fetcher: The underlying data source
            cache: Cache instance (creates default if None)
            cache_key: Override cache key (defaults to source identifier)
        """
        self.fetcher = fetcher
        self.cache = cache or SoftwareCache()
        self._cache_key = cache_key

    @property
    def cache_key(self) -> str:
        """Get the cache key for this fetcher."""
        if self._cache_key:
            return self._cache_key

        # Try to get source from fetcher
        if hasattr(self.fetcher, "file_path"):
            return str(self.fetcher.file_path)
        if hasattr(self.fetcher, "sheet_id"):
            return f"sheets:{self.fetcher.sheet_id}"
        return "unknown"

    def fetch(self, force_refresh: bool = False) -> SoftwareCollection:
        """Fetch data, using cache if available.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            SoftwareCollection
        """
        if not force_refresh:
            cached = self.cache.get(self.cache_key)
            if cached:
                print(f"Using cached data for {self.cache_key}")
                return cached

        # Fetch fresh data
        print(f"Fetching fresh data from {self.cache_key}")
        collection = self.fetcher.fetch()

        # Store in cache
        self.cache.set(self.cache_key, collection)

        return collection

    def invalidate(self) -> bool:
        """Invalidate the cache for this fetcher."""
        return self.cache.invalidate(self.cache_key)
