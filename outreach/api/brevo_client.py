"""
brevo_client.py – Transactional email sending via Brevo (formerly Sendinblue).

API docs: https://developers.brevo.com/reference/sendtransacemail
"""

from outreach.api.base_client import BaseAPIClient
from outreach.models import OutreachCampaign, CampaignResult
from outreach.utils.retry import retry


class BrevoClient(BaseAPIClient):
    """Sends transactional outreach emails via the Brevo API."""

    @property
    def base_url(self) -> str:
        return self._settings.brevo_base_url

    def _auth_header(self):
        # Brevo uses the api-key header (not Bearer)
        return {"api-key": self._settings.brevo_api_key}

    @retry(max_attempts=3, backoff_factor=2.0)
    def send_email(self, campaign: OutreachCampaign) -> CampaignResult:
        """
        Send one transactional email.

        Args:
            campaign: Fully populated OutreachCampaign object.

        Returns:
            CampaignResult with success flag and Brevo message ID.
        """
        self._logger.info(
            "Sending email to %s <%s>", campaign.to_name, campaign.to_email
        )

        payload = {
            "sender": {
                "name": campaign.sender_name,
                "email": campaign.sender_email,
            },
            "to": [{"email": campaign.to_email, "name": campaign.to_name}],
            "subject": campaign.subject,
            "htmlContent": campaign.html_body,
            "textContent": campaign.text_body,
        }

        data = self.post("/smtp/email", json=payload)
        message_id = data.get("messageId")

        self._logger.info(
            "Email sent to %s — messageId=%s", campaign.to_email, message_id
        )
        return CampaignResult(
            campaign=campaign,
            success=True,
            message_id=message_id,
        )
