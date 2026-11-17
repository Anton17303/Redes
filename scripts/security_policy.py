#!/usr/bin/env python3
"""Audit and reconcile the project's NSGs; default mode is read-only."""
import argparse
import csv
import ipaddress
import json
from pathlib import Path

from azure_snapshot import request
from validate_azure import DMZ, LOCATION, RG, same, security, need

ROOT = Path(__file__).resolve().parents[1]
NETWORKS = {"Visitas": "10.0.0.0/26", "Ventas": "10.0.0.64/27", "TI": "10.0.0.96/27",
            "DataCenter": "10.0.0.128/28", "DMZ": DMZ}


def rule(name, priority, direction, access, source, destination, protocol="*", ports="*"):
    return dict(name=name, priority=priority, direction=direction, access=access, protocol=protocol,
                sourceAddressPrefixes=source.split(), destinationAddressPrefixes=destination.split(),
                sourcePortRanges=["*"], destinationPortRanges=ports.split())


def desired_rules():
    v, s, t, d, z = (NETWORKS[k] for k in ("Visitas", "Ventas", "TI", "DataCenter", "DMZ"))
    return {
        "NSG-Visitas": [rule("Allow-TI-In", 100, "Inbound", "Allow", t, v),
            rule("Deny-VNet-In", 4000, "Inbound", "Deny", "VirtualNetwork", v),
            rule("Deny-Visitas-Interno", 100, "Outbound", "Deny", v, "VirtualNetwork")],
        "NSG-Ventas": [rule("Allow-TI-In", 110, "Inbound", "Allow", t, s),
            rule("Deny-Visitas-Ventas", 100, "Inbound", "Deny", v + " " + z, s),
            rule("Deny-TI-Out", 100, "Outbound", "Deny", s, t)],
        "NSG-TI": [rule("Deny-Otras-A-TI", 100, "Inbound", "Deny", v + " " + s + " " + d + " " + z, t)],
        "NSG-DataCenter": [
            # Restrict the legacy broad rule in place; no deletion or permissive transition.
            rule("Allow-Ventas", 100, "Inbound", "Allow", s, "10.0.0.132", "*", "53"),
            rule("Allow-Ventas-DNS", 101, "Inbound", "Allow", s, "10.0.0.132", "*", "53"),
            rule("Allow-Ventas-Intranet", 105, "Inbound", "Allow", s, "10.0.0.133", "Tcp", "80"),
            rule("Allow-TI", 110, "Inbound", "Allow", t, d),
            rule("Allow-DC-Interno", 120, "Inbound", "Allow", d, d),
            rule("Deny-Resto-VNet", 200, "Inbound", "Deny", "VirtualNetwork", d),
            rule("Deny-TI-Out", 100, "Outbound", "Deny", d, t)],
        "NSG-DMZ": [rule("Allow-Web-Internet", 100, "Inbound", "Allow", "Internet", z, "Tcp", "80"),
            rule("Allow-TI-Admin", 110, "Inbound", "Allow", t, z, "Tcp", "22 80"),
            rule("Deny-All-In", 4000, "Inbound", "Deny", "*", "*"),
            rule("Deny-Internas-Out", 100, "Outbound", "Deny", z, "VirtualNetwork")],
    }


def normalize(r):
    fields = ("name", "priority", "direction", "access", "protocol")
    out = {key: r.get(key) for key in fields}
    for singular, plural in (("sourceAddressPrefix", "sourceAddressPrefixes"),
                             ("destinationAddressPrefix", "destinationAddressPrefixes"),
                             ("sourcePortRange", "sourcePortRanges"),
                             ("destinationPortRange", "destinationPortRanges")):
        out[plural] = sorted(r.get(plural) or [r.get(singular)])
    return out


