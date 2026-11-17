#!/usr/bin/env python3
"""Record real DNS, HTTP, Azure effective policy and guest/positive-control results."""
import argparse
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from azure_snapshot import collect, request
from validate_azure import PRIVATE, same, validate

ROOT = Path(__file__).resolve().parents[1]


class Evidence:
    def __init__(self, output):
        self.output = output
        self.rows = []
        output.mkdir(parents=True, exist_ok=True)

    def save(self, name, data):
        (self.output / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def result(self, test, state, detail):
        self.rows.append({"test": test, "result": state, "detail": detail})
        print(f"{state}: {test}: {detail}", flush=True)

    def azure(self, name, *args):
        try:
            data = request(*args)
            self.save(name, data)
            return data
        except (RuntimeError, ValueError) as error:
            self.save(name, {"error": str(error)})
            self.result(name, "INCONCLUSIVE", str(error))
            return None

    def finish(self):
        self.save("results", {"utc": datetime.now(timezone.utc).isoformat(), "tests": self.rows})
        text = "# Resultados reales de Azure\n\n| Prueba | Resultado | Detalle |\n|---|---|---|\n"
        for row in self.rows:
            text += "| " + " | ".join(str(row[k]).replace("|", "/").replace("\n", " ") for k in ("test", "result", "detail")) + " |\n"
        (self.output / "RESULTADOS.md").write_text(text, encoding="utf-8")
        return 1 if any(r["result"] == "FAIL" for r in self.rows) else (
            2 if any(r["result"] in {"PENDING", "INCONCLUSIVE"} for r in self.rows) else 0)


def run_remote(evidence, vm, name, script, marker):
    # A Run Command provisioning success is not a successful test; require our JSON marker.
    data = evidence.azure(name, "vm", "run-command", "invoke", "-g", "RG-CafeNube", "-n", vm,
                          "--command-id", "RunShellScript", "--scripts", "python3 - <<'CAFENUBE_PY'\n" + script + "\nCAFENUBE_PY")
    if data is None:
        return None
    for item in data.get("value", []):
        for line in item.get("message", "").splitlines():
            if line.startswith(marker):
                try:
                    parsed = json.loads(line[len(marker):])
                    evidence.save(name + "-parsed", parsed)
                    return parsed
                except json.JSONDecodeError:
                    pass
    evidence.result(name + "-guest-result", "INCONCLUSIVE", "Run Command no devolvió JSON completo; revisar stdout/stderr")
    return None


def running(evidence, vm, name):
    data = evidence.azure(name, "vm", "get-instance-view", "-g", "RG-CafeNube", "-n", vm)
    view = (data or {}).get("instanceView", data or {})
    return any(s.get("code") == "PowerState/running" for s in view.get("statuses", []))


def public_tests(evidence, pip, external):
    fqdn = (pip.get("dnsSettings") or {}).get("fqdn") or ""
    public_ip = pip.get("ipAddress") or ""
    try:
        global_ip = ipaddress.ip_address(public_ip).is_global
    except ValueError:
        global_ip = False
    if not re.fullmatch(r"[a-z0-9.-]+\.cloudapp\.azure\.com", fqdn) or not global_ip:
        evidence.result("public-endpoint", "INCONCLUSIVE", "Azure no devolvió un FQDN cloudapp.azure.com y una IP pública válidos")
        return
    evidence.save("endpoint", {"fqdn": fqdn, "public_ip": public_ip, "external_source": external})
    try:
        resolved = {r[4][0] for r in socket.getaddrinfo(fqdn, 80, socket.AF_INET, socket.SOCK_STREAM)}
        evidence.result("dns-system", "PASS" if resolved == {public_ip} else "FAIL", f"{fqdn} -> {sorted(resolved)}; esperado {public_ip}")
    except OSError as error:
        evidence.result("dns-system", "FAIL", str(error))
    for resolver in ("1.1.1.1", "8.8.8.8"):
        try:
            result = subprocess.run(["dig", "@" + resolver, fqdn, "A", "+short", "+time=3", "+tries=1"],
                                    capture_output=True, text=True, timeout=6)
            addresses = {line for line in result.stdout.splitlines() if re.fullmatch(r"[0-9.]+", line)}
            evidence.save("dns-" + resolver, {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode})
            state = "PASS" if result.returncode == 0 and addresses == {public_ip} else "INCONCLUSIVE"
            evidence.result("dns-public-" + resolver, state, "Respuesta pública guardada; cotejada con IP de Azure")
        except (OSError, subprocess.TimeoutExpired) as error:
            evidence.result("dns-public-" + resolver, "INCONCLUSIVE", str(error))
    if not external:
        evidence.result("http-external-source", "PENDING", "Repetir con --external-source indicando una red realmente externa a la VNet")
    for route, source in (("/", "web/index.html"), ("/styles.css", "web/styles.css"), ("/healthz", None)):
        connection = http.client.HTTPConnection(fqdn, 80, timeout=12)
        try:
            connection.request("GET", route)
            response = connection.getresponse()
            body = response.read(131072)
            headers = dict(response.getheaders())
            expected = (ROOT / source).read_bytes() if source else b"cafenube-ok\n"
            state = "PASS" if response.status == 200 and hashlib.sha256(body).digest() == hashlib.sha256(expected).digest() else "FAIL"
            if not external and state == "PASS":
                state = "INCONCLUSIVE"
            evidence.save("http-" + (route.strip("/") or "index").replace(".", "-"),
                          {"status": response.status, "headers": headers, "body_sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
            evidence.result("http" + route, state,
                            f"Esperado HTTP200 y contenido exacto; observado HTTP{response.status}, "
                            f"contenido_coincide={body == expected}; fuente: {external or 'sin confirmar'}")
            if route == "/":
                safe_headers = (response.getheader("Server", "").lower() == "nginx" and
                                response.getheader("X-Content-Type-Options") == "nosniff" and
                                response.getheader("X-Frame-Options") == "DENY" and
                                bool(response.getheader("Content-Security-Policy")))
                evidence.result("nginx-public-headers", "PASS" if safe_headers else "FAIL",
                                f"Esperado Nginx sin versión y cabeceras de seguridad; coincide={safe_headers}")
        except (OSError, http.client.HTTPException) as error:
            evidence.result("http" + route, "INCONCLUSIVE", f"{error}; no equivale a bloqueo NSG")
        finally:
            connection.close()
    # Son intentos TCP, no una afirmación de firewall ante un timeout.
    for port in (22, 53, 443):
        try:
            with socket.create_connection((public_ip, port), timeout=3):
                evidence.result(f"public-tcp-{port}", "FAIL", "Conexión inesperada al puerto no publicado")
        except OSError as error:
            evidence.save(f"public-tcp-{port}", {"error": str(error), "interpretation": "NSG debe confirmar el motivo; silencio no demuestra bloqueo"})


def flow_tests(evidence):
    watchers = evidence.azure("network-watchers", "network", "watcher", "list")
    if not watchers or not any(w.get("location") == "northcentralus" for w in watchers):
        evidence.result("effective-ip-flow", "PENDING", "No hay Network Watcher existente en northcentralus; no se crea automáticamente")
        return False
    cases = [("http-internet", "Inbound", "TCP", PRIVATE + ":80", "1.1.1.1:50000", "Allow"),
             ("ssh-ti", "Inbound", "TCP", PRIVATE + ":22", "10.0.0.100:50000", "Allow")]
    for port in (22, 443, 53, 3389):
        cases.append((f"internet-{port}", "Inbound", "TCP", f"{PRIVATE}:{port}", "1.1.1.1:50000", "Deny"))
    cases.append(("internet-dns-udp", "Inbound", "UDP", PRIVATE + ":53", "1.1.1.1:50000", "Deny"))
    for name, ip in (("visitas", "10.0.0.4"), ("ventas", "10.0.0.68"), ("dc", "10.0.0.133")):
        for port in (22, 80):
            cases.append((f"{name}-in-{port}", "Inbound", "TCP", f"{PRIVATE}:{port}", ip + ":50000", "Deny"))
    for name, ip, port, protocol in (("ventas", "10.0.0.68", 22, "TCP"), ("ti", "10.0.0.100", 22, "TCP"),
                                     ("dns-tcp", "10.0.0.132", 53, "TCP"), ("dns-udp", "10.0.0.132", 53, "UDP"),
                                     ("intranet", "10.0.0.133", 80, "TCP"), ("visitas", "10.0.0.4", 80, "TCP")):
        cases.append(("dmz-to-" + name, "Outbound", protocol, PRIVATE + ":50000", f"{ip}:{port}", "Deny"))
    passed = True
    for name, direction, protocol, local, remote, expected in cases:
        data = evidence.azure("flow-" + name, "network", "watcher", "test-ip-flow", "-g", "RG-CafeNube",
                              "--vm", "VM-Web-Publica", "--nic", "NIC-Web-Publica", "--direction", direction,
                              "--protocol", protocol, "--local", local, "--remote", remote)
        valid = data is not None and data.get("access") == expected and bool(data.get("ruleName"))
        evidence.result("ip-flow-" + name, "PASS" if valid else ("FAIL" if data else "INCONCLUSIVE"),
                        f"Esperado {expected}; resultado {data}")
        passed = passed and valid
    return passed


def privacy_inventory(evidence, data):
    for name in ("VM-DNS", "VM-Intranet"):
        vm = next((v for v in data["vms"] if v.get("name") == name and "/resourcegroups/rg-cafenube/" in v.get("id", "").lower()), None)
        if not vm:
            evidence.result("private-" + name, "PENDING", "No existe en el inventario de la suscripción")
            continue
        interfaces = vm.get("networkProfile", {}).get("networkInterfaces", [])
        complete, exposed, proxy = bool(interfaces), False, False
        for interface in interfaces:
            nic = next((n for n in data["nics"] if same(n.get("id"), interface.get("id"))), None)
            if not nic:
                complete = False
                continue
            for config in nic.get("ipConfigurations", []):
                exposed = exposed or bool(config.get("publicIPAddress"))
                proxy = proxy or any(config.get(k) for k in ("loadBalancerBackendAddressPools", "loadBalancerInboundNatRules", "applicationGatewayBackendAddressPools"))
        evidence.result("private-direct-ip-" + name, "FAIL" if exposed else ("PASS" if complete else "INCONCLUSIVE"),
                        "Inventario de todas las NIC: asociación directa de IP pública")
        if proxy:
            evidence.result("private-proxy-" + name, "INCONCLUSIVE", "NIC asociada a balanceador/gateway; revisar publicación indirecta con Adrián/José")
    for kind, resource_type in (("load-balancers", "Microsoft.Network/loadBalancers"),
                                ("app-gateways", "Microsoft.Network/applicationGateways"),
                                ("firewalls", "Microsoft.Network/azureFirewalls")):
        # API genérica de inventario: evita instalar extensiones de Azure CLI.
        inventory = evidence.azure("private-" + kind, "resource", "list", "--resource-type", resource_type)
        if inventory is not None:
            serialized = json.dumps(inventory)
            possible = any(ip in serialized for ip in ("10.0.0.132", "10.0.0.133")) or bool(inventory)
            evidence.result("private-indirect-" + kind, "INCONCLUSIVE" if possible else "PASS",
                            "Revisar frontends/reglas/backend privados" if possible else "No hay recursos de este tipo en la suscripción")
    evidence.result("private-publication-scope", "PENDING",
                    "Adrián/José deben confirmar ausencia de proxies/túneles/DNS público ajenos a este inventario y aportar prueba externa")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--external-source", default="", help="Descripción veraz: red móvil, equipo externo o Cloud Shell sin VNet")
    args = parser.parse_args()
    evidence = Evidence(args.output)
    try:
        collect(args.output)
        data = {p.stem: json.loads(p.read_text("utf-8")) for p in args.output.glob("*.json")}
        plan = validate(data)
        evidence.save("plan", plan)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        evidence.result("preflight", "FAIL", str(error))
        return evidence.finish()
    evidence.result("configured-security", "PASS", "Perfil conservador NSG validado incluyendo reglas predeterminadas")
    privacy_inventory(evidence, data)
    pip = next((p for p in data["pips"] if same(p.get("id"), plan["existing_resources"]["pip"])), None)
    if pip:
        public_tests(evidence, pip, args.external_source)
    else:
        evidence.result("public-site", "PENDING", "PIP todavía no creada")
    if not plan["existing_resources"]["vm"] or not running(evidence, "VM-Web-Publica", "public-vm-state"):
        evidence.result("guest-and-isolation", "PENDING", "VM pública inexistente/apagada; no se inicia automáticamente")
        return evidence.finish()
    effective = evidence.azure("effective-nsg", "network", "nic", "list-effective-nsg", "-g", "RG-CafeNube", "-n", "NIC-Web-Publica")
    if effective is not None:
        entries = effective.get("value", []) if isinstance(effective, dict) else effective
        ids = {e.get("networkSecurityGroup", {}).get("id", "").lower() for e in entries}
        expected = data["nsg"]["id"].lower()
        evidence.result("effective-nsg-association", "PASS" if ids == {expected} else "FAIL", "Reglas efectivas guardadas y NSG esperado único")
    evidence.azure("effective-routes", "network", "nic", "show-effective-route-table", "-g", "RG-CafeNube", "-n", "NIC-Web-Publica")
    policy_ok = flow_tests(evidence)
    guest = run_remote(evidence, "VM-Web-Publica", "guest-services", (ROOT / "config/verify_guest.py").read_text("utf-8"), "I4_GUEST_JSON=")
    if guest:
        for key in ("cloud_init", "nginx_config", "nginx_service", "http_loopback"):
            check = guest.get(key, {})
            ok = check.get("exit_code") == 0
            if key == "cloud_init":
                ok = ok and "status: done" in check.get("stdout", "")
            evidence.result("guest-" + key, "PASS" if ok else "FAIL", str(check))
        ufw = guest.get("ufw", {}).get("stdout", "")
        ssh = guest.get("ssh", {}).get("stdout", "")
        ok = (guest.get("bootstrap_ready") and "Status: active" in ufw and "10.0.0.96/27" in ufw and
              all(setting in ssh.splitlines() for setting in ("passwordauthentication no", "permitrootlogin no", "kbdinteractiveauthentication no")))
        evidence.result("guest-hardening", "PASS" if ok else "FAIL", "UFW, marcador de bootstrap y configuración efectiva de sshd")
    probe_script = (ROOT / "config/probe_internal.py").read_text("utf-8")
    negative = run_remote(evidence, "VM-Web-Publica", "dmz-probes", "ROLE='DMZ'\n" + probe_script, "I4_PROBE_JSON=")
    positive = None
    ti = next((v for v in data["vms"] if v.get("name") == "VM-TI-1" and "/resourcegroups/rg-cafenube/" in v.get("id", "").lower()), None)
    if ti and running(evidence, "VM-TI-1", "ti-vm-state"):
        positive = run_remote(evidence, "VM-TI-1", "ti-positive-controls", "ROLE='TI'\n" + probe_script, "I4_PROBE_JSON=")
    if not positive:
        evidence.result("positive-controls", "PENDING", "Requiere VM-TI-1 activa y servicios privados sanos; un timeout desde DMZ no prueba aislamiento")
    for name in ("dns_udp", "dns_tcp", "intranet_http"):
        blocked = (negative or {}).get(name)
        healthy = (positive or {}).get(name, {}).get("healthy")
        if blocked and blocked.get("response"):
            state, detail = "FAIL", "DMZ recibió respuesta del servicio interno, incluso REFUSED sería conectividad"
        elif blocked and healthy and policy_ok:
            state, detail = "PASS", "Sin respuesta desde DMZ + servicio sano desde TI + Deny efectivo de Azure"
        else:
            state, detail = "INCONCLUSIVE", "Falta control positivo sano, prueba guest o Deny efectivo; no atribuirlo a NSG"
        evidence.result("dmz-isolation-" + name, state, detail)
    if positive:
        evidence.result("admin-positive-ssh-ti", "PASS" if positive.get("admin_ssh", {}).get("healthy") else "INCONCLUSIVE", "Banner SSH desde TI a 10.0.0.148:22")
    evidence.result("browser-external-screenshot", "PENDING", "Abrir FQDN en navegador externo y guardar captura real con fecha/origen")
    print(f"Evidencias: {args.output}")
    return evidence.finish()


if __name__ == "__main__":
    sys.exit(main())
