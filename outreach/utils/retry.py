"""
retry.py – Retry decorator with exponential back-off.

Design rationale
----------------
*  Written as a decorator factory so call-sites are clean:
       @retry(max_attempts=3, backoff_factor=2.0)
       def call_api(): ...

*  We distinguish between "transient" errors (network timeout, 429, 5xx) that
   are worth retrying and "permanent" errors (400, 401, 404) that are not.
   Retrying a 401 is pointless and wastes quota.

*  Jitter (random ± 10 %) is added to the sleep interval so that a batch of
   parallel workers doesn't produce a thundering herd after a 429.

*  The decorator preserves the wrapped function's __name__ and __doc__ via
   functools.wraps — essential for introspection and debugging.
"""

import random
import time
import functools
import logging
from typing import Callable, Tuple, Type

from outreach.utils.logger import get_logger

logger = get_logger(__name__)

# HTTP status codes that are worth retrying
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Exceptions that are always retried regardless of status code
_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
)


class APIError(Exception):
    """
    Raised by our API clients when the HTTP layer succeeds but the response
    indicates an error.  Carries the status_code so the retry decorator can
    decide whether to retry.
    """

    def __init__(self, message: str, status_code: int = 0, response_body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def is_retryable(self) -> bool:
        return self.status_code in _RETRYABLE_STATUS_CODES


class RateLimitError(APIError):
    """Specific subclass for 429s — lets callers catch it separately."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = _RETRYABLE_EXCEPTIONS,
) -> Callable:
    """
    Decorator factory.  Wraps a function with retry + exponential back-off.

    Args:
        max_attempts:          Total attempts (1 = no retries).
        backoff_factor:        Multiplier for sleep time between attempts.
                               Sleep = backoff_factor ** (attempt - 1) seconds.
        retryable_exceptions:  Tuple of exception types that trigger a retry.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception = RuntimeError("retry() called with max_attempts < 1")

            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)

                except RateLimitError as exc:
                    # Respect the Retry-After header if the API provides it
                    sleep_time = exc.retry_after
                    logger.warning(
                        "Rate limit hit in %s (attempt %d/%d). "
                        "Sleeping %ds (Retry-After).",
                        fn.__name__, attempt, max_attempts, sleep_time,
                    )
                    last_exc = exc

                except APIError as exc:
                    if not exc.is_retryable():
                        # 400, 401, 403, 404 — no point retrying
                        logger.error(
                            "Non-retryable API error in %s: %s (status=%d)",
                            fn.__name__, exc, exc.status_code,
                        )
                        raise
                    sleep_time = _jittered_sleep(backoff_factor, attempt)
                    logger.warning(
                        "Retryable API error in %s (attempt %d/%d, status=%d). "
                        "Sleeping %.1fs.",
                        fn.__name__, attempt, max_attempts, exc.status_code, sleep_time,
                    )
                    last_exc = exc

                except retryable_exceptions as exc:
                    sleep_time = _jittered_sleep(backoff_factor, attempt)
                    logger.warning(
                        "Network error in %s (attempt %d/%d): %s. Sleeping %.1fs.",
                        fn.__name__, attempt, max_attempts, exc, sleep_time,
                    )
                    last_exc = exc

                if attempt < max_attempts:
                    time.sleep(sleep_time)

            logger.error(
                "%s failed after %d attempts. Last error: %s",
                fn.__name__, max_attempts, last_exc,
            )
            raise last_exc

        return wrapper
    return decorator


def _jittered_sleep(backoff_factor: float, attempt: int) -> float:
    """Exponential back-off with ±10 % jitter."""
    base = backoff_factor ** (attempt - 1)
    jitter = base * random.uniform(-0.1, 0.1)
    return max(0.1, base + jitter)
