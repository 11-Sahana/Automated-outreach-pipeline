from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Company:
    """
    Represents a company returned by the Ocean.io lookalike API.

    Design note: We use a dataclass here (not Pydantic) to keep the dependency
    footprint small for a CLI tool. If this grew into a web service, swapping
    to Pydantic for automatic validation would be the right move.
    """

    domain: str
    name: str
    industry: Optional[str] = None
    country: Optional[str] = None
    employee_count: Optional[int] = None
    description: Optional[str] = None
    similarity_score: Optional[float] = None  # 0.0–1.0, provided by Ocean.io
    raw: dict = field(default_factory=dict, repr=False)  # preserve original payload

    def __post_init__(self) -> None:
        # Normalise domain: strip scheme and trailing slashes so downstream
        # calls always receive a clean value like "stripe.com".
        self.domain = (
            self.domain.replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
            .lower()
        )

    def __str__(self) -> str:
        return f"{self.name} ({self.domain})"