def build_plan(account, vnet, nsgs, nics, subscription):
    need(same(account.get("id"), subscription) and account.get("state") == "Enabled", "Suscripción incorrecta/inactiva")
    base = f"/subscriptions/{subscription}/resourceGroups/{RG}/providers/Microsoft.Network/"
    need(same(vnet.get("id"), base + "virtualNetworks/VNet-CafeNube"), "VNet inesperada")
    need(vnet.get("location") == LOCATION and vnet.get("addressSpace", {}).get("addressPrefixes") == ["10.0.0.0/16"], "VNet fuera del diseño")
    need(not vnet.get("virtualNetworkPeerings"), "Peering requiere revisión antes de cambiar la política")
    current_subnets = {s["name"]: s for s in vnet.get("subnets", [])}
    current_nsgs = {s["name"]: s for s in nsgs}
    policies = desired_rules()
    operations = []
    for segment, cidr in NETWORKS.items():
        sn, nn = "Subnet-" + segment, "NSG-" + segment
        subnet, nsg = current_subnets.get(sn), current_nsgs.get(nn)
        expected_id = base + "networkSecurityGroups/" + nn
        if segment != "DMZ":
            need(subnet and nsg, f"Falta red/NSG existente: {segment}")
        if subnet:
            need((subnet.get("addressPrefixes") or [subnet.get("addressPrefix")]) == [cidr], f"CIDR inesperado en {sn}")
            need(not subnet.get("routeTable") and not subnet.get("delegations"), f"Rutas/delegaciones requieren revisión: {sn}")
            need(segment != "DMZ" or not subnet.get("natGateway"), "DMZ con NAT existente; revisar costos/salida sin desconectarlo")
            attached = (subnet.get("networkSecurityGroup") or {}).get("id")
            need(same(attached, expected_id) or (segment == "DMZ" and not attached), f"NSG diferente en {sn}")
        else:
            for other in current_subnets.values():
                for prefix in other.get("addressPrefixes") or [other.get("addressPrefix")]:
                    need(not ipaddress.ip_network(cidr).overlaps(ipaddress.ip_network(prefix)), "DMZ se traslapa")
        if nsg:
            need(same(nsg.get("id"), expected_id) and nsg.get("location") == LOCATION, f"NSG fuera del diseño: {nn}")
            expected_subnet = base + "virtualNetworks/VNet-CafeNube/subnets/" + sn
            need(all(same(ref.get("id"), expected_subnet) for ref in nsg.get("subnets", [])), f"{nn} asociado fuera de su subred prevista")
            for other in current_subnets.values():
                need(other.get("name") == sn or not same((other.get("networkSecurityGroup") or {}).get("id"), expected_id), f"{nn} compartido con otra subred")
            need(not any(same((nic.get("networkSecurityGroup") or {}).get("id"), expected_id) for nic in nics), f"{nn} también asociado a una NIC")
            wanted = {r["name"]: r for r in policies[nn]}
            for old in nsg.get("securityRules", []):
                need(old["name"] in wanted, f"Regla existente fuera del catálogo en {nn}: {old['name']}; revisar sin borrar")
                need(not old.get("sourceApplicationSecurityGroups") and not old.get("destinationApplicationSecurityGroups"), f"ASG requiere revisión: {nn}/{old['name']}")
                collision = next((r for r in policies[nn] if r["direction"] == old["direction"] and r["priority"] == old["priority"] and r["name"] != old["name"]), None)
                need(collision is None, f"Prioridad ocupada en {nn}: {old['name']}")
        else:
            operations.append({"action": "create-nsg", "name": nn})
        existing = {r["name"]: r for r in (nsg or {}).get("securityRules", [])}
        # Denies first so a failed run never attaches an unprotected DMZ.
        for target in sorted(policies[nn], key=lambda r: (r["access"] != "Deny", r["priority"])):
            if target["name"] not in existing or normalize(existing[target["name"]]) != normalize(target):
                operations.append({"action": "upsert-rule", "nsg": nn, "rule": target,
                                   "mode": "update" if target["name"] in existing else "create"})
        if not subnet:
            operations.append({"action": "create-subnet", "name": sn, "prefix": cidr, "nsg": nn})
        elif not subnet.get("networkSecurityGroup"):
            operations.append({"action": "associate-nsg", "name": sn, "nsg": nn})
    # Keep the web deployment's fail-closed profile as an independent check.
    defaults = [{"name": n} for n in ("AllowVnetInBound", "AllowVnetOutBound", "AllowInternetOutBound", "DenyAllInBound", "DenyAllOutBound")]
    security({"securityRules": policies["NSG-DMZ"], "defaultSecurityRules": defaults})
    return {"operations": operations, "billable_resources_created": False,
            "scope": "Project NSGs and DMZ only; no NAT, VM, IP, disk or provider registration"}


