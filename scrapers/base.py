"""Base scraper class with common functionality."""

import time
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests

from models.opportunity import YieldOpportunity
from utils.vpn import get_vpn_manager
from config import CACHE_DURATION, REQUEST_TIMEOUT, RATE_LIMIT_DELAY


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    requires_vpn: bool = False
    category: str = ""
    cache_file: str = ""

    def __init__(self):
        """Initialize the scraper."""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self._last_request_time: float = 0
        self._cache_dir = Path(".cache")
        self._cache_dir.mkdir(exist_ok=True)

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _ensure_vpn(self) -> bool:
        """Ensure VPN is connected if required.

        Returns:
            True if VPN is ready (or not required), False if VPN failed.
        """
        if not self.requires_vpn:
            return True

        vpn = get_vpn_manager()
        return vpn.ensure_vpn()

    def _get_cached_data(self, stale_ok: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Get cached data if available.

        Args:
            stale_ok: If True, return cached data even if expired.

        Returns:
            Cached data or None if cache is invalid/missing.
        """
        if not self.cache_file:
            return None

        cache_path = self._cache_dir / f"{self.cache_file}.json"
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)

            cached_time = datetime.fromisoformat(cache["timestamp"])
            age_seconds = (datetime.now() - cached_time).total_seconds()

            # Return if cache is fresh OR if stale data is acceptable
            if age_seconds < CACHE_DURATION or stale_ok:
                return cache["data"]
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

        return None

    def _save_to_cache(self, data: List[Dict[str, Any]]) -> None:
        """Save data to cache.

        Args:
            data: Data to cache.
        """
        if not self.cache_file:
            return

        cache_path = self._cache_dir / f"{self.cache_file}.json"
        cache = {
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        with open(cache_path, "w") as f:
            json.dump(cache, f)

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = REQUEST_TIMEOUT,
    ) -> requests.Response:
        """Make an HTTP request with rate limiting and error handling.

        Args:
            url: URL to request.
            method: HTTP method.
            params: Query parameters.
            json_data: JSON body data.
            headers: Additional headers.
            timeout: Request timeout.

        Returns:
            Response object.

        Raises:
            requests.RequestException: If request fails.
        """
        self._rate_limit()

        request_headers = dict(self.session.headers)
        if headers:
            request_headers.update(headers)

        response = self.session.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=request_headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response

    def fetch(self, use_cache: bool = True, stale_ok: bool = False) -> List[YieldOpportunity]:
        """Fetch yield opportunities.

        Args:
            use_cache: Whether to use cached data if available.
            stale_ok: If True, return stale cached data immediately without refreshing.

        Returns:
            List of yield opportunities.
        """
        # Check cache first
        if use_cache or stale_ok:
            cached = self._get_cached_data(stale_ok=stale_ok)
            if cached:
                return [YieldOpportunity.from_dict(d) for d in cached]

        # If stale_ok was requested but no cache exists, we need to fetch
        # Ensure VPN if required
        if not self._ensure_vpn():
            raise RuntimeError(f"VPN required but could not connect for {self.category}")

        # Fetch and parse data
        try:
            opportunities = self._fetch_data()

            # Cache the results
            self._save_to_cache([o.to_dict() for o in opportunities])

            return opportunities

        except Exception as e:
            # Try to return cached data on error (stale is ok here)
            cached = self._get_cached_data(stale_ok=True)
            if cached:
                return [YieldOpportunity.from_dict(d) for d in cached]
            raise

    @abstractmethod
    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch data from the source. Must be implemented by subclasses.

        Returns:
            List of yield opportunities.
        """
        pass
