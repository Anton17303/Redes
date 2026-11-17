#!/usr/bin/env python3
"""Plan/apply approved VM reuse and temporary explicit outbound connectivity."""
import argparse
import json
import os
from pathlib import Path

from azure_snapshot import request
from check_credit_guard import validate_credit
from project_ops import execute
from security_policy import collect, build_plan
from validate_azure import need, same

RG = "RG-CafeNube"
VNET = "VNet-CafeNube"
NAT = "NAT-CafeNube-Pruebas"
PIP = "PIP-CafeNube-Pruebas"
TAGS = {"proyecto": "CafeNube", "componente": "salida-temporal", "gestion": "cafenube-v1"}
SEGMENTS = ("Ventas", "DataCenter")


def own(resource):
    need(all((resource.get("tags") or {}).get(k) == v for k, v in TAGS.items()), "Unexpected egress resource owner")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--cleanup-egress", action="store_true")
    p.add_argument("--reuse-sales-vm", action="store_true", help="Explicitly approve the reviewed change of VM-Ventas-2 role")
    p.add_argument("--credit-review", type=Path)
    p.add_argument("--budget-usd", default="3")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    data, subscription = collect(args.output / "network-before")
    need(not build_plan(**data, subscription=subscription)["operations"], "Project NSGs must be convergent first")
    vnet = data["vnet"]
    subnets = {s["name"]: s for s in vnet["subnets"]}
    nats = request("network", "nat", "gateway", "list", "-g", RG)
    pips = request("network", "public-ip", "list", "-g", RG)
    nat = next((n for n in nats if n.get("name") == NAT), None)
    pip = next((n for n in pips if n.get("name") == PIP), None)
    if nat:
        own(nat)
    if pip:
        own(pip)
    nat_id = f"/subscriptions/{subscription}/resourceGroups/{RG}/providers/Microsoft.Network/natGateways/{NAT}"
    for name in SEGMENTS:
        current = subnets["Subnet-" + name].get("natGateway")
        need(not current or same(current.get("id"), nat_id), "Foreign NAT association in " + name)
    if args.cleanup_egress:
        # This removes only resources created by this workflow; caller stops tests first.
        if not nat and not pip:
            print("No managed temporary egress remains")
            return 0
        need(args.apply, "Cleanup requires --apply")
        for name in SEGMENTS:
            if subnets["Subnet-" + name].get("natGateway"):
                execute(args.output, "detach-nat-" + name, "network", "vnet", "subnet", "update", "-g", RG,
                        "--vnet-name", VNET, "-n", "Subnet-" + name, "--remove", "natGateway")
        if nat:
            execute(args.output, "delete-managed-nat", "network", "nat", "gateway", "delete", "-g", RG, "-n", NAT)
        if pip:
            execute(args.output, "delete-managed-egress-pip", "network", "public-ip", "delete", "-g", RG, "-n", PIP)
        remaining_nat = request("network", "nat", "gateway", "list", "-g", RG)
        remaining_pip = request("network", "public-ip", "list", "-g", RG)
        need(not any(x.get("name") == NAT for x in remaining_nat), "Temporary NAT still exists")
        need(not any(x.get("name") == PIP for x in remaining_pip), "Temporary public IP still exists")
        print("CONFIRMED: temporary NAT and its public IP removed; other resources preserved")
        return 0
    vm = request("vm", "get-instance-view", "-g", RG, "-n", "VM-Ventas-2")
    (args.output / "private-vm-before.json").write_text(json.dumps(vm, indent=2) + "\n", "utf-8")
    need(vm.get("osProfile", {}).get("adminUsername") == "azureuser", "Unexpected administrative account")
    ids = [i["id"] for i in vm.get("networkProfile", {}).get("networkInterfaces", [])]
    need(len(ids) == 1, "Unexpected private server NIC count")
    nic = next(n for n in data["nics"] if same(n["id"], ids[0]))
    primary = next(c for c in nic["ipConfigurations"] if c.get("primary"))
    dc = subnets["Subnet-DataCenter"]
    original = primary.get("privateIPAddress") == "10.0.0.69" and same(primary["subnet"]["id"], subnets["Subnet-Ventas"]["id"])
    moved = primary.get("privateIPAddress") == "10.0.0.132" and same(primary["subnet"]["id"], dc["id"])
    need(original or moved, "Private server is not at its reviewed original or final location")
    for item in data["nics"]:
        for config in item.get("ipConfigurations", []):
            need(config.get("privateIPAddress") not in {"10.0.0.132", "10.0.0.133"} or same(item["id"], nic["id"]), "Private service IP collision")
    plan = {"private_server": vm["name"], "preserve_os_disk_and_data": True,
            "original_nic": nic, "final_subnet": dc["id"], "dns_ip": "10.0.0.132", "intranet_ip": "10.0.0.133",
            "temporary_nat": NAT, "temporary_public_ip": PIP, "egress_subnets": list(SEGMENTS),
            "client_capacity": "Deploy separately after regional quota verification", "new_virtual_machines": 0,
            "new_disks": 0, "billing_plan_changes": False}
    (args.output / "network-plan.json").write_text(json.dumps(plan, indent=2) + "\n", "utf-8")
    print("Plan: reuse VM-Ventas-2 in DataCenter; preserve disk/data; temporary NAT for private servers")
    if not args.apply:
        return 0
    need(args.reuse_sales_vm, "Explicit reviewed VM reuse required")
    need(any(s.get("code") == "PowerState/deallocated" for s in vm.get("instanceView", {}).get("statuses", [])), "Private VM must be deallocated before NIC changes")
    need(args.credit_review is not None, "Recent private credit review required")
    metadata = request("rest", "--method", "get", "--uri", "/subscriptions/" + subscription,
                       "--url-parameters", "api-version=2022-12-01")
    review = json.loads(args.credit_review.read_text("utf-8"))
    guard = validate_credit(metadata, review, subscription, args.budget_usd)
    (args.output / "credit-guard.json").write_text(json.dumps(guard, indent=2) + "\n", "utf-8")
    tag_args = [key + "=" + value for key, value in TAGS.items()]
    if not pip:
        execute(args.output, "create-egress-pip", "network", "public-ip", "create", "-g", RG, "-n", PIP,
                "-l", "northcentralus", "--sku", "Standard", "--allocation-method", "Static", "--tags", *tag_args)
    if not nat:
        execute(args.output, "create-egress-nat", "network", "nat", "gateway", "create", "-g", RG, "-n", NAT,
                "-l", "northcentralus", "--public-ip-addresses", PIP, "--idle-timeout", "4", "--tags", *tag_args)
    for name in SEGMENTS:
        command = ["network", "vnet", "subnet", "update", "-g", RG, "--vnet-name", VNET, "-n", "Subnet-" + name,
                   "--nat-gateway", nat_id]
        execute(args.output, "prepare-egress-" + name, *command)
    if original:
        execute(args.output, "move-private-server-nic", "network", "nic", "ip-config", "update", "-g", RG,
                "--nic-name", nic["name"], "-n", primary["name"], "--subnet", dc["id"], "--private-ip-address", "10.0.0.132")
    if not any(c.get("privateIPAddress") == "10.0.0.133" for c in nic["ipConfigurations"]):
        execute(args.output, "add-intranet-ip", "network", "nic", "ip-config", "create", "-g", RG,
                "--nic-name", nic["name"], "-n", "intranet", "--subnet", dc["id"], "--private-ip-address", "10.0.0.133")
    execute(args.output, "private-server-azure-dns", "network", "nic", "update", "-g", RG, "-n", nic["name"],
            "--dns-servers", "168.63.129.16")
    sales = next(n for n in data["nics"] if any(c.get("privateIPAddress") == "10.0.0.68" for c in n.get("ipConfigurations", [])))
    execute(args.output, "employee-private-dns", "network", "nic", "update", "-g", RG, "-n", sales["name"], "--dns-servers", "10.0.0.132")
    after, _ = collect(args.output / "network-after")
    need(not build_plan(**after, subscription=subscription)["operations"], "Network policy changed unexpectedly")
    print("Network prepared; no VM started and no OS disk or data deleted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
