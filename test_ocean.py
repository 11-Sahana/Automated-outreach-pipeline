from outreach.config import settings
from outreach.api.ocean_client import OceanClient

# Print which key is loaded (masked for safety)
print("Config loaded:", settings.redacted_repr())

client = OceanClient(settings)
companies = client.get_lookalikes("stripe.com", limit=3)

print("\nRaw first result:", companies[0].raw)

print(f"\nFound {len(companies)} companies:\n")
for c in companies:
    print(f"  • {c.name} — {c.domain} — similarity: {c.similarity_score}")