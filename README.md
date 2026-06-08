# outreach-cli

A production-grade B2B outreach CLI that finds lookalike companies, discovers decision-makers, generates personalised emails, and optionally sends them — all from one command.

```bash
python main.py stripe.com --dry-run
```

---

## What it does
Your input: stripe.com
│
▼
[1] Ocean.io      → 10 lookalike companies (Razorpay, Adyen, GoCardless…)
│
▼
[2] Prospeo       → C-suite + VP contacts per company (202 decision-makers)
│
▼
[3] EmailProvider → Work email per contact (Mock by default, swap for Hunter/Eazyreach)
│
▼
Campaign preview shown in terminal
│
Type 'yes' to confirm
│
▼
[4] Brevo         → Personalised transactional emails sent (optional)

---

## Architecture
outreach_cli/
├── main.py                          ← CLI shell (argparse + safety confirmation)
└── outreach/
├── config.py                    ← Settings dataclass loaded from env vars
├── api/
│   ├── base_client.py           ← Shared HTTP, auth, retry, error handling
│   ├── ocean_client.py          ← Lookalike company discovery (Ocean.io v3)
│   ├── prospeo_client.py        ← Contact/decision-maker search (Prospeo)
│   ├── email_provider.py        ← Abstract interface (EmailProvider ABC)
│   ├── mock_email_provider.py   ← Default: generates placeholder emails
│   └── brevo_client.py          ← Optional: transactional email sending
├── models/
│   ├── company.py               ← Company dataclass
│   ├── contact.py               ← Contact dataclass + ContactTitle enum
│   ├── email.py                 ← VerifiedEmail + EmailStatus enum
│   └── campaign.py              ← OutreachCampaign + CampaignResult
├── services/
│   ├── outreach_service.py      ← Pipeline orchestrator (dependency injection)
│   └── template_service.py      ← Personalised email copy generator
└── utils/
├── logger.py                ← Named loggers, colour TTY output
└── retry.py                 ← Retry decorator with exponential back-off

### Key design decisions

| Decision | Why |
|---|---|
| `EmailProvider` abstract interface | Swap Mock → Hunter → Eazyreach with one line change. Zero modifications to business logic. |
| Dependency injection in `OutreachService` | All providers passed via constructor. Fully testable without any real API calls. |
| `BaseAPIClient` inheritance | Auth, rate-limiting, error translation written once. New API = one new subclass, ~40 lines. |
| `@retry` with jitter | Exponential back-off + ±10% random jitter prevents thundering herd on 429s. |
| Generator in `send_campaigns()` | Progress shown incrementally. One failure doesn't abort the rest. |
| Typed confirmation gate | Must type `yes` exactly before any emails send. Accidental runs are impossible. |
| SOLID throughout | Single responsibility per class, open for extension, Liskov-safe, interface segregation, dependency inversion. |

---

## Quickstart

### 1. Clone and set up

```bash
git clone <your-repo-url>
cd outreach_cli
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Minimum required to run:
OCEAN_API_KEY=your_key
PROSPEO_API_KEY=your_key

### 3. Run

```bash
# Safe dry run — full pipeline, no emails sent
python main.py stripe.com --dry-run

# Limit to 5 lookalike companies
python main.py stripe.com --limit 5 --dry-run

# Full run with confirmation prompt
python main.py stripe.com

# Debug logging
python main.py stripe.com --dry-run --log-level DEBUG
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OCEAN_API_KEY` | ✅ | — | Ocean.io API key |
| `OCEAN_BASE_URL` | | `https://api.ocean.io/v3` | Ocean API base URL |
| `OCEAN_LOOKALIKE_LIMIT` | | `10` | Max lookalike companies |
| `PROSPEO_API_KEY` | ✅ | — | Prospeo API key |
| `PROSPEO_BASE_URL` | | `https://api.prospeo.io` | Prospeo base URL |
| `BREVO_API_KEY` | | — | Optional — only needed for real sends |
| `SENDER_EMAIL` | | — | Optional — only needed for real sends |
| `SENDER_NAME` | | `Outreach Bot` | Display name for sender |
| `MAX_RETRIES` | | `3` | Retry attempts per API call |
| `RETRY_BACKOFF_FACTOR` | | `2.0` | Exponential back-off multiplier |
| `RATE_LIMIT_DELAY` | | `1.0` | Seconds between calls to the same API |
| `LOG_LEVEL` | | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | | — | If set, also writes logs to this file |

---

## Adding a new email provider

The system is designed so you can plug in Hunter.io, Eazyreach, or any other provider without touching existing code:

**Step 1** — Create `outreach/api/hunter_provider.py`:

```python
from outreach.api.email_provider import EmailProvider
from outreach.models import Contact, VerifiedEmail

class HunterProvider(EmailProvider):
    def find_email(self, contact: Contact) -> Optional[VerifiedEmail]:
        # call Hunter.io API here
        ...
```

**Step 2** — Change one line in `main.py`:

```python
# Before
email_provider = MockEmailProvider()

# After
email_provider = HunterProvider(settings)
```

That's it. `OutreachService` never changes.

---

## Running Tests

```bash
pytest tests/unit/ -v
pytest tests/unit/ --cov=outreach --cov-report=term-missing
```

---

## Sample output
✓ Found 10 lookalike companies:
• Razorpay (razorpay.com)
• Cashfree Payments (cashfree.com)
• Adyen (adyen.com)
...
✓ Found 202 contacts
✓ 202 verified sendable email(s)
────────────────────────────────────────────
CAMPAIGN PREVIEW (202 emails)
────────────────────────────────────────────
1. To:      Akhil Joshi akhil.joshi@razorpay.com
Subject: Quick question, Akhil — connecting companies like stripe.com with razorpay.com
...
🔵  DRY RUN — no emails sent. Remove --dry-run to send for real.

---

## Tech stack

- Python 3.11+
- `requests` — HTTP client
- `python-dotenv` — environment variable loading
- `pytest` — unit testing

No heavy frameworks. Clean, readable, production-quality Python.

---

## API Documentation

- [Ocean.io v3 API](https://app.ocean.io/docs/searchCompaniesV3)
- [Prospeo API](https://prospeo.io/api-docs/search-person)
- [Brevo Transactional Email API](https://developers.brevo.com/reference/sendtransacemail)