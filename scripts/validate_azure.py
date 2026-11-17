#!/usr/bin/env python3
"""Conservative pre-deployment checks; ambiguous or unsupported policy fails closed.

This validates configured subnet policy. Effective NSGs/routes and guest behavior
still require a running NIC/VM and the integration tests.
"""
import ipaddress
import json
import sys
from pathlib import Path

RG = "RG-CafeNube"
LOCATION = "northcentralus"
PRIVATE = "10.0.0.148"
DMZ = "10.0.0.144/28"
TI = "10.0.0.96/27"
OWNER = {"proyecto": "CafeNube", "componente": "web-publica", "gestion": "cafenube-v1"}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def same(a, b):
    return bool(a and b) and a.lower() == b.lower()


def prefixes(rule, field):
    plural = rule.get(field + "es") if field.endswith("Prefix") else None
    return plural or [rule.get(field)]


def ports(rule, field):
    return rule.get(field + "s") or [rule.get(field)]


def security(nsg):
    """Prove a narrow accepted rule profile; never guess the meaning of ASGs/tags."""
    rules = nsg.get("securityRules", [])
    default = nsg.get("defaultSecurityRules", [])
    need({r.get("name") for r in default} >= {
        "AllowVnetInBound", "AllowVnetOutBound", "AllowInternetOutBound", "DenyAllInBound", "DenyAllOutBound"
    }, "No se recibieron las reglas predeterminadas completas")
    inbound_deny = []
    outbound_deny = []
    web = []
    ssh = []
    apt = []
    inbound_priorities, outbound_priorities = set(), set()
    for r in rules:
        name = r.get("name", "sin nombre")
        need(not r.get("sourceApplicationSecurityGroups") and not r.get("destinationApplicationSecurityGroups"),
             f"{name}: ASG requiere revisión; perfil no soportado")
        priority = r.get("priority", 99999)
        need(100 <= priority <= 4096, f"{name}: prioridad inválida")
        direction = r.get("direction")
        need(direction in ("Inbound", "Outbound"), f"{name}: dirección desconocida")
        seen = inbound_priorities if direction == "Inbound" else outbound_priorities
        need(priority not in seen, f"{name}: prioridad duplicada en {direction}")
        seen.add(priority)
        src = set(prefixes(r, "sourceAddressPrefix"))
        dst = set(prefixes(r, "destinationAddressPrefix"))
        sp = set(ports(r, "sourcePortRange"))
        dp = set(ports(r, "destinationPortRange"))
        protocol = r.get("protocol", "").lower()
        need(None not in src | dst | sp | dp, f"{name}: campos incompletos")
        universal = sp == {"*"} and dp == {"*"} and protocol == "*"
        if r.get("access") == "Deny":
            if direction == "Inbound" and src == {"*"} and dst == {"*"} and universal:
                inbound_deny.append(priority)
            if direction == "Outbound" and src <= {"*", DMZ, PRIVATE, PRIVATE + "/32"} and (
                    "VirtualNetwork" in dst or "*" in dst) and universal:
                outbound_deny.append(priority)
            continue
        need(r.get("access") == "Allow", f"{name}: acción desconocida")
        need(sp == {"*"}, f"{name}: puertos de origen no soportados")
        if direction == "Inbound":
            need(dst <= {"*", DMZ, PRIVATE, PRIVATE + "/32"}, f"{name}: destino no corresponde a DMZ")
            need(protocol == "tcp", f"{name}: permitir solo TCP de entrada")
            if src == {"Internet"} and dp == {"80"}:
                web.append(priority)
            elif src == {TI} and dp <= {"22", "80"}:
                if "22" in dp:
                    ssh.append(priority)
            else:
                raise ValueError(f"{name}: acceso fuera del perfil HTTP80 / SSH desde TI; revisar con el área de seguridad")
        else:
            need(src <= {"*", DMZ, PRIVATE, PRIVATE + "/32"}, f"{name}: origen no corresponde a DMZ")
            if dst == {"Internet"} and protocol == "tcp" and dp <= {"80", "443"}:
                apt.append((priority, dp))
            else:
                need(dst <= {"AzurePlatformDNS", "168.63.129.16", "168.63.129.16/32"}
                     and protocol in {"tcp", "udp", "*"} and dp == {"53"},
                     f"{name}: salida no soportada o posible excepción a aislamiento")
    need(inbound_deny, "Falta DenyAll-In explícito antes de AllowVnetInBound (65000)")
    need(outbound_deny, "Falta Deny hacia VirtualNetwork antes de AllowVnetOutBound (65000)")
    need(web and min(web) < min(inbound_deny), "HTTP80 no está permitido antes del bloqueo general")
    need(ssh and min(ssh) < min(inbound_deny), "SSH debe permitir únicamente TI antes del bloqueo general")
    # Cualquier Deny adicional puede bloquear apt o el servicio aun con reglas Allow válidas.
    # Un perfil inesperado se rechaza para evitar una falsa validación.
    for r in rules:
        if r.get("access") != "Deny":
            continue
        direction = r["direction"]
        src, dst = set(prefixes(r, "sourceAddressPrefix")), set(prefixes(r, "destinationAddressPrefix"))
        universal = (set(ports(r, "sourcePortRange")) == {"*"} and
                     set(ports(r, "destinationPortRange")) == {"*"} and r["protocol"] == "*")
        recognized = universal and ((direction == "Inbound" and src == {"*"} and dst == {"*"}) or
            (direction == "Outbound" and src <= {"*", DMZ, PRIVATE, PRIVATE + "/32"} and
             dst in ({"VirtualNetwork"}, {"*"})))
        need(recognized, f"{r['name']}: Deny adicional requiere revisión explícita del perfil")
    out_all = [r["priority"] for r in rules if r["direction"] == "Outbound" and
               r["access"] == "Deny" and set(prefixes(r, "destinationAddressPrefix")) == {"*"}]
    if out_all:
        allowed = set().union(*(p for priority, p in apt if priority < min(out_all)))
        need(allowed >= {"80", "443"}, "No se demuestra salida TCP80/443 para apt antes de DenyAll-Out")
        # Azure DNS no se bloquea con un Deny NSG general; el tag AzurePlatformDNS sí lo controla.
    return {"configured_nsg": "PASS", "http": 80, "ssh_source": TI,
            "dmz_to_virtualnetwork": "Deny", "tls": "not implemented",
            "effective_nsg": "PENDING: requiere NIC y VM en ejecución"}


