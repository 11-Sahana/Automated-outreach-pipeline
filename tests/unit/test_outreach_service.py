"""
tests/unit/test_outreach_service.py

Integration-level unit test: OutreachService with all API clients mocked.
This verifies the pipeline orchestration logic without any network calls.
"""

import pytest
from unittest.mock import MagicMock, patch, create_autospec

from outreach.services.outreach_service import OutreachService
from outreach.models import Company, Contact, VerifiedEmail, EmailStatus, CampaignResult
from outreach.config import Settings


@pytest.fixture
def settings():
    return Settings(
        ocean_api_key="k",
        prospeo_api_key="k",
        eazyreach_api_key="k",
        brevo_api_key="k",
        sender_email="sender@test.com",
        sender_name="Test Bot",
        rate_limit_delay=0,
    )


@pytest.fixture
def service(settings):
    svc = OutreachService(settings)
    # Replace real clients with mocks
    svc._ocean = MagicMock()
    svc._prospeo = MagicMock()
    svc._eazyreach = MagicMock()
    svc._brevo = MagicMock()
    return svc


def make_company(domain="acme.com"):
    return Company(domain=domain, name="ACME")


def make_contact(domain="acme.com"):
    return Contact(
        first_name="Jane",
        last_name="Doe",
        title="CTO",
        company_domain=domain,
        company_name="ACME",
    )


def make_verified(email="jane@acme.com"):
    return VerifiedEmail(
        email=email,
        status=EmailStatus.VALID,
        contact_first_name="Jane",
        contact_last_name="Doe",
        company_domain="acme.com",
    )


class TestOutreachService:
    def test_find_lookalikes_returns_companies(self, service):
        service._ocean.get_lookalikes.return_value = [make_company()]
        result = service.find_lookalikes("stripe.com")
        assert len(result) == 1
        service._ocean.get_lookalikes.assert_called_once_with("stripe.com")

    def test_find_lookalikes_handles_api_error(self, service):
        from outreach.utils.retry import APIError
        service._ocean.get_lookalikes.side_effect = APIError("boom", status_code=500)
        result = service.find_lookalikes("stripe.com")
        assert result == []  # graceful degradation

    def test_verify_emails_filters_non_sendable(self, service):
        contacts = [make_contact()]
        risky = VerifiedEmail(
            email="jane@acme.com",
            status=EmailStatus.RISKY,
            contact_first_name="Jane",
            contact_last_name="Doe",
            company_domain="acme.com",
        )
        service._eazyreach.find_email.return_value = risky
        result = service.verify_emails(contacts)
        # RISKY emails should not be returned
        assert result == []

    def test_verify_emails_includes_valid(self, service):
        contacts = [make_contact()]
        service._eazyreach.find_email.return_value = make_verified()
        result = service.verify_emails(contacts)
        assert len(result) == 1
        assert contacts[0].email == "jane@acme.com"  # contact updated in place

    def test_send_campaigns_yields_results(self, service):
        contact = make_contact()
        contact.email = "jane@acme.com"
        verified = [make_verified()]
        campaigns = service.build_campaigns([contact], verified, "stripe.com")

        mock_result = MagicMock(spec=CampaignResult, success=True)
        service._brevo.send_email.return_value = mock_result

        results = list(service.send_campaigns(campaigns))
        assert len(results) == 1
        assert results[0].success is True
