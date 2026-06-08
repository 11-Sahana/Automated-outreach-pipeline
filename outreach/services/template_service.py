"""
template_service.py – Builds personalised email copy.

Design rationale
----------------
*  Personalisation tokens are kept to facts we *actually know* so we never
   generate hallucinated company details.
*  HTML and plain-text versions are always produced together — Brevo (and good
   ESP practice) sends multipart/alternative so recipients with text-only
   clients still get something readable.
*  Templates live in this service rather than in string constants scattered
   across the codebase.  When marketing wants to A/B test copy, they change
   one file.
"""

from outreach.models import OutreachCampaign, VerifiedEmail, Contact
from outreach.config import Settings
from outreach.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateService:
    """Generates personalised OutreachCampaign objects."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_campaign(
        self,
        contact: Contact,
        verified_email: VerifiedEmail,
        source_domain: str,
    ) -> OutreachCampaign:
        """
        Construct a campaign for one contact.

        Args:
            contact:         The person we're reaching out to.
            verified_email:  Their verified address.
            source_domain:   The original domain the user typed (used for context).
        """
        subject = self._subject(contact, source_domain)
        text_body = self._text_body(contact, source_domain)
        html_body = self._html_body(contact, source_domain)

        logger.debug(
            "Built campaign for %s <%s>", contact.full_name, verified_email.email
        )

        return OutreachCampaign(
            to_email=verified_email.email,
            to_name=contact.full_name,
            company_name=contact.company_name or contact.company_domain,
            company_domain=contact.company_domain,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            sender_email=self._settings.sender_email,
            sender_name=self._settings.sender_name,
        )

    # ── Copy ──────────────────────────────────────────────────────────────────

    def _subject(self, contact: Contact, source_domain: str) -> str:
        return (
            f"Quick question, {contact.first_name} — "
            f"connecting companies like {source_domain} with {contact.company_domain}"
        )

    def _text_body(self, contact: Contact, source_domain: str) -> str:
        company = contact.company_name or contact.company_domain
        return f"""\
Hi {contact.first_name},

I noticed that {company} and {source_domain} operate in a very similar space, \
and I thought it would be worth reaching out directly.

I'd love to explore whether there's a fit between what we're building and \
the challenges your team is working through as {contact.title} at {company}.

Would you be open to a 20-minute call this week or next?

Best,
{self._settings.sender_name}
"""

    def _html_body(self, contact: Contact, source_domain: str) -> str:
        company = contact.company_name or contact.company_domain
        text = self._text_body(contact, source_domain)
        # Simple, spam-filter-friendly HTML — avoid heavy inline CSS
        paragraphs = "".join(
            f"<p>{line}</p>" for line in text.strip().split("\n\n")
        )
        return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;font-size:15px;color:#222;max-width:600px;margin:0 auto;">
  {paragraphs}
</body>
</html>
"""
