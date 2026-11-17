#!/usr/bin/env python3
"""Fake CLI for offline deployment control-flow tests; does not contact Azure."""
import json
import os
import sys
from pathlib import Path

from test_safety import fixture

path = Path(os.environ["CAFENUBE_TEST_STATE"])
state = json.loads(path.read_text("utf-8"))
args = sys.argv[1:]
state["calls"].append(args)


def option(flag):
    return args[args.index(flag) + 1]


data = state["data"]
keys = {
    ("account", "show"): "account", ("group", "show"): "group",
    ("network", "vnet", "show"): "vnet", ("network", "nsg", "show"): "nsg",
    ("network", "nic", "list"): "nics", ("network", "public-ip", "list"): "pips",
    ("vm", "list"): "vms", ("disk", "list"): "disks",
    ("network", "vnet", "check-ip-address"): "ip_available", ("network", "check-dns"): "dns_available",
    ("vm", "list-skus"): "skus", ("vm", "list-usage"): "usage",
}
result = None
for prefix, key in keys.items():
    if args[:len(prefix)] == list(prefix):
        result = data[key]
        break
if args[:3] == ["network", "public-ip", "create"]:
    result = fixture(True)["pips"][0]
    result.pop("ipConfiguration", None)
    result["dnsSettings"]["domainNameLabel"] = os.environ["CAFENUBE_DNS_LABEL"]
    data["pips"] = [result]
elif args[:3] == ["network", "nic", "create"]:
    result = fixture(True)["nics"][0]
    result.pop("virtualMachine", None)
    data["nics"] = [result]
    data["pips"][0]["ipConfiguration"] = {"id": result["id"] + "/ipConfigurations/ipconfig1"}
    data["ip_available"] = {"available": False}
elif args[:2] == ["vm", "create"]:
    data["vms"] = fixture(True)["vms"]
    data["nics"][0]["virtualMachine"] = {"id": data["vms"][0]["id"]}
    result = {}
elif args[:3] == ["network", "public-ip", "show"]:
    result = {"fqdn": "fixture.invalid", "ip": "192.0.2.1"}
elif args[:2] == ["vm", "show"]:
    result = data["vms"][0]
elif args[:2] == ["vm", "deallocate"]:
    result = {}
elif args[:2] == ["vm", "get-instance-view"]:
    result = {"instanceView": {"statuses": [{"code": "PowerState/deallocated"}]}}
elif args[:1] == ["rest"]:
    if option("--method") != "get":
        raise SystemExit("Fake CLI allows GET only")
    if "/providers/Microsoft.Compute/skus" in option("--uri"):
        result = {"value": data["skus"]}
    else:
        result = {"subscriptionId": data["request"]["subscription"], "state": "Enabled",
                  "subscriptionPolicies": {"spendingLimit": state.get("spending_limit", "On")}}
if state.get("fail_read") and args[:3] == ["network", "nic", "list"]:
    path.write_text(json.dumps(state), encoding="utf-8")
    print("Synthetic RBAC failure", file=sys.stderr)
    sys.exit(3)
path.write_text(json.dumps(state), encoding="utf-8")
if result is None:
    print(f"Unsupported fake CLI call: {args}", file=sys.stderr)
    sys.exit(2)
print(json.dumps(result))
