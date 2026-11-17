#!/usr/bin/env python3
"""Inspect allowed secondary regions without changing quota or billing."""
import argparse
import json
import os
from pathlib import Path

from azure_snapshot import request, resource_skus


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--all-sizes", action="store_true")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    subscription = os.environ["CAFENUBE_SUBSCRIPTION_ID"]
    policies = request("rest", "--method", "get", "--uri", "/subscriptions/" + subscription +
                       "/providers/Microsoft.Authorization/policyAssignments", "--url-parameters", "api-version=2022-06-01")
    (args.output / "policies.json").write_text(json.dumps(policies, indent=2) + "\n", "utf-8")
    allowed = set()
    for assignment in policies.get("value", []):
        for name, parameter in assignment.get("properties", {}).get("parameters", {}).items():
            value = parameter.get("value")
            if any(key in name.lower() for key in ("location", "region")) and isinstance(value, list):
                allowed.update(v.lower().replace(" ", "") for v in value if isinstance(v, str))
    choices = [r for r in ("canadacentral", "eastus2", "westus2", "centralus", "southcentralus", "westus3",
                           "francecentral", "spaincentral", "belgiumcentral")
               if not allowed or r in allowed]
    print("Policy location parameters: " + json.dumps(sorted(allowed)), flush=True)
    summary = []
    for region in choices:
        try:
            usage = request("vm", "list-usage", "-l", region)
            skus = resource_skus(subscription, None if args.all_sizes else "Standard_B2ats_v2", region)
            quotas = {u["name"]["value"].lower(): int(u["limit"]) - int(u["currentValue"]) for u in usage}
            eligible = []
            if args.all_sizes:
                selected = []
                for sku in skus:
                    caps = {c["name"]: c["value"] for c in sku.get("capabilities", [])}
                    cpu = int(caps.get("vCPUs", "0"))
                    memory = float(caps.get("MemoryGB", "0"))
                    if not (1 <= cpu <= 2 and 0 < memory <= 8 and "V2" in caps.get("HyperVGenerations", "")
                            and caps.get("CpuArchitecture", "x64").lower() == "x64"):
                        continue
                    selected.append(sku)
                    # No availability zone is requested; zone-only restrictions do not prohibit this deployment.
                    if any(r.get("type") != "Zone" for r in sku.get("restrictions", [])):
                        continue
                    free = min(quotas.get("cores", 0), quotas.get(sku.get("family", "").lower(), 0))
                    if free >= 2 * cpu:
                        eligible.append({"name": sku["name"], "family": sku.get("family"),
                                         "vcpus": cpu, "memory_gb": memory, "quota_free": free})
                skus = selected
            item = {"region": region, "usage": [u for u in usage if u.get("name", {}).get("value", "").lower()
                                                   in ({"cores"} | {s.get("family", "").lower() for s in skus})],
                    "skus": skus}
            (args.output / (region + ".json")).write_text(json.dumps(item, indent=2) + "\n", "utf-8")
            compact = {"region": region, "quota": item["usage"],
                       "restrictions": [s.get("restrictions", []) for s in skus]}
            summary.append(compact)
            if args.all_sizes:
                summary[-1] = {"region": region, "eligible": eligible}
            print(json.dumps(summary[-1]), flush=True)
            if eligible:
                break
        except (RuntimeError, ValueError) as error:
            print(region + ": " + str(error), flush=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", "utf-8")


if __name__ == "__main__":
    main()
