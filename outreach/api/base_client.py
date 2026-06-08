"""
base_client.py – Thin wrapper around requests.Session.

Design rationale
----------------
*  Every API client inherits from BaseAPIClient rather than calling requests
   directly.  This gives us:
     - A single place to set headers (auth, content-type, user-agent)
     - Automatic JSON decoding
     - Consistent error translation into our APIError / RateLimitError types
     - Rate-limit delay between calls (configurable via settings)

*  We pass settings in via the constructor (dependency injection) so tests
   can supply a fake Settings object without monkeypatching globals.

*  The _request() method is intentionally simple — no async, no connection
   pooling tuning.  For a CLI tool that processes O(10–100) companies this
   is fast enough; over-engineering here would hurt readability.
"""

import time
from typing import Any, Dict, Optional

import requests

from outreach.config import Settings
from outreach.utils.logger import get_logger
from outreach.utils.retry import APIError, RateLimitError


class BaseAPIClient:
    """
    Shared HTTP machinery for all service clients.

    Subclasses set:
        base_url  – e.g. "https://api.ocean.io/v1"
        _auth_header() – returns {"Authorization": "Bearer <key>"} or similar
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = get_logger(self.__class__.__name__)
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "outreach-cli/1.0",
            }
        )
        self._session.headers.update(self._auth_header())

    # ── Subclass interface ────────────────────────────────────────────────────

    @property
    def base_url(self) -> str:  # pragma: no cover
        raise NotImplementedError

    def _auth_header(self) -> Dict[str, str]:  # pragma: no cover
        raise NotImplementedError

    # ── Internal HTTP ─────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        timeout: int = 30,
    ) -> Any:
        """
        Make one HTTP request and return the parsed JSON body.

        Raises:
            RateLimitError  on 429
            APIError        on all other 4xx / 5xx
        """
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        self._logger.debug("%s %s params=%s", method.upper(), url, params)

        # Polite rate-limit delay between calls to the same service
        time.sleep(self._settings.rate_limit_delay)

        try:
            response = self._session.request(
                method,
                url,
                params=params,
                json=json,
                timeout=timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise TimeoutError(f"Request to {url} timed out") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(f"Could not connect to {url}: {exc}") from exc

        self._logger.debug("Response %d from %s", response.status_code, url)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise RateLimitError(retry_after=retry_after)

        if response.status_code >= 400:
            raise APIError(
                message=f"HTTP {response.status_code} from {url}: {response.text[:200]}",
                status_code=response.status_code,
                response_body=response.text,
            )

        if not response.content:
            return {}

        return response.json()

    def get(self, path: str, **kwargs) -> Any:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> Any:
        return self._request("POST", path, **kwargs)
