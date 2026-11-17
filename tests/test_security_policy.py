"""Synthetic network state and mutation contracts, not Azure evidence."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from security_policy import NETWORKS, apply_operation, build_plan, desired_rules, normalize
from hardening import make_script
from verify_network import classify

SUB = "00000000-0000-0000-0000-000000000001"
BASE = f"/subscriptions/{SUB}/resourceGroups/RG-CafeNube/providers/Microsoft.Network/"


def inventory(complete=False):
    policies = desired_rules()
    segments = list(NETWORKS) if complete else list(NETWORKS)[:-1]
    subnets = [{"id": BASE + "virtualNetworks/VNet-CafeNube/subnets/Subnet-" + s,
                "name": "Subnet-" + s, "addressPrefix": NETWORKS[s],
                "networkSecurityGroup": {"id": BASE + "networkSecurityGroups/NSG-" + s}} for s in segments]
    nsgs = [{"id": BASE + "networkSecurityGroups/NSG-" + s, "name": "NSG-" + s,
             "location": "northcentralus", "securityRules": copy.deepcopy(policies["NSG-" + s]) if complete else []} for s in segments]
    return dict(account={"id": SUB, "state": "Enabled"}, subscription=SUB, nics=[], nsgs=nsgs,
                vnet={"id": BASE + "virtualNetworks/VNet-CafeNube", "location": "northcentralus",
                      "addressSpace": {"addressPrefixes": ["10.0.0.0/16"]}, "subnets": subnets})


class SecurityPolicyTests(unittest.TestCase):
    def test_existing_network_creates_only_missing_dmz_and_nsg(self):
        plan = build_plan(**inventory())
        self.assertEqual([o["name"] for o in plan["operations"] if o["action"] == "create-subnet"], ["Subnet-DMZ"])
        self.assertFalse(plan["billable_resources_created"])
        actions = [o["action"] for o in plan["operations"]]
        self.assertLess(actions.index("create-nsg"), actions.index("create-subnet"))
        for op in plan["operations"]:
            with patch("security_policy.request", return_value={}) as request:
                apply_operation(op)
                args = request.call_args.args
                self.assertNotIn("delete", args)
                self.assertNotIn("nat", args)
                self.assertEqual(args[0], "network")

    def test_complete_policy_converges_and_supports_singular_azure_fields(self):
        data = inventory(True)
        for nsg in data["nsgs"]:
            for r in nsg["securityRules"]:
                for plural, singular in (("sourceAddressPrefixes", "sourceAddressPrefix"),
                                         ("destinationAddressPrefixes", "destinationAddressPrefix"),
                                         ("sourcePortRanges", "sourcePortRange"), ("destinationPortRanges", "destinationPortRange")):
                    if len(r[plural]) == 1:
                        r[singular] = r.pop(plural)[0]
        self.assertEqual(build_plan(**data)["operations"], [])

    def test_conflicts_unknown_rules_routes_and_shared_nsg_are_rejected(self):
        changes = [lambda d: d["nsgs"][0]["securityRules"].append({"name": "unreviewed"}),
                   lambda d: d["nsgs"][0]["securityRules"][0].update(priority=4000),
                   lambda d: d["vnet"]["subnets"][0].update(addressPrefix="10.0.0.0/24"),
                   lambda d: d["vnet"]["subnets"][0].update(routeTable={"id": "unknown"}),
                   lambda d: d["nics"].append({"networkSecurityGroup": {"id": d["nsgs"][0]["id"]}}),
                   lambda d: d["vnet"]["subnets"][1].update(networkSecurityGroup={"id": d["nsgs"][0]["id"]})]
        for change in changes:
            with self.subTest(change=change):
                data = inventory(True)
                change(data)
                with self.assertRaises(ValueError):
                    build_plan(**data)

    def test_legacy_sales_rule_narrowed_in_place_and_no_tls_opening(self):
        data = inventory(True)
        legacy = next(r for r in data["nsgs"][3]["securityRules"] if r["name"] == "Allow-Ventas")
        legacy.update(destinationAddressPrefixes=["10.0.0.128/28"], destinationPortRanges=["*"])
        plan = build_plan(**data)
        self.assertEqual(len(plan["operations"]), 1)
        self.assertEqual(plan["operations"][0]["rule"]["destinationPortRanges"], ["53"])
        self.assertTrue(all("443" not in r["destinationPortRanges"] for rules in desired_rules().values() for r in rules))

    def test_observed_phase_one_rules_are_updated_without_priority_collisions(self):
        data = inventory()
        data["nsgs"][0]["securityRules"] = [dict(name="Deny-Visitas-Interno", priority=100,
            direction="Outbound", access="Deny", protocol="*", sourceAddressPrefix="*",
            destinationAddressPrefix="10.0.0.0/16", sourcePortRange="*", destinationPortRange="*")]
        data["nsgs"][1]["securityRules"] = [dict(name="Deny-Visitas-Ventas", priority=100,
            direction="Inbound", access="Deny", protocol="*", sourceAddressPrefix="10.0.0.0/26",
            destinationAddressPrefix="*", sourcePortRange="*", destinationPortRange="*")]
        plan = build_plan(**data)
        updates = [o for o in plan["operations"] if o.get("mode") == "update"]
        self.assertEqual({o["rule"]["name"] for o in updates}, {"Deny-Visitas-Interno", "Deny-Visitas-Ventas"})
        self.assertTrue(all(o["rule"]["access"] == "Deny" for o in updates))

    def test_shared_hardening_preserves_dmz_egress_and_has_no_reset_or_public_ssh(self):
        script = make_script("web")
        self.assertIn("test -s /home/azureuser/.ssh/authorized_keys", script)
        self.assertIn("ufw deny out to 10.0.0.0/8", script)
        self.assertIn("AllowTcpForwarding no", script)
        self.assertNotIn("ufw --force reset", script)
        self.assertNotIn("ufw allow 443", script)
        self.assertNotIn("ufw allow 22/tcp", script)

    def test_timeouts_never_prove_isolation_without_healthy_control_and_effective_deny(self):
        self.assertEqual(classify("Deny", "TIMEOUT", None, True), "INCONCLUSIVE")
        self.assertEqual(classify("Deny", "TIMEOUT", "OPEN", False), "INCONCLUSIVE")
        self.assertEqual(classify("Deny", "ERROR", "OPEN", True), "INCONCLUSIVE")
        self.assertEqual(classify("Deny", "REFUSED", "OPEN", True), "FAIL")
        self.assertEqual(classify("Deny", "TIMEOUT", "OPEN", True), "PASS")


if __name__ == "__main__":
    unittest.main()
