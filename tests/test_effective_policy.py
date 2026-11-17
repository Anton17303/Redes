"""Effective Azure NSG and Network Manager layers, using synthetic IDs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_deployment import effective_association

EXPECTED = "/synthetic/NSG-DMZ"


class EffectivePolicyTests(unittest.TestCase):
    def fixture(self):
        return {"value": [
            {"networkSecurityGroup": {"id": EXPECTED}, "effectiveSecurityRules": [{"access": "Allow"}]},
            {"networkSecurityGroup": {}, "association": {"networkManager": {"id": "/synthetic/manager"}},
             "effectiveSecurityRules": [{"name": "DefaultIPv6OutboundDeny", "access": "Deny"}]}
        ]}

    def test_expected_nsg_and_restrictive_admin_layer_are_recognized(self):
        valid, detail = effective_association(self.fixture(), EXPECTED)
        self.assertTrue(valid)
        self.assertEqual(detail["additional_admin_denies"], ["DefaultIPv6OutboundDeny"])

    def test_bypass_unknown_layer_or_extra_nsg_is_rejected(self):
        changes = [lambda d: d["value"][1]["effectiveSecurityRules"][0].update(access="AlwaysAllow"),
                   lambda d: d["value"][1]["effectiveSecurityRules"][0].update(access="Allow"),
                   lambda d: d["value"][1].update(association={}),
                   lambda d: d["value"][1].update(effectiveSecurityRules=[]),
                   lambda d: d["value"].append({"networkSecurityGroup": {"id": "/synthetic/other"}})]
        for change in changes:
            data = self.fixture()
            change(data)
            with self.subTest(change=change):
                self.assertFalse(effective_association(data, EXPECTED)[0])


if __name__ == "__main__":
    unittest.main()
