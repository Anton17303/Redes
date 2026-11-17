#!/usr/bin/env python3
"""Collect Azure inventory using only read operations and explicit subscription."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

RG = "RG-CafeNube"
LOC = "northcentralus"


def request(*args, timeout=600):
    command = [shutil.which("az") or "az", *args, "--subscription",
               os.environ["CAFENUBE_SUBSCRIPTION_ID"], "--only-show-errors", "-o", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Azure CLI excedió {timeout}s en {args[:3]}; revisar estado antes de reintentar") from error
    if result.returncode:
        raise RuntimeError(f"Azure CLI falló ({' '.join(args)}): {result.stderr.strip()}")
    return json.loads(result.stdout)


def resource_skus(subscription, size):
    # The CLI's legacy list-skus endpoint can stall. Use the documented regional
    # ARM API with pagination; keep restrictions/family/vCPU data for validation.
    uri = f"/subscriptions/{subscription}/providers/Microsoft.Compute/skus?" + urlencode({
        "api-version": "2021-07-01", "$filter": f"location eq '{LOC}'"})
    seen, result = set(), []
    while uri:
        if uri in seen or len(seen) >= 100:
            raise ValueError("Paginación SKU inesperada o cíclica")
        parsed = urlparse(uri)
        if parsed.netloc and (parsed.scheme != "https" or parsed.netloc != "management.azure.com"):
            raise ValueError("Azure devolvió nextLink SKU fuera de ARM")
        seen.add(uri)
        # A query URL with '&' is unsafe through Windows az.cmd. Put parameters
        # in a JSON file, also preserving encoded pagination tokens verbatim.
        endpoint = urlunparse(parsed._replace(query="", fragment=""))
        with tempfile.TemporaryDirectory(prefix="cafenube-sku-") as folder:
            parameters = Path(folder) / "parameters.json"
            parameters.write_text(json.dumps(dict(parse_qsl(parsed.query))), encoding="utf-8")
            page = request("rest", "--method", "get", "--uri", endpoint,
                           "--url-parameters", "@" + str(parameters), timeout=120)
        result.extend(s for s in page["value"] if (size is None or s.get("name") == size)
                      and s.get("resourceType") == "virtualMachines")
        uri = page.get("nextLink")
    return result


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
        "dns_available": ("rest", "--method", "get", "--uri",
                          f"/subscriptions/{subscription}/providers/Microsoft.Network/locations/{LOC}/checkDnsNameAvailability",
                          "--url-parameters", "api-version=2025-05-01", "domainNameLabel=" + label),
        "usage": ("vm", "list-usage", "-l", LOC),
    }
    for name, args in queries.items():
        value = request(*args)
        (output / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        print(f"Inventario de solo lectura: {name}", flush=True)
    (output / "skus.json").write_text(json.dumps(resource_skus(subscription, size), indent=2) + "\n", encoding="utf-8")
    print("Inventario de solo lectura: skus (ARM regional)", flush=True)
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
