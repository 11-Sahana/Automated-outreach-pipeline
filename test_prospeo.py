from outreach.config import settings
from outreach.api.prospeo_client import ProspeoClient

print("Config loaded:", settings.redacted_repr())

client = ProspeoClient(settings)
contacts = client.get_contacts("razorpay.com")

print("\nRaw first result:", contacts[0].raw if contacts else "No contacts found")
print(f"\nFound {len(contacts)} contacts:\n")
for c in contacts:
    print(f"  • {c.full_name} — {c.title} — {c.company_domain}")
