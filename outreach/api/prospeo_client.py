from typing import List

from outreach.api.base_client import BaseAPIClient
from outreach.models import Contact, ContactTitle
from outreach.utils.retry import retry


class ProspeoClient(BaseAPIClient):

    @property
    def base_url(self) -> str:
        return self._settings.prospeo_base_url

    def _auth_header(self):
        return {"X-KEY": self._settings.prospeo_api_key}

    @retry(max_attempts=3, backoff_factor=2.0)
    def get_contacts(
        self,
        domain: str,
        titles: List[ContactTitle] | None = None,
    ) -> List[Contact]:
        self._logger.info("Searching Prospeo contacts at '%s'", domain)

        data = self.post(
            "/search-person",
            json={
                "page": 1,
                "filters": {
                    "company": {
                        "websites": {
                            "include": [domain]
                        }
                    },
                    "person_seniority": {
                    "include": [
                        "C-Suite",
                        "Founder/Owner",
                        "Partner",
                        "Vice President",
                        "Head",
                        "Director"
                    ]
                }
                }
            },
        )

        # Prospeo returns {"error": true} on failure
        if data.get("error"):
            self._logger.warning(
                "Prospeo error for '%s': %s", domain, data.get("error_code")
            )
            return []

        results = data.get("results", [])
        contacts = [self._parse_contact(r, domain) for r in results]
        self._logger.info("Found %d contacts at '%s'", len(contacts), domain)
        return contacts

    @staticmethod
    def _parse_contact(raw: dict, domain: str) -> Contact:
        person = raw.get("person", {})
        company = raw.get("company", {})

        return Contact(
            first_name=person.get("first_name", ""),
            last_name=person.get("last_name", ""),
            title=person.get("job_title", ""),
            company_domain=domain,
            company_name=company.get("name"),
            linkedin_url=person.get("linkedin_url"),
            raw=raw,
        )