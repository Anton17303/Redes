"""Synthetic safety checks for deliberate reuse of existing project resources."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import full_project_network as project

SUB = "11111111-1111-1111-1111-111111111111"
BASE = f"/subscriptions/{SUB}/resourceGroups/RG-CafeNube/providers/Microsoft.Network/"


def fixture():
    subnets = [{"name": "Subnet-" + n, "id": BASE + "virtualNetworks/VNet-CafeNube/subnets/Subnet-" + n}
               for n in ("Ventas", "DataCenter")]
    nic = {"name": "sales-two", "id": BASE + "networkInterfaces/sales-two", "ipConfigurations": [
        {"name": "primary", "primary": True, "privateIPAddress": "10.0.0.69", "subnet": subnets[0]}]}
    sales = {"name": "sales-one", "id": BASE + "networkInterfaces/sales-one", "ipConfigurations": [
        {"name": "primary", "primary": True, "privateIPAddress": "10.0.0.68", "subnet": subnets[0]}]}
    vm = {"name": "VM-Ventas-2", "osProfile": {"adminUsername": "azureuser"},
          "networkProfile": {"networkInterfaces": [{"id": nic["id"]}]},
          "instanceView": {"statuses": [{"code": "PowerState/deallocated"}]}}
    return {"account": {}, "vnet": {"subnets": subnets}, "nsgs": [], "nics": [nic, sales]}, vm


class FullProjectSafetyTests(unittest.TestCase):
    def run_project(self, flags=(), *, spending="On", foreign_nat=False, collision=False):
        data, vm = fixture()
        if collision:
            other = copy.deepcopy(data["nics"][0]); other["id"] += "-other"
            other["ipConfigurations"][0]["privateIPAddress"] = "10.0.0.132"
            data["nics"].append(other)
        metadata = {"subscriptionId": SUB, "state": "Enabled", "subscriptionPolicies": {"spendingLimit": spending}}
        def reply(*args, **kwargs):
            if args[:4] == ("network", "nat", "gateway", "list"):
                return [{"name": project.NAT, "tags": {}}] if foreign_nat else []
            if args[:3] == ("network", "public-ip", "list"):
                return []
            if args[:2] == ("vm", "get-instance-view"):
                return vm
            if args[0] == "rest":
                return metadata
            raise AssertionError("Unexpected API request " + repr(args))
        with tempfile.TemporaryDirectory(prefix="cafenube-synthetic-") as folder:
            review = Path(folder) / "review.json"
            review.write_text(json.dumps({"subscription_id": SUB, "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
                                         "expires_on": "2099-01-01", "available_lower_bound_usd": 20}), "utf-8")
            argv = ["full_project_network.py", "--output", folder, "--credit-review", str(review), *flags]
            with patch.object(project, "collect", return_value=(data, SUB)), \
                 patch.object(project, "build_plan", return_value={"operations": []}), \
                 patch.object(project, "request", side_effect=reply), \
                 patch.object(project, "execute") as mutate, patch.object(sys, "argv", argv):
                try:
                    result = project.main()
                    plan = json.loads((Path(folder) / "network-plan.json").read_text("utf-8"))
                    self.assertEqual(plan["new_virtual_machines"], 0)
                    self.assertTrue(plan["preserve_os_disk_and_data"])
                    return result
                finally:
                    mutate.assert_not_called()

    def test_default_plan_does_not_start_move_or_create_resources(self):
        self.assertEqual(self.run_project(), 0)

    def test_reuse_must_be_explicit_before_any_mutation(self):
        with self.assertRaisesRegex(ValueError, "reuse required"):
            self.run_project(["--apply"])

    def test_disabled_spending_protection_stops_all_mutations(self):
        with self.assertRaisesRegex(ValueError, "protección de gasto"):
            self.run_project(["--apply", "--reuse-sales-vm"], spending="Off")

    def test_foreign_egress_resource_is_never_removed(self):
        with self.assertRaisesRegex(ValueError, "owner"):
            self.run_project(["--apply", "--cleanup-egress"], foreign_nat=True)

    def test_private_ip_collision_stops_before_reuse(self):
        with self.assertRaisesRegex(ValueError, "collision"):
            self.run_project(["--apply", "--reuse-sales-vm"], collision=True)


if __name__ == "__main__":
    unittest.main()
