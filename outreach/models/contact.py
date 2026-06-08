from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ContactTitle(str, Enum):
    """
    Seniority tiers we target.

    Using an Enum (not raw strings) means typos are caught at import time,
    not at 2 AM when a batch run silently skips everyone.
    """

    CEO = "CEO"
    CTO = "CTO"
    CFO = "CFO"
    COO = "COO"
    CMO = "CMO"
    VP_ENGINEERING = "VP Engineering"
    VP_SALES = "VP Sales"
    VP_MARKETING = "VP Marketing"
    VP_PRODUCT = "VP Product"
    VP_OPERATIONS = "VP Operations"

    @classmethod
    def c_suite(cls) -> list["ContactTitle"]:
        return [cls.CEO, cls.CTO, cls.CFO, cls.COO, cls.CMO]

    @classmethod
    def vp_level(cls) -> list["ContactTitle"]:
        return [
            cls.VP_ENGINEERING,
            cls.VP_SALES,
            cls.VP_MARKETING,
            cls.VP_PRODUCT,
            cls.VP_OPERATIONS,
        ]

    @classmethod
    def all_targets(cls) -> list["ContactTitle"]:
        return cls.c_suite() + cls.vp_level()


@dataclass
class Contact:
    """
    A person discovered via Prospeo for a given company domain.
    """

    first_name: str
    last_name: str
    title: str                     # Raw string from API; may not match enum exactly
    company_domain: str
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[str] = None    # Populated later by Eazyreach
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def has_verified_email(self) -> bool:
        return bool(self.email)

    def __str__(self) -> str:
        return f"{self.full_name} – {self.title} @ {self.company_domain}"
