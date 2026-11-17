"""Synthetic balances only; verify protection before any billable deployment."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_credit_guard import validate_credit

SUB = "00000000-0000-0000-0000-000000000001"
NOW = datetime(2026, 11, 17, 14, tzinfo=timezone.utc)


class CreditGuardTests(unittest.TestCase):
    def fixture(self):
        return ({"subscriptionId": SUB, "state": "Enabled", "subscriptionPolicies": {"spendingLimit": "On"}},
                {"subscription_id": SUB, "reviewed_at_utc": NOW.isoformat(),
                 "expires_on": "2027-01-01", "available_lower_bound_usd": "10.00"})

    def test_enabled_protection_and_sufficient_credit(self):
        subscription, review = self.fixture()
        self.assertTrue(validate_credit(subscription, review, SUB, "1.00", NOW)["credit_covers_approved_budget"])

    def test_unknown_off_or_temporary_off_protection_rejected(self):
        for state in (None, "Off", "CurrentPeriodOff"):
            with self.subTest(state=state):
                subscription, review = self.fixture()
                subscription["subscriptionPolicies"]["spendingLimit"] = state
                with self.assertRaises(ValueError):
                    validate_credit(subscription, review, SUB, "1.00", NOW)

    def test_old_future_expired_or_mismatched_review_rejected(self):
        for change in ({"reviewed_at_utc": (NOW - timedelta(hours=25)).isoformat()},
                       {"reviewed_at_utc": (NOW + timedelta(hours=1)).isoformat()},
                       {"reviewed_at_utc": "2026-11-17T14:00:00"},
                       {"expires_on": "2026-11-17"}, {"subscription_id": "other"}):
            with self.subTest(change=change):
                subscription, review = self.fixture()
                review.update(change)
                with self.assertRaises(ValueError):
                    validate_credit(subscription, review, SUB, "1.00", NOW)

    def test_excessive_nonfinite_or_nonpositive_budget_rejected(self):
        for amount in ("11.00", "NaN", "Infinity", "0", "-1"):
            with self.subTest(amount=amount):
                subscription, review = self.fixture()
                with self.assertRaises(ValueError):
                    validate_credit(subscription, review, SUB, amount, NOW)
