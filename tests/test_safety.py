"""Offline fixtures are synthetic test data, never Azure evidence."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from render_cloud_init import ROOT, SOURCES, render
from validate_azure import OWNER, security, validate
from verify_deployment import Evidence, run_remote

SUBSCRIPTION = "00000000-0000-0000-0000-000000000001"
BASE = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/RG-CafeNube/providers/"
SUBNET_ID = BASE + "Microsoft.Network/virtualNetworks/VNet-CafeNube/subnets/Subnet-DMZ"
NSG_ID = BASE + "Microsoft.Network/networkSecurityGroups/NSG-DMZ"


def rule(name, priority, direction, access, source, destination, protocol="*", port="*"):
    return {"name": name, "priority": priority, "direction": direction, "access": access,
            "sourceAddressPrefix": source, "destinationAddressPrefix": destination,
            "sourcePortRange": "*", "destinationPortRange": port, "protocol": protocol}


def fixture(existing=False):
    nsg = {"id": NSG_ID, "location": "northcentralus", "securityRules": [
        rule("Allow-Web-Internet", 100, "Inbound", "Allow", "Internet", "10.0.0.148", "Tcp", "80"),
        rule("Allow-SSH-TI", 110, "Inbound", "Allow", "10.0.0.96/27", "10.0.0.148", "Tcp", "22"),
        rule("Deny-All-In", 4000, "Inbound", "Deny", "*", "*"),
        rule("Deny-DMZ-VNet", 100, "Outbound", "Deny", "*", "VirtualNetwork"),
    ], "defaultSecurityRules": [
        rule("AllowVnetInBound", 65000, "Inbound", "Allow", "VirtualNetwork", "VirtualNetwork"),
        rule("AllowAzureLoadBalancerInBound", 65001, "Inbound", "Allow", "AzureLoadBalancer", "*"),
        rule("DenyAllInBound", 65500, "Inbound", "Deny", "*", "*"),
        rule("AllowVnetOutBound", 65000, "Outbound", "Allow", "VirtualNetwork", "VirtualNetwork"),
        rule("AllowInternetOutBound", 65001, "Outbound", "Allow", "*", "Internet"),
        rule("DenyAllOutBound", 65500, "Outbound", "Deny", "*", "*"),
    ]}
    data = {"request": {"subscription": SUBSCRIPTION, "dns_label": "cafenube-test", "vm_size": "Standard_B2ats_v2"},
            "account": {"id": SUBSCRIPTION, "state": "Enabled"}, "group": {"name": "RG-CafeNube"},
            "vnet": {"location": "northcentralus", "addressSpace": {"addressPrefixes": ["10.0.0.0/16"]},
                     "subnets": [{"id": SUBNET_ID, "name": "Subnet-DMZ", "addressPrefix": "10.0.0.144/28", "networkSecurityGroup": {"id": NSG_ID}}]},
            "nsg": nsg, "pips": [], "nics": [], "vms": [], "disks": [],
            "ip_available": {"available": True}, "dns_available": {"available": True},
            "skus": [{"name": "Standard_B2ats_v2", "resourceType": "virtualMachines", "restrictions": [],
                      "family": "standardBasv2Family", "capabilities": [{"name": "vCPUs", "value": "2"}]}],
            "usage": [{"name": {"value": name}, "limit": 10, "currentValue": 0} for name in ("cores", "standardBasv2Family")]}
    if existing:
        pip = {"id": BASE + "Microsoft.Network/publicIPAddresses/PIP-Web-Publica", "name": "PIP-Web-Publica",
               "location": "northcentralus", "tags": OWNER.copy(), "sku": {"name": "Standard"},
               "publicIPAllocationMethod": "Static", "publicIPAddressVersion": "IPv4", "dnsSettings": {"domainNameLabel": "cafenube-test"}}
        nic = {"id": BASE + "Microsoft.Network/networkInterfaces/NIC-Web-Publica", "name": "NIC-Web-Publica",
               "location": "northcentralus", "tags": OWNER.copy(), "dnsSettings": {"dnsServers": ["168.63.129.16"]},
               "ipConfigurations": [{"name": "ipconfig1", "privateIPAddress": "10.0.0.148", "privateIPAllocationMethod": "Static",
                                     "subnet": {"id": SUBNET_ID}, "publicIPAddress": {"id": pip["id"]}}]}
        vm = {"id": BASE + "Microsoft.Compute/virtualMachines/VM-Web-Publica", "name": "VM-Web-Publica", "location": "northcentralus",
              "tags": OWNER.copy(), "hardwareProfile": {"vmSize": "Standard_B2ats_v2"},
              "networkProfile": {"networkInterfaces": [{"id": nic["id"], "primary": True}]},
              "osProfile": {"adminUsername": "azureuser", "linuxConfiguration": {"disablePasswordAuthentication": True}}}
        nic["virtualMachine"] = {"id": vm["id"]}
        pip["ipConfiguration"] = {"id": nic["id"] + "/ipConfigurations/ipconfig1"}
        data.update(pips=[pip], nics=[nic], vms=[vm], ip_available={"available": False}, dns_available={"available": False})
    return data


class SafetyTests(unittest.TestCase):
    def test_fresh_plan_is_read_only_and_requires_approval(self):
        plan = validate(fixture())
        self.assertEqual(set(plan["resources"].values()), {"create"})
        self.assertIn("REQUIRED", plan["cost_approval"])

    def test_valid_rerun_reuses_all_resources_and_occupied_own_ip(self):
        self.assertEqual(set(validate(fixture(True))["resources"].values()), {"reuse"})

    def test_partial_rerun_reuses_own_pip_and_nic(self):
        data = fixture(True)
        data["vms"] = []
        data["nics"][0].pop("virtualMachine")
        self.assertEqual(validate(data)["resources"], {"pip": "reuse", "nic": "reuse", "vm": "create"})

    def test_rejects_unsafe_security_profiles(self):
        mutations = {
            "public-ssh": lambda d: d["nsg"]["securityRules"][1].update(sourceAddressPrefix="Internet"),
            "https-without-tls": lambda d: d["nsg"]["securityRules"][0].update(destinationPortRange="443"),
            "udp-web": lambda d: d["nsg"]["securityRules"][0].update(protocol="Udp"),
            "no-explicit-inbound-deny": lambda d: d["nsg"]["securityRules"].pop(2),
            "no-outbound-isolation": lambda d: d["nsg"]["securityRules"].pop(3),
            "web-shadowed": lambda d: d["nsg"]["securityRules"][2].update(priority=100),
            "no-default-rules": lambda d: d["nsg"].update(defaultSecurityRules=[]),
            "asgs": lambda d: d["nsg"]["securityRules"][0].update(sourceApplicationSecurityGroups=[{"id": "unknown"}]),
            "bypass-vnet": lambda d: d["nsg"]["securityRules"].append(rule("bypass", 101, "Outbound", "Allow", "*", "10.0.0.132", "Tcp", "53")),
            "outbound-closed-apt": lambda d: d["nsg"]["securityRules"].append(rule("close-egress", 4000, "Outbound", "Deny", "*", "*")),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                data = fixture()
                mutate(data)
                with self.assertRaises(ValueError):
                    validate(data)

    def test_plural_port_443_is_not_missed(self):
        data = fixture()
        data["nsg"]["securityRules"][0]["destinationPortRanges"] = ["80", "443"]
        with self.assertRaises(ValueError):
            validate(data)

    def test_plural_safe_rules_are_supported(self):
        data = fixture()
        for item in data["nsg"]["securityRules"]:
            for field in ("sourceAddressPrefix", "destinationAddressPrefix"):
                item[field + "es"] = [item.pop(field)]
            for field in ("sourcePortRange", "destinationPortRange"):
                item[field + "s"] = [item.pop(field)]
        validate(data)

    def test_rejects_network_and_resource_conflicts(self):
        mutations = {
            "wrong-subscription": lambda d: d["account"].update(id="other"),
            "missing-dmz": lambda d: d["vnet"].update(subnets=[]),
            "wrong-cidr": lambda d: d["vnet"]["subnets"][0].update(addressPrefix="10.0.0.128/28"),
            "wrong-nsg": lambda d: d["vnet"]["subnets"][0].update(networkSecurityGroup={"id": "other"}),
            "custom-routes": lambda d: d["vnet"]["subnets"][0].update(routeTable={"id": "other"}),
            "wrong-owner": lambda d: d["pips"][0]["tags"].update(componente="otro"),
            "wrong-label": lambda d: d["pips"][0]["dnsSettings"].update(domainNameLabel="different"),
            "wrong-subnet": lambda d: d["nics"][0]["ipConfigurations"][0].update(subnet={"id": "other"}),
            "extra-nic-nsg": lambda d: d["nics"][0].update(networkSecurityGroup={"id": "other"}),
            "internal-dns": lambda d: d["nics"][0]["dnsSettings"].update(dnsServers=["10.0.0.132"]),
            "pip-used-elsewhere": lambda d: d["pips"][0].update(ipConfiguration={"id": "other"}),
            "password-auth": lambda d: d["vms"][0]["osProfile"]["linuxConfiguration"].update(disablePasswordAuthentication=False),
            "failed-resource": lambda d: d["nics"][0].update(provisioningState="Failed"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                data = fixture(True)
                mutate(data)
                with self.assertRaises(ValueError):
                    validate(data)

    def test_collision_in_other_resource_group_same_subnet(self):
        data = fixture()
        data["nics"] = [{"id": "/subscriptions/x/resourceGroups/other/providers/Microsoft.Network/networkInterfaces/other", "ipConfigurations": [
            {"privateIPAddress": "10.0.0.148", "subnet": {"id": SUBNET_ID}}]}]
        with self.assertRaisesRegex(ValueError, "ocupada"):
            validate(data)

    def test_matching_private_ip_in_other_vnet_is_not_a_collision(self):
        data = fixture()
        data["nics"] = [{"id": "other", "ipConfigurations": [{"privateIPAddress": "10.0.0.148", "subnet": {"id": "another-vnet"}}]}]
        validate(data)

    def test_low_quota_and_orphan_disk_stop_creation(self):
        for key in ("quota", "disk"):
            with self.subTest(key=key):
                data = fixture()
                if key == "quota":
                    data["usage"][0]["limit"] = 1
                else:
                    data["disks"] = [{"name": "Disk-Web-Publica-OS"}]
                with self.assertRaises(ValueError):
                    validate(data)

    def test_cloud_init_has_exact_current_sources_and_no_tls(self):
        payload = render()
        config = json.loads(payload.split("\n", 1)[1])
        files = {item["path"]: item["content"] for item in config["write_files"]}
        for source, (target, _) in SOURCES.items():
            self.assertEqual(files[target], (ROOT / source).read_text("utf-8"))
        self.assertLess(len(payload.encode("utf-8")), 65536)
        self.assertNotIn("listen 443", files["/etc/nginx/sites-available/cafenube"])
        self.assertFalse(config["ssh_pwauth"])
        self.assertEqual(render(), payload)

    def test_run_command_success_without_guest_marker_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Evidence(Path(tmp))
            evidence.azure = lambda *args: {"value": [{"code": "ProvisioningState/succeeded", "message": "script exit 1"}]}
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(run_remote(evidence, "test", "test", "", "CAFENUBE_GUEST_JSON="))
            self.assertEqual(evidence.finish(), 2)

    def test_failed_evidence_returns_nonzero_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Evidence(Path(tmp))
            with contextlib.redirect_stdout(io.StringIO()):
                evidence.result("synthetic-failure", "FAIL", "fixture only")
            self.assertEqual(evidence.finish(), 1)
            self.assertTrue((Path(tmp) / "results.json").is_file())


if __name__ == "__main__":
    unittest.main()
