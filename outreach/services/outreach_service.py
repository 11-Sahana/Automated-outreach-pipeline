"""
outreach_service.py – Pipeline orchestrator.

OutreachService receives all its dependencies via the constructor.
It has no knowledge of which EmailProvider is in use — it calls
find_email() on whatever was injected. Swapping MockEmailProvider
for HunterProvider tomorrow requires zero changes here.
"""
from typing import Generator, List, Optional

from outreach.api.ocean_client import OceanClient
from outreach.api.prospeo_client import ProspeoClient
from outreach.api.email_provider import EmailProvider
from outreach.api.brevo_client import BrevoClient
from outreach.config import Settings
from outreach.models import Company, Contact, CampaignResult, VerifiedEmail
from outreach.services.template_service import TemplateService
from outreach.utils.logger import get_logger
from outreach.utils.retry import APIError


class OutreachService:
    """
    Coordinates the pipeline:
        domain → lookalikes → contacts → emails → campaigns → send
    """

    def __init__(
        self,
        settings: Settings,
        email_provider: EmailProvider,
        brevo_client: Optional[BrevoClient] = None,
    ) -> None:
        self._settings = settings
        self._logger = get_logger(__name__)
        self._ocean = OceanClient(settings)
        self._prospeo = ProspeoClient(settings)
        self._email_provider = email_provider
        self._brevo = brevo_client
        self._templates = TemplateService(settings)

        self._logger.info(
            "OutreachService ready — email provider: %s",
            self._email_provider.provider_name,
        )

    def find_lookalikes(self, domain: str, limit: Optional[int] = None) -> List[Company]:
        self._logger.info("=== Step 1/4: Lookalike discovery for '%s' ===", domain)
        try:
            if limit is None:
                return self._ocean.get_lookalikes(domain)
            return self._ocean.get_lookalikes(domain, limit=limit)
        except APIError as exc:
            self._logger.error("Ocean.io failed for '%s': %s", domain, exc)
            return []

    def find_contacts(self, companies: List[Company]) -> List[Contact]:
        self._logger.info(
            "=== Step 2/4: Contact discovery for %d companies ===", len(companies)
        )
        all_contacts: List[Contact] = []
        for company in companies:
            try:
                contacts = self._prospeo.get_contacts(company.domain)
                all_contacts.extend(contacts)
            except APIError as exc:
                self._logger.warning(
                    "Prospeo failed for '%s': %s — skipping", company.domain, exc
                )
        self._logger.info("Total contacts found: %d", len(all_contacts))
        return all_contacts

    def verify_emails(self, contacts: List[Contact]) -> List[VerifiedEmail]:
        self._logger.info(
            "=== Step 3/4: Email lookup via %s ===",
            self._email_provider.provider_name,
        )
        verified: List[VerifiedEmail] = []
        for contact in contacts:
            try:
                result = self._email_provider.find_email(contact)
                if result and result.is_sendable:
                    contact.email = result.email
                    verified.append(result)
                elif result:
                    self._logger.debug(
                        "Skipping %s — email not sendable", contact.full_name
                    )
            except Exception as exc:
                self._logger.warning(
                    "Email lookup failed for %s: %s — skipping",
                    contact.full_name, exc,
                )
        self._logger.info(
            "%d sendable emails from %d contacts", len(verified), len(contacts)
        )
        return verified

    def build_campaigns(
        self,
        contacts: List[Contact],
        verified_emails: List[VerifiedEmail],
        source_domain: str,
    ):
        email_by_address = {v.email: v for v in verified_emails}
        campaigns = []
        for contact in contacts:
            if contact.email and contact.email in email_by_address:
                campaign = self._templates.build_campaign(
                    contact, email_by_address[contact.email], source_domain
                )
                campaigns.append(campaign)
        return campaigns

    def send_campaigns(self, campaigns) -> Generator[CampaignResult, None, None]:
        if not self._brevo:
            self._logger.warning(
                "No Brevo client configured — skipping send. "
                "Set BREVO_API_KEY to enable real sending."
            )
            return

        self._logger.info("=== Step 4/4: Sending %d emails ===", len(campaigns))
        for campaign in campaigns:
            try:
                result = self._brevo.send_email(campaign)
                yield result
            except APIError as exc:
                self._logger.error(
                    "Failed to send to %s: %s", campaign.to_email, exc
                )
                yield CampaignResult(
                    campaign=campaign,
                    success=False,
                    error=str(exc),
                )