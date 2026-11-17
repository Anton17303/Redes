#!/usr/bin/env python3
"""Project TCP matrix with healthy controls and actual Azure NSG flow decisions."""
import argparse
import ipaddress
import json
from pathlib import Path

from azure_snapshot import request
from verify_deployment import Evidence, run_remote, running
from security_policy import NETWORKS
from validate_azure import same

ROOT = Path(__file__).resolve().parents[1]
SEGMENTS = {"VM-Visitas-1": "Visitas", "VM-Ventas-1": "Ventas", "VM-TI-1": "TI",
            "VM-DNS": "DataCenter", "VM-Intranet": "DataCenter", "VM-Web-Publica": "DMZ"}
CASES = [
    ("VM-Ventas-1", "VM-DNS", 53, "Allow"), ("VM-Ventas-1", "VM-Intranet", 80, "Allow"),
    ("VM-Ventas-1", "VM-DNS", 22, "Deny"), ("VM-Ventas-1", "VM-TI-1", 22, "Deny"),
    ("VM-Visitas-1", "VM-DNS", 53, "Deny"), ("VM-Visitas-1", "VM-Intranet", 80, "Deny"),
    ("VM-Visitas-1", "VM-Ventas-1", 22, "Deny"), ("VM-Visitas-1", "VM-TI-1", 22, "Deny"),
    ("VM-Visitas-1", "VM-Web-Publica", 80, "Deny"), ("VM-DNS", "VM-Intranet", 80, "Allow"),
    ("VM-DNS", "VM-TI-1", 22, "Deny"), ("VM-Web-Publica", "VM-DNS", 53, "Deny"),
    ("VM-Web-Publica", "VM-Intranet", 80, "Deny"), ("VM-Web-Publica", "VM-Ventas-1", 22, "Deny"),
    ("VM-Web-Publica", "VM-TI-1", 22, "Deny"), ("VM-Web-Publica", "VM-Visitas-1", 22, "Deny"),
]


def classify(expected, observed, control, denied):
    if expected == "Allow":
        return "PASS" if observed == "OPEN" else "FAIL" if observed else "INCONCLUSIVE"
    if observed in {"OPEN", "REFUSED"}:
        return "FAIL"
    return "PASS" if observed == "TIMEOUT" and control == "OPEN" and denied else "INCONCLUSIVE"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    evidence = Evidence(args.output)
    vms = evidence.azure("matrix-vms", "vm", "list", "-g", "RG-CafeNube")
    nics = evidence.azure("matrix-nics", "network", "nic", "list", "-g", "RG-CafeNube")
    if vms is None or nics is None:
        return evidence.finish()
    endpoints = {}
    for name, segment in SEGMENTS.items():
        vm = next((v for v in vms if v.get("name") == name), None)
        if not vm or not running(evidence, name, "state-" + name):
            evidence.result("available-" + name, "PENDING", "VM ausente/apagada; no se inicia para las pruebas")
            continue
        ids = [n.get("id") for n in vm.get("networkProfile", {}).get("networkInterfaces", [])]
        candidates = [(nic["name"], c.get("privateIPAddress")) for nic in nics if any(same(nic.get("id"), i) for i in ids)
                      for c in nic.get("ipConfigurations", []) if c.get("privateIPAddress")]
        if len(candidates) == 1 and ipaddress.ip_address(candidates[0][1]) in ipaddress.ip_network(NETWORKS[segment]):
            endpoints[name] = candidates[0]
        else:
            evidence.result("address-" + name, "FAIL", "NIC/IP fuera del segmento esperado o configuración ambigua")
    targets = sorted({(endpoints[d][1], port) for _, d, port, _ in CASES if d in endpoints})
    script = "TARGETS=" + json.dumps(targets) + "\n" + (ROOT / "config/probe_matrix.py").read_text("utf-8")
    probes = {name: run_remote(evidence, name, "matrix-" + name, script, "CAFENUBE_MATRIX_JSON=") or {} for name in endpoints}
    watchers = evidence.azure("matrix-watchers", "network", "watcher", "list") or []
    can_flow = any(w.get("location") == "northcentralus" for w in watchers)
    for index, (source, dest, port, expected) in enumerate(CASES):
        label = f"{source}-to-{dest}-{port}"
        if source not in endpoints or dest not in endpoints:
            evidence.result(label, "PENDING", "Falta VM activa o dirección comprobada")
            continue
        key = f"{endpoints[dest][1]}:{port}"
        observed = probes.get(source, {}).get(key)
        # Testing a VM's own address from TI still verifies its listener for TI-target denials.
        control = probes.get("VM-TI-1", {}).get(key)
        denied = False
        if expected == "Deny" and can_flow:
            for direction, vm, local, remote in (
                ("Outbound", source, endpoints[source][1] + ":50000", key),
                ("Inbound", dest, key, endpoints[source][1] + ":50000")):
                flow = evidence.azure(f"matrix-flow-{index}-{direction}", "network", "watcher", "test-ip-flow",
                    "-g", "RG-CafeNube", "--vm", vm, "--nic", endpoints[vm][0], "--direction", direction,
                    "--protocol", "TCP", "--local", local, "--remote", remote)
                denied = denied or bool(flow and flow.get("access") == "Deny" and flow.get("ruleName"))
        evidence.result(label, classify(expected, observed, control, denied),
            f"esperado={expected}; observado={observed}; control_TI={control}; Deny_efectivo={denied}")
    evidence.result("protocol-scope", "PENDING", "Esta matriz es TCP; completar DNS UDP/funcional y controles externos con 02_pruebas.sh y pruebas de servicios internos")
    return evidence.finish()


if __name__ == "__main__":
    raise SystemExit(main())
