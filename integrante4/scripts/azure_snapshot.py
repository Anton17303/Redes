#!/usr/bin/env python3
"""Collect Azure inventory using only read operations and explicit subscription."""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RG = "RG-CafeNube"
LOC = "northcentralus"


def request(*args):
    command = [shutil.which("az") or "az", *args, "--subscription",
               os.environ["CAFENUBE_SUBSCRIPTION_ID"], "--only-show-errors", "-o", "json"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Azure CLI falló ({' '.join(args)}): {result.stderr.strip()}")
    return json.loads(result.stdout)


def collect(output):
    subscription = os.environ.get("CAFENUBE_SUBSCRIPTION_ID", "")
    label = os.environ.get("CAFENUBE_DNS_LABEL", "")
    size = os.environ.get("CAFENUBE_VM_SIZE", "")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", subscription):
        raise ValueError("Indicar el ID de suscripción, no su nombre ni credenciales")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,61}[a-z0-9]", label):
        raise ValueError("Etiqueta DNS inválida: 3-63 caracteres minúsculos, números y guiones")
    output.mkdir(parents=True, exist_ok=True)
    queries = {
        "account": ("account", "show", "--query", "{id:id,name:name,state:state}"),
        "group": ("group", "show", "-n", RG),
        "vnet": ("network", "vnet", "show", "-g", RG, "-n", "VNet-CafeNube"),
        "nsg": ("network", "nsg", "show", "-g", RG, "-n", "NSG-DMZ"),
        # Toda la suscripción: también detecta NICs de otros grupos en la misma VNet.
        "nics": ("network", "nic", "list"),
        "pips": ("network", "public-ip", "list"),
        "vms": ("vm", "list"),
        "disks": ("disk", "list", "-g", RG),
        "ip_available": ("network", "vnet", "check-ip-address", "-g", RG,
                         "-n", "VNet-CafeNube", "--ip-address", "10.0.0.148"),
        "dns_available": ("network", "check-dns", "--name", label, "-l", LOC),
        "skus": ("vm", "list-skus", "-l", LOC, "--size", size, "--all"),
        "usage": ("vm", "list-usage", "-l", LOC),
    }
    for name, args in queries.items():
        value = request(*args)
        (output / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        print(f"Inventario de solo lectura: {name}", flush=True)
    (output / "request.json").write_text(json.dumps({
        "subscription": subscription, "dns_label": label, "vm_size": size,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        collect(Path(sys.argv[1]))
    except (ValueError, RuntimeError, KeyError) as error:
        print(f"DETENIDO: {error}", file=sys.stderr)
        sys.exit(1)
