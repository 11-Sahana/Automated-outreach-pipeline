"""
tests/unit/test_retry.py

We test the retry decorator in isolation — no network calls, no env vars.
These tests document the expected behaviour for readers as much as they
verify correctness.
"""

import time
import pytest
from unittest.mock import MagicMock, patch, call

from outreach.utils.retry import retry, APIError, RateLimitError


class TestRetryDecorator:
    """retry() decorator behaviour."""

    def test_success_on_first_attempt(self):
        """Happy path: function succeeds immediately, no retries needed."""
        mock_fn = MagicMock(return_value="ok")

        @retry(max_attempts=3, backoff_factor=0)
        def call_api():
            return mock_fn()

        result = call_api()

        assert result == "ok"
        mock_fn.assert_called_once()

    def test_retries_on_retryable_api_error(self):
        """A 503 should be retried up to max_attempts times."""
        mock_fn = MagicMock(
            side_effect=[
                APIError("Service unavailable", status_code=503),
                APIError("Service unavailable", status_code=503),
                "recovered",
            ]
        )

        @retry(max_attempts=3, backoff_factor=0)
        def call_api():
            return mock_fn()

        with patch("time.sleep"):
            result = call_api()

        assert result == "recovered"
        assert mock_fn.call_count == 3

    def test_does_not_retry_non_retryable_error(self):
        """A 401 Unauthorized should raise immediately, no retries."""
        mock_fn = MagicMock(
            side_effect=APIError("Unauthorized", status_code=401)
        )

        @retry(max_attempts=3, backoff_factor=0)
        def call_api():
            return mock_fn()

        with pytest.raises(APIError) as exc_info:
            call_api()

        assert exc_info.value.status_code == 401
        mock_fn.assert_called_once()  # no retries

    def test_raises_after_max_attempts_exhausted(self):
        """If every attempt fails, the last exception should propagate."""
        mock_fn = MagicMock(
            side_effect=APIError("Server error", status_code=500)
        )

        @retry(max_attempts=3, backoff_factor=0)
        def call_api():
            return mock_fn()

        with patch("time.sleep"):
            with pytest.raises(APIError):
                call_api()

        assert mock_fn.call_count == 3

    def test_rate_limit_error_uses_retry_after(self):
        """RateLimitError should sleep for the Retry-After value."""
        mock_fn = MagicMock(
            side_effect=[
                RateLimitError(retry_after=42),
                "ok",
            ]
        )

        @retry(max_attempts=3, backoff_factor=0)
        def call_api():
            return mock_fn()

        with patch("time.sleep") as mock_sleep:
            result = call_api()

        assert result == "ok"
        mock_sleep.assert_called_with(42)

    def test_preserves_function_name(self):
        """functools.wraps should preserve the wrapped function's metadata."""

        @retry(max_attempts=1)
        def my_special_function():
            pass

        assert my_special_function.__name__ == "my_special_function"

    def test_retries_on_connection_error(self):
        """Network-level errors (ConnectionError) are always retried."""
        mock_fn = MagicMock(
            side_effect=[ConnectionError("Connection refused"), "ok"]
        )

        @retry(max_attempts=2, backoff_factor=0)
        def call_api():
            return mock_fn()

        with patch("time.sleep"):
            result = call_api()

        assert result == "ok"
        assert mock_fn.call_count == 2


class TestAPIError:
    def test_retryable_status_codes(self):
        for code in [429, 500, 502, 503, 504]:
            assert APIError("", status_code=code).is_retryable()

    def test_non_retryable_status_codes(self):
        for code in [400, 401, 403, 404, 422]:
            assert not APIError("", status_code=code).is_retryable()
