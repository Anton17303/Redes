#!/usr/bin/env python3
"""Plan/apply hardening to one named running VM; never starts VMs or creates NAT."""
import argparse
import json
from pathlib import Path

from azure_snapshot import request
from validate_azure import RG, need

ROOT = Path(__file__).resolve().parents[1]
ROLES = {"VM-DNS": "dns", "VM-Intranet": "intranet", "VM-Ventas-1": "cliente",
         "VM-Ventas-2": "cliente", "VM-TI-1": "cliente", "VM-Visitas-1": "visitas", "VM-Web-Publica": "web"}


def make_script(role, update=False):
    ssh = (ROOT / "config/ssh_hardening.conf").read_text("utf-8")
    hardening = (ROOT / "config/hardening_vm.sh").read_text("utf-8")
    return "set -eu\ntest -s /home/azureuser/.ssh/authorized_keys\nmkdir -p /etc/ssh/sshd_config.d\n" + (
        "cat > /etc/ssh/sshd_config.d/00-cafenube.conf <<'CAFENUBE_SSH'\n" + ssh +
        "CAFENUBE_SSH\nbash -s -- " + role + " " + str(int(update)) + " <<'CAFENUBE_SCRIPT'\n" + hardening + "\nCAFENUBE_SCRIPT\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vm", choices=ROLES, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--update-packages", action="store_true")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        vm = request("vm", "get-instance-view", "-g", RG, "-n", args.vm)
        (args.output / "vm-hardening-before.json").write_text(json.dumps(vm, indent=2) + "\n", encoding="utf-8")
        need(vm.get("osProfile", {}).get("adminUsername") == "azureuser", "Usuario administrativo distinto: revisar antes de cambiar SSH")
        need(any(s.get("code") == "PowerState/running" for s in vm.get("instanceView", {}).get("statuses", [])), "VM apagada; no se inicia automáticamente")
        print(f"VM: {args.vm}; rol: {ROLES[args.vm]}; actualizar paquetes: {args.update_packages}; aplicar: {args.apply}")
        if args.apply:
            data = request("vm", "run-command", "invoke", "-g", RG, "-n", args.vm,
                           "--command-id", "RunShellScript", "--scripts", make_script(ROLES[args.vm], args.update_packages))
            (args.output / "hardening-result.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            need(any("CAFENUBE_HARDENING_OK" in item.get("message", "").splitlines() for item in data.get("value", [])), "Sin marcador final del guest; hardening no confirmado")
            print("Hardening ejecutado; contrastar reglas efectivas y matriz de conectividad.")
        return 0
    except (ValueError, RuntimeError, KeyError, OSError) as error:
        print(f"DETENIDO: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
