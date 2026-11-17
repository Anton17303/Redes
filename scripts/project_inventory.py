#!/usr/bin/env python3
"""Read project capacity and resource state; never starts or modifies resources."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from azure_snapshot import request, resource_skus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    subscription = os.environ["CAFENUBE_SUBSCRIPTION_ID"]
    queries = {
        "subscription": ("rest", "--method", "get", "--uri", "/subscriptions/" + subscription,
                         "--url-parameters", "api-version=2022-12-01"),
        "vms": ("vm", "list", "-g", "RG-CafeNube", "--show-details"),
        "nics": ("network", "nic", "list", "-g", "RG-CafeNube"),
        "vnet": ("network", "vnet", "show", "-g", "RG-CafeNube", "-n", "VNet-CafeNube"),
        "nsgs": ("network", "nsg", "list", "-g", "RG-CafeNube"),
        "pips": ("network", "public-ip", "list", "-g", "RG-CafeNube"),
        "usage": ("vm", "list-usage", "-l", "northcentralus"),
    }
    data = {}
    for name, command in queries.items():
        data[name] = request(*command)
        (args.output / (name + ".json")).write_text(json.dumps(data[name], indent=2) + "\n", "utf-8")
        print("Inventario de solo lectura: " + name, flush=True)
    skus = resource_skus(subscription, None)
    candidates = []
    for sku in skus:
        caps = {c["name"]: c["value"] for c in sku.get("capabilities", [])}
        if caps.get("vCPUs") == "1" or sku.get("name") == "Standard_B2ats_v2":
            candidates.append(sku)
    (args.output / "small-skus.json").write_text(json.dumps(candidates, indent=2) + "\n", "utf-8")
    summary = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "spending_limit": data["subscription"].get("subscriptionPolicies", {}).get("spendingLimit"),
        "vms": [{"name": v["name"], "size": v["hardwareProfile"]["vmSize"],
                 "state": v.get("powerState"), "security": v.get("securityProfile")}
                for v in data["vms"]],
        "quota": [u for u in data["usage"] if u.get("name", {}).get("value", "").lower()
                  in {"cores", "standardbsfamily", "standardbasv2family"}],
        "small_skus": [{"name": s["name"], "family": s.get("family"), "restrictions": s.get("restrictions"),
                        "capabilities": {c["name"]: c["value"] for c in s.get("capabilities", [])
                                         if c["name"] in {"vCPUs", "MemoryGB", "HyperVGenerations", "PremiumIO",
                                                          "MaxResourceVolumeMB", "TrustedLaunchDisabled"}}}
                       for s in candidates],
    }
    (args.output / "capacity-summary.json").write_text(json.dumps(summary, indent=2) + "\n", "utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