def collect(output):
    import os
    output.mkdir(parents=True, exist_ok=True)
    data = {"account": request("account", "show"),
            "vnet": request("network", "vnet", "show", "-g", RG, "-n", "VNet-CafeNube"),
            "nsgs": request("network", "nsg", "list", "-g", RG),
            "nics": request("network", "nic", "list")}
    for name, value in data.items():
        (output / (name + "-security.json")).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return data, os.environ["CAFENUBE_SUBSCRIPTION_ID"]


def apply_operation(op):
    action = op["action"]
    if action == "create-nsg":
        return request("network", "nsg", "create", "-g", RG, "-n", op["name"], "-l", LOCATION,
                       "--tags", "proyecto=CafeNube", "componente=seguridad", "gestion=cafenube-v1")
    if action == "upsert-rule":
        r = op["rule"]
        return request("network", "nsg", "rule", op["mode"], "-g", RG, "--nsg-name", op["nsg"], "-n", r["name"],
                       "--priority", str(r["priority"]), "--direction", r["direction"], "--access", r["access"],
                       "--protocol", r["protocol"], "--source-address-prefixes", *r["sourceAddressPrefixes"],
                       "--destination-address-prefixes", *r["destinationAddressPrefixes"],
                       "--source-port-ranges", "*", "--destination-port-ranges", *r["destinationPortRanges"])
    if action == "create-subnet":
        return request("network", "vnet", "subnet", "create", "-g", RG, "--vnet-name", "VNet-CafeNube", "-n", op["name"],
                       "--address-prefixes", op["prefix"], "--network-security-group", op["nsg"], "--default-outbound-access", "false")
    return request("network", "vnet", "subnet", "update", "-g", RG, "--vnet-name", "VNet-CafeNube", "-n", op["name"], "--network-security-group", op["nsg"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--export-matrix", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.export_matrix:
        with args.export_matrix.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["NSG", "Prioridad", "Direccion", "Regla", "Origen", "Destino", "Puerto", "Protocolo", "Accion"])
            for name, rules in desired_rules().items():
                for r in rules:
                    writer.writerow([name, r["priority"], r["direction"], r["name"], " ".join(r["sourceAddressPrefixes"]),
                        " ".join(r["destinationAddressPrefixes"]), " ".join(r["destinationPortRanges"]), r["protocol"], r["access"]])
        print(f"Matriz de diseño generada: {args.export_matrix}; no se consultó Azure")
        return 0
    try:
        data, subscription = collect(args.output)
        plan = build_plan(**data, subscription=subscription)
        (args.output / "security-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
        if args.apply:
            # Re-read before mutation; a changed inventory requires a fresh reviewed plan.
            latest, _ = collect(args.output / "before-apply")
            need(latest == data, "El inventario cambió durante el plan; repetir auditoría")
            for index, operation in enumerate(plan["operations"]):
                response = apply_operation(operation)
                (args.output / f"change-{index:02d}.json").write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
            after, _ = collect(args.output / "after-apply")
            need(not build_plan(**after, subscription=subscription)["operations"], "La política no quedó convergente")
            print("Política configurada y contrastada con Azure; conectividad efectiva pendiente de las pruebas.")
        return 0
    except (ValueError, KeyError, TypeError, RuntimeError, OSError) as error:
        print(f"DETENIDO: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
