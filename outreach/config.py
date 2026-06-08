"""
config.py – Central configuration via environment variables.

Design rationale
----------------
*  We use a single Settings dataclass (not a dict, not module-level globals)
   so that the full config is inspectable, type-annotated, and easy to pass
   around or mock in tests.
*  Every value has a default of None; the validate() method enforces required
   keys at startup so the process fails loudly before making any API calls.
*  We read from the environment (and optionally a .env file via python-dotenv)
   rather than hard-coding anything — a basic 12-factor app principle.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# python-dotenv is optional: if it's installed we auto-load a .env file.
try:
    from dotenv import load_dotenv

    _DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(_DOTENV_PATH)
except ImportError:
    pass  # dotenv not installed; rely on shell environment


@dataclass
class Settings:
    # ── Ocean.io ──────────────────────────────────────────────────────────────
    ocean_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OCEAN_API_KEY",  "api_STvRIE_CKgtYqxlIT8nxi0dxmIALiXnyG8pszRB")
    )
    ocean_base_url: str = field(
        default_factory=lambda: os.getenv(
            "OCEAN_BASE_URL", "https://api.ocean.io/v3"
        )
    )
    ocean_lookalike_limit: int = field(
        default_factory=lambda: int(os.getenv("OCEAN_LOOKALIKE_LIMIT", "10"))
    )

    # ── Prospeo ───────────────────────────────────────────────────────────────
    prospeo_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("PROSPEO_API_KEY", "pk_03d0c2e866a6206a6c253758160e0d4048dd2d99488042a86a246db11e07944f")
    )
    prospeo_base_url: str = field(
        default_factory=lambda: os.getenv(
            "PROSPEO_BASE_URL", "https://api.prospeo.io"
        )
    )

    # ── Eazyreach ─────────────────────────────────────────────────────────────

    # ── Brevo (SendinBlue) ────────────────────────────────────────────────────
    brevo_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("BREVO_API_KEY")
    )
    brevo_base_url: str = field(
        default_factory=lambda: os.getenv(
            "BREVO_BASE_URL", "https://api.brevo.com/v3"
        )
    )
    sender_email: Optional[str] = field(
        default_factory=lambda: os.getenv("SENDER_EMAIL")
    )
    sender_name: str = field(
        default_factory=lambda: os.getenv("SENDER_NAME", "Outreach Bot")
    )

    # ── Retry / rate-limit behaviour ──────────────────────────────────────────
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES", "3"))
    )
    retry_backoff_factor: float = field(
        default_factory=lambda: float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))
    )
    # Seconds to sleep between requests to the same service
    rate_limit_delay: float = field(
        default_factory=lambda: float(os.getenv("RATE_LIMIT_DELAY", "1.0"))
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )
    log_file: Optional[str] = field(
        default_factory=lambda: os.getenv("LOG_FILE")  # None → stdout only
    )

    def validate(self) -> None:
        required = {
            "OCEAN_API_KEY": self.ocean_api_key,
            "PROSPEO_API_KEY": self.prospeo_api_key,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Copy .env.example to .env and fill in the values."
            )

    def redacted_repr(self) -> str:
        """Safe string for logging — never prints actual keys."""
        def mask(val: Optional[str]) -> str:
            if not val:
                return "<not set>"
            return val[:4] + "****"

        return (
            f"Settings("
            f"ocean_api_key={mask(self.ocean_api_key)}, "
            f"prospeo_api_key={mask(self.prospeo_api_key)}, "
            f"sender_email={self.sender_email}, "
            f"max_retries={self.max_retries}, "
            f"rate_limit_delay={self.rate_limit_delay}s"
            f")"
        )


# Module-level singleton — import this everywhere rather than constructing
# Settings() multiple times.
settings = Settings()
