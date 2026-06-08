# outreach-cli

A production-grade B2B outreach pipeline that finds lookalike companies, discovers contacts, verifies emails, and sends personalised outreach — all from one CLI command.

```
python main.py stripe.com --limit 5
```

---

## Architecture

```
main.py                     ← CLI (argparse, confirmation gate, progress output)
outreach/
  config.py                 ← Settings dataclass, env-var loading, validation
  models/                   ← Pure data classes (no business logic)
    company.py
    contact.py
    email.py
    campaign.py
  api/                      ← One client class per external API
    base_client.py          ← Shared HTTP, auth, error translation
    ocean_client.py         ← Lookalike discovery
    prospeo_client.py       ← Contact search
    eazyreach_client.py     ← Email verification
    brevo_client.py         ← Email sending
  services/
    outreach_service.py     ← Pipeline orchestrator (Step 1→4)
    template_service.py     ← Email copy / personalisation
  utils/
    logger.py               ← Structured logging factory
    retry.py                ← Retry decorator + APIError hierarchy
tests/
  unit/                     ← Fast, isolated, no network
  integration/              ← (scaffold) slow, real or recorded network
```

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| `BaseAPIClient` | Single place for auth, error translation, rate-limit delay. Adding a new API = one new subclass, no duplicated HTTP code. |
| `Settings` dataclass | All config in one place, type-annotated, easy to mock in tests. `validate()` fails fast before any network call. |
| `@retry` decorator | Separates retry policy from business logic. Jitter prevents thundering-herd. Non-retryable errors (4xx) raise immediately. |
| Named loggers (`outreach.*`) | Each module has its own logger; log output shows the exact source. Console uses colour when attached to a TTY. |
| Generator in `send_campaigns()` | Progress is shown incrementally; a failed send doesn't abort the rest. |
| Confirmation gate | Typed `yes` required before any real send — protects against accidental runs in production. |
| SOLID | **S**ingle responsibility per class; **O**pen for extension (new API client); **L**iskov (all clients are `BaseAPIClient`); **I**nterface segregation (models vs services vs API); **D**ependency injection (Settings passed in, not imported globally in clients). |

---

## Quickstart

### 1. Clone and set up

```bash
git clone <repo>
cd outreach_cli
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

### 3. Run

```bash
# Full pipeline (will ask for confirmation before sending)
python main.py stripe.com

# Limit to 5 lookalike companies
python main.py stripe.com --limit 5

# Dry run: all discovery steps, no emails sent
python main.py stripe.com --dry-run

# Debug logging
python main.py stripe.com --log-level DEBUG
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OCEAN_API_KEY` | ✅ | — | Ocean.io API key |
| `PROSPEO_API_KEY` | ✅ | — | Prospeo API key |
| `EAZYREACH_API_KEY` | ✅ | — | Eazyreach API key |
| `BREVO_API_KEY` | ✅ | — | Brevo (Sendinblue) API key |
| `SENDER_EMAIL` | ✅ | — | From address for outbound emails |
| `SENDER_NAME` | | `Outreach Bot` | Display name for sender |
| `OCEAN_LOOKALIKE_LIMIT` | | `10` | Max lookalike companies to fetch |
| `MAX_RETRIES` | | `3` | Retry attempts per API call |
| `RETRY_BACKOFF_FACTOR` | | `2.0` | Exponential back-off multiplier |
| `RATE_LIMIT_DELAY` | | `1.0` | Seconds between calls to the same API |
| `LOG_LEVEL` | | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | | — | If set, also writes logs to this file |

---

## Running Tests

```bash
# All unit tests
pytest tests/unit/

# With coverage report
pytest tests/unit/ --cov=outreach --cov-report=term-missing

# Single test file
pytest tests/unit/test_retry.py -v
```

---

## Pipeline flow

```
User input: stripe.com
     │
     ▼
[1] Ocean.io → 10 lookalike companies (Adyen, Braintree, …)
     │
     ▼
[2] Prospeo → C-suite + VP contacts per company
     │
     ▼
[3] Eazyreach → verified VALID email addresses only
     │
     ▼
   Preview table shown in terminal
     │
   User types 'yes' to confirm
     │
     ▼
[4] Brevo → personalised transactional emails sent
     │
     ▼
   Summary: N sent, M failed
```

---

## Extending the pipeline

**Add a new API integration:**
1. Create `outreach/api/newservice_client.py` inheriting `BaseAPIClient`
2. Implement `base_url`, `_auth_header()`, and your method(s)
3. Add the API key to `Settings` and `.env.example`
4. Inject the client into `OutreachService.__init__`

**Change email copy:**
Edit `outreach/services/template_service.py` — the `_subject`, `_text_body`, and `_html_body` methods are entirely self-contained.

---

## API Documentation

- [Ocean.io API](https://ocean.io/api-docs)
- [Prospeo API](https://prospeo.io/api)
- [Eazyreach API](https://eazyreach.io/docs)
- [Brevo Transactional Email API](https://developers.brevo.com/reference/sendtransacemail)