def owned(resource):
    need(all((resource.get("tags") or {}).get(k) == v for k, v in OWNER.items()),
         f"{resource.get('name')}: recurso ajeno o sin identificación; no se reutiliza automáticamente")
    need(resource.get("location", "").lower() == LOCATION, "Ubicación de recurso existente distinta")
    need(resource.get("provisioningState", "Succeeded") == "Succeeded", "Recurso incompleto o fallido: revisar manualmente")


def validate(data):
    req, account, vnet, nsg = (data[k] for k in ("request", "account", "vnet", "nsg"))
    need(same(account.get("id"), req["subscription"]) and account.get("state") == "Enabled", "Suscripción incorrecta o inactiva")
    need(data["group"].get("name", "").lower() == RG.lower(), "Grupo incorrecto")
    base = f"/subscriptions/{req['subscription']}/resourceGroups/{RG}"
    expected_nsg = base + "/providers/Microsoft.Network/networkSecurityGroups/NSG-DMZ"
    need(same(nsg.get("id"), expected_nsg), "NSG de otra suscripción/grupo")
    need(vnet.get("location") == LOCATION and nsg.get("location") == LOCATION, "VNet/NSG fuera de northcentralus")
    need(vnet.get("addressSpace", {}).get("addressPrefixes") == ["10.0.0.0/16"], "Direccionamiento de VNet distinto al acordado")
    need(not vnet.get("virtualNetworkPeerings"), "VNet con peering: requiere revisión adicional de rutas")
    subnets = vnet.get("subnets", [])
    dmz = next((s for s in subnets if s.get("name") == "Subnet-DMZ"), None)
    need(dmz is not None, "Falta Subnet-DMZ: coordinar con el área de redes; no se crea automáticamente")
    need((dmz.get("addressPrefixes") or [dmz.get("addressPrefix")]) == [DMZ], "CIDR de Subnet-DMZ incorrecto")
    need(same(dmz.get("networkSecurityGroup", {}).get("id"), nsg["id"]), "Subnet-DMZ no usa NSG-DMZ")
    need(not dmz.get("routeTable") and not dmz.get("delegations"), "DMZ con UDR/delegación: revisar salida y rutas antes de desplegar")
    for subnet in subnets:
        if subnet is dmz:
            continue
        for prefix in subnet.get("addressPrefixes") or [subnet.get("addressPrefix")]:
            need(not ipaddress.ip_network(DMZ).overlaps(ipaddress.ip_network(prefix)), "DMZ se traslapa con otra subred")
    policy = security(nsg)
    expected = {
        "pip": ("pips", "PIP-Web-Publica", "Microsoft.Network/publicIPAddresses"),
        "nic": ("nics", "NIC-Web-Publica", "Microsoft.Network/networkInterfaces"),
        "vm": ("vms", "VM-Web-Publica", "Microsoft.Compute/virtualMachines"),
    }
    found = {}
    for kind, (collection, name, provider) in expected.items():
        resource_id = base + "/providers/" + provider + "/" + name
        resource = next((r for r in data[collection] if same(r.get("id"), resource_id)), None)
        if resource:
            owned(resource)
        found[kind] = resource
    pip, nic, vm = (found[k] for k in ("pip", "nic", "vm"))
    if pip:
        need(pip.get("sku", {}).get("name") == "Standard" and pip.get("publicIPAllocationMethod") == "Static"
             and pip.get("publicIPAddressVersion") == "IPv4", "PIP incompatible: requiere Standard Static IPv4")
        need(pip.get("dnsSettings", {}).get("domainNameLabel") == req["dns_label"], "Etiqueta DNS existente distinta")
        need(not pip.get("natGateway"), "PIP ya pertenece a un NAT Gateway")
        association = pip.get("ipConfiguration", {}).get("id")
        need(not association or (nic and association.lower().startswith(nic["id"].lower() + "/ipconfigurations/")),
             "PIP asociada a otro recurso")
    else:
        need(data["dns_available"].get("available") is True, "Etiqueta DNS ocupada: elegir otra antes de crear")
    if nic:
        need(not nic.get("networkSecurityGroup"), "NIC existente tiene otro NSG: revisar reglas acumuladas")
        need(not nic.get("enableIPForwarding"), "No permitir IP forwarding en el servidor público")
        need(nic.get("dnsSettings", {}).get("dnsServers") == ["168.63.129.16"], "NIC debe usar DNS Azure explícito, no BIND privado")
        configs = nic.get("ipConfigurations", [])
        need(len(configs) == 1, "NIC debe tener una sola configuración IP")
        ip = configs[0]
        need(ip.get("privateIPAddress") == PRIVATE and ip.get("privateIPAllocationMethod") == "Static", "IP de NIC incompatible")
        need(same(ip.get("subnet", {}).get("id"), dmz["id"]), "NIC en otra subred")
        need(pip and same(ip.get("publicIPAddress", {}).get("id"), pip["id"]), "NIC no utiliza la PIP esperada")
        need(not ip.get("loadBalancerBackendAddressPools") and not ip.get("loadBalancerInboundNatRules")
             and not ip.get("applicationGatewayBackendAddressPools"), "NIC con publicación adicional: revisar")
        attached = nic.get("virtualMachine", {}).get("id")
        need(not attached or (vm and same(attached, vm["id"])), "NIC usada por otra VM")
    for other in data["nics"]:
        for ip in other.get("ipConfigurations", []):
            if ip.get("privateIPAddress") == PRIVATE and same(ip.get("subnet", {}).get("id"), dmz["id"]):
                need(nic and same(other["id"], nic["id"]), "10.0.0.148 está ocupada por otra NIC")
    need(nic is not None or data["ip_available"].get("available") is True, "Azure indica que la IP está ocupada")
    if vm:
        vm_nics = vm.get("networkProfile", {}).get("networkInterfaces", [])
        need(nic and len(vm_nics) == 1 and same(vm_nics[0].get("id"), nic["id"])
             and vm_nics[0].get("primary", True), "VM existente debe usar únicamente NIC-Web-Publica primaria")
        need(vm.get("hardwareProfile", {}).get("vmSize") == req["vm_size"], "VM existente con tamaño distinto")
        os_profile = vm.get("osProfile", {})
        need(os_profile.get("adminUsername") == "azureuser" and os_profile.get("linuxConfiguration", {}).get("disablePasswordAuthentication") is True,
             "VM existente sin autenticación SSH exclusiva")
    else:
        for disk in data["disks"]:
            need(disk.get("name") != "Disk-Web-Publica-OS", "Disco de un despliegue parcial: revisar antes de recrear VM")
    skus = [s for s in data["skus"] if s.get("name") == req["vm_size"] and s.get("resourceType") == "virtualMachines"]
    need(any(not s.get("restrictions") for s in skus), "SKU restringido/no disponible; revisar región, cuota y presupuesto")
    if not vm:
        sku = next(s for s in skus if not s.get("restrictions"))
        cores = next((int(c["value"]) for c in sku.get("capabilities", []) if c.get("name") == "vCPUs"), 0)
        need(cores > 0 and sku.get("family"), "Azure no informó vCPU/familia del SKU")
        for quota_name in ("cores", sku["family"]):
            quota = next((q for q in data["usage"] if q.get("name", {}).get("value", "").lower() == quota_name.lower()), None)
            need(quota and quota["limit"] - quota["currentValue"] >= cores,
                 f"Cuota regional/familia insuficiente o desconocida: {quota_name}")
    return {"subscription": req["subscription"], "resource_group": RG, "location": LOCATION,
            "subnet": DMZ, "private_ip": PRIVATE, "dns_label": req["dns_label"], "vm_size": req["vm_size"],
            "resources": {k: "reuse" if v else "create" for k, v in found.items()},
            "security": policy, "cost_approval": "REQUIRED before --apply",
            "existing_resources": {k: v["id"] if v else None for k, v in found.items()}}


def main():
    folder = Path(sys.argv[1])
    data = {p.stem: json.loads(p.read_text("utf-8")) for p in folder.glob("*.json") if p.stem != "plan"}
    # No conservar una aprobación anterior si una nueva validación falla.
    plan_file = folder / "plan.json"
    plan_file.unlink(missing_ok=True)
    try:
        plan = validate(data)
    except (ValueError, KeyError, TypeError) as error:
        print(f"DETENIDO: {error}", file=sys.stderr)
        return 1
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
