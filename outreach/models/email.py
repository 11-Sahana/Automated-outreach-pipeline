from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EmailStatus(str, Enum):
    """
    Eazyreach verification result.
    Only VALID emails should be used in campaigns — sending to RISKY or INVALID
    addresses damages sender reputation and can get your domain blacklisted.
    """

    VALID = "valid"
    RISKY = "risky"        # Deliverable but may bounce (catch-all, disposable)
    INVALID = "invalid"    # Definitively bad address
    UNKNOWN = "unknown"    # API could not determine status


@dataclass
class VerifiedEmail:
    email: str
    status: EmailStatus
    contact_first_name: str
    contact_last_name: str
    company_domain: str
    mx_found: bool = False
    smtp_valid: Optional[bool] = None
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def is_sendable(self) -> bool:
        """Conservative default: only send to definitively valid addresses."""
        return self.status == EmailStatus.VALID

    def __str__(self) -> str:
        return f"{self.email} [{self.status.value}]"
