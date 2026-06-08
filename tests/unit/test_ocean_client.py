"""
tests/unit/test_ocean_client.py

We test the Ocean client by patching the _request method on BaseAPIClient.
This tests our parsing logic without hitting the real API.

Pattern: Always mock at the boundary closest to the external system.
"""

import pytest
from unittest.mock import MagicMock, patch

from outreach.api.ocean_client import OceanClient
from outreach.config import Settings


@pytest.fixture
def settings():
    return Settings(
        ocean_api_key="test-key",
        ocean_base_url="https://api.ocean.io/v1",
        ocean_lookalike_limit=5,
        prospeo_api_key="x",
        eazyreach_api_key="x",
        brevo_api_key="x",
        sender_email="test@test.com",
        rate_limit_delay=0,  # don't sleep in tests
    )


@pytest.fixture
def client(settings):
    return OceanClient(settings)


SAMPLE_RESPONSE = {
    "results": [
        {
            "domain": "adyen.com",
            "name": "Adyen",
            "industry": "Fintech",
            "country": "NL",
            "employee_count": 3000,
            "similarity_score": 0.91,
        },
        {
            "domain": "braintreepayments.com",
            "name": "Braintree",
            "industry": "Fintech",
            "country": "US",
            "similarity_score": 0.84,
        },
    ]
}


class TestOceanClient:
    def test_get_lookalikes_returns_companies(self, client):
        with patch.object(client, "post", return_value=SAMPLE_RESPONSE):
            companies = client.get_lookalikes("stripe.com")

        assert len(companies) == 2
        assert companies[0].domain == "adyen.com"
        assert companies[0].similarity_score == 0.91
        assert companies[1].domain == "braintreepayments.com"

    def test_get_lookalikes_empty_results(self, client):
        with patch.object(client, "post", return_value={"results": []}):
            companies = client.get_lookalikes("unknown.com")

        assert companies == []

    def test_get_lookalikes_passes_limit(self, client):
        with patch.object(client, "post", return_value={"results": []}) as mock_post:
            client.get_lookalikes("stripe.com", limit=7)

        mock_post.assert_called_once_with(
            "/lookalike",
            json={"domain": "stripe.com", "limit": 7},
        )

    def test_parse_company_normalises_domain(self, client):
        raw = {"domain": "Adyen.com", "name": "Adyen"}
        company = OceanClient._parse_company(raw)
        assert company.domain == "adyen.com"

    def test_parse_company_strips_scheme_if_present(self, client):
        raw = {"domain": "https://Adyen.com/", "name": "Adyen"}
        company = OceanClient._parse_company(raw)
        assert company.domain == "adyen.com"
