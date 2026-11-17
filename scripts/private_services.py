#!/usr/bin/env python3
"""Plan or install the private DNS/Intranet on an explicitly selected project VM."""
import argparse
import base64
import json
from pathlib import Path

from azure_snapshot import request
from validate_azure import need

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "intranet/index.html": ("/var/www/cafenube-intranet/index.html", "0644"),
    "config/nginx_intranet.conf": ("/etc/nginx/sites-available/cafenube-intranet", "0644"),
    "config/bind/named.conf.options": ("/etc/bind/named.conf.options", "0644"),
    "config/bind/named.conf.local": ("/etc/bind/named.conf.local", "0644"),
    "config/bind/db.cafenube.internal": ("/etc/bind/db.cafenube.internal", "0644"),
    "config/bind/db.10.0.0": ("/etc/bind/db.10.0.0", "0644"),
    "config/private-ip.sh": ("/opt/cafenube/private-ip.sh", "0755"),
    "config/private-ip.service": ("/opt/cafenube/private-ip.service", "0644"),
    "config/ssh_hardening.conf": ("/etc/ssh/sshd_config.d/00-cafenube.conf", "0644"),
    "config/hardening_vm.sh": ("/usr/local/sbin/cafenube-hardening", "0755"),
    "config/bootstrap_private.sh": ("/opt/cafenube/bootstrap_private.sh", "0755"),
}


def make_script():
    files = [{"path": target, "mode": mode,
              "data": base64.b64encode((ROOT / source).read_bytes()).decode("ascii")}
             for source, (target, mode) in FILES.items()]
    return "python3 - <<'CAFENUBE_PRIVATE'\n" + '''import base64,datetime,json,shutil,subprocess
from pathlib import Path
assert Path('/home/azureuser/.ssh/authorized_keys').is_file(), 'Existing SSH key required'
addresses=subprocess.check_output(['ip','-4','address','show'],text=True)
assert '10.0.0.132/' in addresses, 'Azure NIC must be assigned to the private Data Center first'
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup=Path('/var/backups/cafenube-private')/stamp
backup.mkdir(parents=True,exist_ok=False)
for original in ['/etc/bind','/etc/nginx','/etc/ssh/sshd_config.d','/etc/ufw']:
    source=Path(original)
    if source.is_dir(): shutil.copytree(source,backup/source.name,symlinks=True)
files=''' + repr(files) + '''
for item in files:
    path=Path(item['path'])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(base64.b64decode(item['data'],validate=True))
    path.chmod(int(item['mode'],8))
log=backup/'bootstrap.log'
with log.open('w') as output:
    result=subprocess.run(['bash','/opt/cafenube/bootstrap_private.sh'],stdout=output,stderr=subprocess.STDOUT,timeout=1200)
print('CAFENUBE_PRIVATE_JSON='+json.dumps({'exit_code':result.returncode,'ready':Path('/var/lib/cafenube/private-ready').is_file(),'backup':str(backup),'log_tail':log.read_text(errors='replace')[-1000:]}))
CAFENUBE_PRIVATE
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vm", choices=["VM-Ventas-2", "VM-Servicios-Privados"], required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    vm = request("vm", "get-instance-view", "-g", "RG-CafeNube", "-n", args.vm)
    (args.output / "vm-before.json").write_text(json.dumps(vm, indent=2) + "\n", "utf-8")
    need(vm.get("osProfile", {}).get("adminUsername") == "azureuser", "Unexpected admin account")
    script = make_script()
    (args.output / "private-script.sh").write_text(script, "utf-8", newline="\n")
    print("Plan: install DNS at 10.0.0.132 and Intranet at 10.0.0.133 on " + args.vm)
    if not args.apply:
        return 0
    need(any(s.get("code") == "PowerState/running" for s in vm.get("instanceView", {}).get("statuses", [])), "VM must already be running")
    data = request("vm", "run-command", "invoke", "-g", "RG-CafeNube", "-n", args.vm,
                   "--command-id", "RunShellScript", "--scripts", script, timeout=1500)
    (args.output / "private-result.json").write_text(json.dumps(data, indent=2) + "\n", "utf-8")
    for item in data.get("value", []):
        for line in item.get("message", "").splitlines():
            if line.startswith("CAFENUBE_PRIVATE_JSON="):
                parsed = json.loads(line.split("=", 1)[1])
                (args.output / "private-parsed.json").write_text(json.dumps(parsed, indent=2) + "\n", "utf-8")
                print(json.dumps(parsed, ensure_ascii=False, indent=2))
                return 0 if parsed.get("exit_code") == 0 and parsed.get("ready") else 1
    raise RuntimeError("No complete private guest result; inspect original Run Command output")


if __name__ == "__main__":
    raise SystemExit(main())
