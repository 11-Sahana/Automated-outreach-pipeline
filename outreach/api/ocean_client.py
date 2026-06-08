from typing import List

from outreach.api.base_client import BaseAPIClient
from outreach.config import Settings
from outreach.models import Company
from outreach.utils.retry import retry


class OceanClient(BaseAPIClient):

    @property
    def base_url(self) -> str:
        return self._settings.ocean_base_url

    def _auth_header(self):
        # Ocean v3 uses x-api-token, not X-API-KEY
        return {"x-api-token": self._settings.ocean_api_key}

    @retry(max_attempts=3, backoff_factor=2.0)
    def get_lookalikes(self, domain: str, limit: int | None = None) -> List[Company]:
        limit = limit or self._settings.ocean_lookalike_limit
        self._logger.info("Fetching %d lookalikes for '%s'", limit, domain)

        data = self.post(
            "/search/companies",
            json={
                "size": limit,
                "companiesFilters": {
                    "lookalikeDomains": [domain]
                }
            },
        )

        companies = [self._parse_company(item) for item in data.get("companies", [])]
        self._logger.info("Found %d lookalike companies", len(companies))
        return companies

    @staticmethod
    def _parse_company(raw: dict) -> Company:
        # Ocean v3 nests all company data under a "company" key
        c = raw.get("company", raw)  # fallback to raw itself if no nesting

        return Company(
            domain=c.get("domain", ""),
            name=c.get("name", ""),
            industry=c.get("industries", [None])[0],
            country=c.get("primaryCountry"),
            employee_count=c.get("employeeCountOcean"),
            description=c.get("description"),
            similarity_score=None,  # Ocean v3 returns 'relevance' (A/B/C) not a number
            raw=raw,
        )