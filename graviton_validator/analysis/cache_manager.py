"""
Cache Manager for Runtime Analyzers

Provides persistent caching, batch processing, and rate limiting for API calls.
"""

import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: str
    version: str = "1.0"
    source: str = "api"
    
    def is_expired(self, max_age_days: int = 30) -> bool:
        """Check if cache entry is expired."""
        try:
            entry_time = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            now = datetime.now().replace(tzinfo=entry_time.tzinfo)
            
            # Check if this is a TTL-based entry (future timestamp means TTL expiry)
            if entry_time > now:
                return False  # Not expired yet
            
            # Regular age-based expiry
            return now - entry_time > timedelta(days=max_age_days)
        except:
            return True


@dataclass
class RateLimitState:
    """Rate limiting state."""
    requests_made: int = 0
    window_start: float = 0
    backoff_until: float = 0
    consecutive_failures: int = 0


class CacheManager:
    """Manages persistent caching and API rate limiting."""
    
    def __init__(self, cache_dir: str = ".cache", max_age_days: int = 30):
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files
            max_age_days: Maximum age for cache entries in days
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_age_days = max_age_days
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.rate_limits: Dict[str, RateLimitState] = {}
        self.lock = threading.Lock()
        
        # Rate limiting configuration
        self.rate_config = {
            'nuget': {'requests_per_minute': 60, 'burst_limit': 10},
            'pypi': {'requests_per_minute': 60, 'burst_limit': 10},
            'npm': {'requests_per_minute': 60, 'burst_limit': 10},
            'maven': {'requests_per_minute': 60, 'burst_limit': 10}
        }
    
    def _get_cache_key(self, runtime: str, package: str, version: Optional[str] = None) -> str:
        """Generate cache key for package using SHA256."""
        key_data = f"{runtime}:{package}:{version or 'latest'}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _get_cache_file(self, runtime: str) -> Path:
        """Get cache file path for runtime."""
        return self.cache_dir / f"{runtime}_cache.json"
    
    def _load_cache(self, runtime: str) -> Dict[str, CacheEntry]:
        """Load cache from disk."""
        cache_file = self._get_cache_file(runtime)
        if not cache_file.exists():
            return {}
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            cache = {}
            for key, entry_data in data.items():
                try:
                    cache[key] = CacheEntry(**entry_data)
                except Exception as e:
                    logger.debug(f"Skipping invalid cache entry {key}: {e}")
            
            return cache
        except Exception as e:
            logger.warning(f"Failed to load cache for {runtime}: {e}")
            return {}
    
    def _save_cache(self, runtime: str, cache: Dict[str, CacheEntry]):
        """Save cache to disk."""
        cache_file = self._get_cache_file(runtime)
        try:
            data = {key: asdict(entry) for key, entry in cache.items()}
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache for {runtime}: {e}")
    
    def get_cached(self, runtime: str, package: str, version: Optional[str] = None) -> Optional[Any]:
        """Get cached data for package."""
        cache_key = self._get_cache_key(runtime, package, version)
        
        with self.lock:
            # Check memory cache first
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                if not entry.is_expired(self.max_age_days):
                    logger.debug(f"Cache hit (memory) for {runtime} package {package}")
                    return entry.data
                else:
                    del self.memory_cache[cache_key]
            
            # Load from disk cache
            disk_cache = self._load_cache(runtime)
            if cache_key in disk_cache:
                entry = disk_cache[cache_key]
                if not entry.is_expired(self.max_age_days):
                    logger.debug(f"Cache hit (disk) for {runtime} package {package}")
                    self.memory_cache[cache_key] = entry
                    return entry.data
        
        logger.debug(f"Cache miss for {package}")
        return None
    
    def set_cached(self, runtime: str, package: str, data: Any, version: Optional[str] = None, source: str = "api", ttl_hours: Optional[int] = None):
        """Cache data for package with optional TTL."""
        cache_key = self._get_cache_key(runtime, package, version)
        
        # Set custom expiration if TTL specified
        if ttl_hours:
            expiry_time = datetime.now() + timedelta(hours=ttl_hours)
            timestamp = expiry_time.isoformat() + 'Z'
        else:
            timestamp = datetime.now().isoformat() + 'Z'
        
        entry = CacheEntry(
            data=data,
            timestamp=timestamp,
            source=source
        )
        
        with self.lock:
            self.memory_cache[cache_key] = entry
            
            # Update disk cache
            disk_cache = self._load_cache(runtime)
            disk_cache[cache_key] = entry
            self._save_cache(runtime, disk_cache)
        
        logger.debug(f"Cached data for {package}" + (f" (TTL: {ttl_hours}h)" if ttl_hours else ""))
    
    def can_make_request(self, runtime: str) -> bool:
        """Check if we can make an API request without hitting rate limits."""
        if runtime not in self.rate_config:
            return True
        
        with self.lock:
            if runtime not in self.rate_limits:
                self.rate_limits[runtime] = RateLimitState()
            
            state = self.rate_limits[runtime]
            now = time.time()
            
            # Check if we're in backoff period
            if now < state.backoff_until:
                return False
            
            # Reset window if needed
            if now - state.window_start >= 60:  # 1 minute window
                state.requests_made = 0
                state.window_start = now
            
            config = self.rate_config[runtime]
            return state.requests_made < config['requests_per_minute']
    
    def record_request(self, runtime: str, success: bool = True):
        """Record an API request."""
        if runtime not in self.rate_config:
            return
        
        with self.lock:
            if runtime not in self.rate_limits:
                self.rate_limits[runtime] = RateLimitState()
            
            state = self.rate_limits[runtime]
            state.requests_made += 1
            
            if success:
                state.consecutive_failures = 0
            else:
                state.consecutive_failures += 1
                # Exponential backoff: 100ms * 2^failures, max 30 seconds
                backoff_seconds = min(30.0, 0.1 * (2 ** state.consecutive_failures))
                state.backoff_until = time.time() + backoff_seconds
                logger.warning(f"API failure for {runtime}, backing off for {backoff_seconds:.1f}s")
    
    def wait_for_rate_limit(self, runtime: str) -> float:
        """Wait for rate limit to allow request. Returns wait time."""
        total_wait = 0
        
        with self.lock:
            if runtime not in self.rate_limits:
                self.rate_limits[runtime] = RateLimitState()
            
            state = self.rate_limits[runtime]
            now = time.time()
            
            # Wait for backoff period if active
            if now < state.backoff_until:
                backoff_wait = state.backoff_until - now
                logger.info(f"Waiting {backoff_wait:.1f}s for {runtime} exponential backoff")
                time.sleep(backoff_wait)
                total_wait += backoff_wait
                now = time.time()
            
            # Check if we need to wait for rate limit window
            if runtime in self.rate_config:
                config = self.rate_config[runtime]
                
                # Reset window if needed
                if now - state.window_start >= 60:  # 1 minute window
                    state.requests_made = 0
                    state.window_start = now
                
                # If we've hit the rate limit, wait for window reset
                if state.requests_made >= config['requests_per_minute']:
                    window_wait = 60 - (now - state.window_start)
                    if window_wait > 0:
                        logger.info(f"Waiting {window_wait:.1f}s for {runtime} rate limit window reset")
                        time.sleep(window_wait)
                        total_wait += window_wait
                        # Reset the window after waiting
                        state.requests_made = 0
                        state.window_start = time.time()
        
        return total_wait
    
    def get_batch_candidates(self, runtime: str, packages: List[str]) -> List[str]:
        """Get packages that need API lookup (not in cache)."""
        candidates = []
        for package in packages:
            if self.get_cached(runtime, package) is None:
                candidates.append(package)
        return candidates
    
    def clear_cache(self, runtime: Optional[str] = None):
        """Clear cache for runtime or all runtimes."""
        with self.lock:
            if runtime:
                # Clear specific runtime
                self.memory_cache = {k: v for k, v in self.memory_cache.items() 
                                   if not k.startswith(f"{runtime}:")}
                cache_file = self._get_cache_file(runtime)
                if cache_file.exists():
                    cache_file.unlink()
            else:
                # Clear all caches
                self.memory_cache.clear()
                for cache_file in self.cache_dir.glob("*_cache.json"):
                    cache_file.unlink()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'memory_entries': len(self.memory_cache),
            'disk_files': len(list(self.cache_dir.glob("*_cache.json"))),
            'rate_limits': {}
        }
        
        for runtime, state in self.rate_limits.items():
            stats['rate_limits'][runtime] = {
                'requests_made': state.requests_made,
                'consecutive_failures': state.consecutive_failures,
                'backoff_active': time.time() < state.backoff_until
            }
        
        return stats


# Global cache manager instance
_cache_manager = None

def get_cache_manager(config=None) -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        if config and hasattr(config, 'cache'):
            cache_config = config.cache
            _cache_manager = CacheManager(
                cache_dir=cache_config.cache_dir,
                max_age_days=cache_config.max_age_days
            )
            # Update rate limits from config
            if cache_config.rate_limiting:
                _cache_manager.rate_config.update(cache_config.rate_limits)
        else:
            _cache_manager = CacheManager()
    return _cache_manager