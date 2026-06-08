#!/usr/bin/env python3
"""
main.py – CLI entry point for the outreach pipeline.

Usage:
    python main.py stripe.com
    python main.py stripe.com --limit 5
    python main.py stripe.com --dry-run
    python main.py --help

Design rationale
----------------
*  argparse (stdlib) over Click/Typer — no extra dependency for a simple CLI.
*  The main() function is kept thin: parse args → validate config → run service.
   All business logic lives in OutreachService, making main() trivially
   testable by asserting it calls the right methods.
*  Confirmation prompt before any real email is sent — this is non-negotiable
   when a script can trigger hundreds of outbound emails.
*  Exit codes follow Unix conventions: 0 = success, 1 = user error / config,
   2 = runtime failure.
"""

import argparse
import sys
from typing import List

from outreach.config import settings
from outreach.services import OutreachService
from outreach.utils.logger import configure_logging, get_logger


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="outreach",
        description="Automated B2B outreach pipeline — find lookalikes, contacts, and send emails.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py stripe.com
  python main.py stripe.com --limit 5
  python main.py stripe.com --dry-run
        """,
    )
    parser.add_argument(
        "domain",
        help="Source company domain to find lookalikes for (e.g. stripe.com)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Max number of lookalike companies (default: OCEAN_LOOKALIKE_LIMIT in .env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all discovery steps but skip sending emails. Safe for testing.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override LOG_LEVEL from environment",
    )
    return parser.parse_args(argv)


def _confirm_send(campaign_count: int, domain: str) -> bool:
    """
    Block until the user explicitly types 'yes'.
    Any other input (including just pressing Enter) aborts.

    This is the safety gate that prevents accidental mass sends.
    """
    print("\n" + "=" * 60)
    print(f"  READY TO SEND {campaign_count} EMAIL(S)")
    print(f"  Source domain : {domain}")
    print("=" * 60)
    print("  This will send real emails to real people.")
    print("  Review the campaign details above before confirming.")
    print()
    answer = input("  Type 'yes' to confirm, anything else to abort: ").strip().lower()
    return answer == "yes"


def _print_campaign_preview(campaigns) -> None:
    """Human-readable preview of what will be sent."""
    print(f"\n{'─' * 60}")
    print(f"  CAMPAIGN PREVIEW ({len(campaigns)} emails)")
    print(f"{'─' * 60}")
    for i, c in enumerate(campaigns, 1):
        print(f"  {i:>3}. To:      {c.to_name} <{c.to_email}>")
        print(f"       Company: {c.company_domain}")
        print(f"       Subject: {c.subject}")
        print()


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)

    # Logging must be configured before the first logger.getLogger() call
    log_level = args.log_level or settings.log_level
    configure_logging(level=log_level, log_file=settings.log_file)
    logger = get_logger("main")

    # Validate config early — fail before any network calls
    try:
        settings.validate()
    except ValueError as exc:
        print(f"\n❌  Configuration error:\n{exc}", file=sys.stderr)
        return 1

    logger.info("Starting outreach pipeline for domain: %s", args.domain)
    logger.debug("Active config: %s", settings.redacted_repr())

    from outreach.api.mock_email_provider import MockEmailProvider
    from outreach.api.brevo_client import BrevoClient

    email_provider = MockEmailProvider()
    brevo = BrevoClient(settings) if settings.brevo_api_key not in (None, "dummy") else None

    service = OutreachService(
        settings=settings,
        email_provider=email_provider,
        brevo_client=brevo,
    )
    # ── Step 1: Lookalikes ─────────────────────────────────────────────────
    companies = service.find_lookalikes(args.domain, limit=args.limit) if args.limit \
        else service.find_lookalikes(args.domain)

    if not companies:
        print(f"\n⚠️  No lookalike companies found for '{args.domain}'. Exiting.")
        return 0

    print(f"\n✓ Found {len(companies)} lookalike companies:")
    for c in companies:
        score = f" (similarity: {c.similarity_score:.0%})" if c.similarity_score else ""
        print(f"  • {c}{score}")

    # ── Step 2: Contacts ───────────────────────────────────────────────────
    contacts = service.find_contacts(companies)
    if not contacts:
        print("\n⚠️  No contacts found. Exiting.")
        return 0

    print(f"\n✓ Found {len(contacts)} contacts")

    # ── Step 3: Email verification ─────────────────────────────────────────
    verified = service.verify_emails(contacts)
    if not verified:
        print("\n⚠️  No sendable verified emails found. Exiting.")
        return 0

    print(f"\n✓ {len(verified)} verified sendable email(s)")

    # ── Step 4: Build & send campaigns ────────────────────────────────────
    campaigns = service.build_campaigns(contacts, verified, args.domain)
    _print_campaign_preview(campaigns)

    if args.dry_run:
        print("\n🔵  DRY RUN — no emails sent. Remove --dry-run to send for real.")
        return 0

    if not _confirm_send(len(campaigns), args.domain):
        print("\n🔴  Aborted. No emails sent.")
        return 0

    sent, failed = 0, 0
    for result in service.send_campaigns(campaigns):
        if result.success:
            sent += 1
            print(f"  ✓ Sent → {result.campaign.to_email}")
        else:
            failed += 1
            print(f"  ✗ Failed → {result.campaign.to_email}: {result.error}")

    print(f"\n{'─' * 60}")
    print(f"  Pipeline complete: {sent} sent, {failed} failed")
    print(f"{'─' * 60}\n")

    logger.info("Pipeline finished — sent=%d failed=%d", sent, failed)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
