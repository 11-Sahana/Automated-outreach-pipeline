from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class OutreachCampaign:
    """
    Everything needed to send one email to one contact.
    Keeping the campaign as a first-class object makes it trivial to audit,
    replay, or hand off to a different sender in the future.
    """

    to_email: str
    to_name: str
    company_name: str
    company_domain: str
    subject: str
    html_body: str
    text_body: str
    sender_email: str
    sender_name: str


@dataclass
class CampaignResult:
    """
    Outcome of a single send attempt.
    """

    campaign: OutreachCampaign
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"{status} {self.campaign.to_email} – {self.campaign.company_domain}"
