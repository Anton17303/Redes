#!/usr/bin/env python3
"""Start/deallocate one explicitly named project VM and verify its real power state."""
import argparse
import json
import os
from pathlib import Path
import time

from azure_snapshot import request
from project_ops import execute
from validate_azure import need

VMS = ["VM-Ventas-1", "VM-Ventas-2", "VM-Web-Publica", "VM-TI-1", "VM-Visitas-1"]


def state(vm):
    return next((s["code"] for s in vm.get("instanceView", {}).get("statuses", [])
                 if s.get("code", "").startswith("PowerState/")), None)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vm", choices=VMS, required=True)
    p.add_argument("--action", choices=["start", "deallocate"], required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    before = request("vm", "get-instance-view", "-g", "RG-CafeNube", "-n", args.vm)
    (args.output / "power-before.json").write_text(json.dumps(before, indent=2) + "\n", "utf-8")
    if args.vm in {"VM-TI-1", "VM-Visitas-1", "VM-Web-Publica"}:
        need((before.get("tags") or {}).get("gestion") == "cafenube-v1", "VM is not a managed project resource")
    print("Plan: " + args.action + " " + args.vm + "; current=" + str(state(before)), flush=True)
    if not args.apply:
        return 0
    if args.action == "start":
        policy = request("rest", "--method", "get", "--uri", "/subscriptions/" + os.environ["CAFENUBE_SUBSCRIPTION_ID"],
                         "--url-parameters", "api-version=2022-12-01")
        need(policy.get("subscriptionPolicies", {}).get("spendingLimit") == "On", "Spending protection not confirmed On")
    execute(args.output, "power-operation", "vm", args.action, "-g", "RG-CafeNube", "-n", args.vm)
    expected = "PowerState/running" if args.action == "start" else "PowerState/deallocated"
    for attempt in range(10):
        after = request("vm", "get-instance-view", "-g", "RG-CafeNube", "-n", args.vm)
        (args.output / "power-after.json").write_text(json.dumps(after, indent=2) + "\n", "utf-8")
        if state(after) == expected:
            print("CONFIRMED: " + args.vm + " -> " + expected, flush=True)
            return 0
        time.sleep(4)
    raise RuntimeError("Expected power state was not observed")


if __name__ == "__main__":
    raise SystemExit(main())
