"""
tests/unit/test_models.py

Tests for data model behaviour, especially __post_init__ normalisation.
"""

import pytest
from outreach.models import Company, Contact, VerifiedEmail, EmailStatus


class TestCompany:
    def test_domain_normalisation_strips_scheme(self):
        c = Company(domain="https://stripe.com/", name="Stripe")
        assert c.domain == "stripe.com"

    def test_domain_normalisation_lowercases(self):
        c = Company(domain="STRIPE.COM", name="Stripe")
        assert c.domain == "stripe.com"

    def test_str_representation(self):
        c = Company(domain="stripe.com", name="Stripe")
        assert str(c) == "Stripe (stripe.com)"


class TestContact:
    def test_full_name(self):
        c = Contact(first_name="Jane", last_name="Doe", title="CTO", company_domain="acme.com")
        assert c.full_name == "Jane Doe"

    def test_has_verified_email_false_by_default(self):
        c = Contact(first_name="Jane", last_name="Doe", title="CTO", company_domain="acme.com")
        assert not c.has_verified_email

    def test_has_verified_email_true_when_set(self):
        c = Contact(
            first_name="Jane",
            last_name="Doe",
            title="CTO",
            company_domain="acme.com",
            email="jane@acme.com",
        )
        assert c.has_verified_email


class TestVerifiedEmail:
    def test_is_sendable_only_for_valid(self):
        def make(status):
            return VerifiedEmail(
                email="a@b.com",
                status=status,
                contact_first_name="A",
                contact_last_name="B",
                company_domain="b.com",
            )

        assert make(EmailStatus.VALID).is_sendable
        assert not make(EmailStatus.RISKY).is_sendable
        assert not make(EmailStatus.INVALID).is_sendable
        assert not make(EmailStatus.UNKNOWN).is_sendable

    def test_str_representation(self):
        v = VerifiedEmail(
            email="jane@acme.com",
            status=EmailStatus.VALID,
            contact_first_name="Jane",
            contact_last_name="Doe",
            company_domain="acme.com",
        )
        assert str(v) == "jane@acme.com [valid]"
