#!/usr/bin/env python3
"""Read ACI quotas/capabilities independently of virtual-machine vCPU quotas."""
import argparse
import json
import os
from pathlib import Path

from azure_snapshot import request


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    prefix = "/subscriptions/" + os.environ["CAFENUBE_SUBSCRIPTION_ID"]
    prefix += "/providers/Microsoft.ContainerInstance/locations/northcentralus/"
    for kind in ("usages", "capabilities"):
        data = request("rest", "--method", "get", "--uri", prefix + kind,
                       "--url-parameters", "api-version=2026-07-01")
        (args.output / (kind + ".json")).write_text(json.dumps(data, indent=2) + "\n", "utf-8")
        print(kind + ": " + json.dumps(data), flush=True)


if __name__ == "__main__":
    main()
