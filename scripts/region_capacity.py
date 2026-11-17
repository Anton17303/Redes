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
            skus = resource_skus(subscription, "Standard_B2ats_v2", region)
            item = {"region": region, "usage": [u for u in usage if u.get("name", {}).get("value", "").lower()
                                                   in {"cores", "standardbasv2family"}],
                    "skus": skus}
            (args.output / (region + ".json")).write_text(json.dumps(item, indent=2) + "\n", "utf-8")
            compact = {"region": region, "quota": item["usage"],
                       "restrictions": [s.get("restrictions", []) for s in skus]}
            summary.append(compact)
            print(json.dumps(compact), flush=True)
        except (RuntimeError, ValueError) as error:
            print(region + ": " + str(error), flush=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", "utf-8")


if __name__ == "__main__":
    main()
