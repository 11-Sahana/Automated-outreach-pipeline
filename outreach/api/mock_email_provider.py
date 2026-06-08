import re
from typing import Optional

from outreach.api.email_provider import EmailProvider
from outreach.models import Contact, VerifiedEmail, EmailStatus
from outreach.utils.logger import get_logger

logger = get_logger(__name__)


class MockEmailProvider(EmailProvider):

    _PATTERNS = [
        "{first}.{last}@{domain}",
        "{first}@{domain}",
        "{f}{last}@{domain}",
    ]

    @staticmethod
    def _sanitise(name: str) -> str:
        name = name.lower().strip()
        name = re.sub(r"[^a-z0-9]", "-", name)
        name = re.sub(r"-+", "-", name).strip("-")
        return name

    def find_email(self, contact: Contact) -> Optional[VerifiedEmail]:
        first = self._sanitise(contact.first_name)
        last = self._sanitise(contact.last_name)
        domain = contact.company_domain.lower().strip()

        if not first or not last or not domain:
            logger.debug("Skipping %s — missing name or domain", contact)
            return None

        email = self._PATTERNS[0].format(
            first=first,
            last=last,
            f=first[0],
            domain=domain,
        )

        return VerifiedEmail(
            email=email,
            status=EmailStatus.VALID,
            contact_first_name=contact.first_name,
            contact_last_name=contact.last_name,
            company_domain=domain,
            mx_found=True,
            smtp_valid=None,
            raw={"mock": True},
        )

    @property
    def provider_name(self) -> str:
        return "MockEmailProvider (placeholder — not verified)"