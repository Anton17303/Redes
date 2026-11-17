"""Read-only diagnostics for existing Ubuntu hosts; invoked with Run Command."""
import json
import subprocess
from pathlib import Path


def run(*args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=40)
        return {"code": r.returncode, "out": r.stdout[:600], "err": r.stderr[-200:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"code": -1, "error": str(e)}


result = {
    "addresses": run("ip", "-br", "address"),
    "listeners": run("ss", "-H", "-lntup"),
    "services": run("systemctl", "list-units", "--type=service", "--state=running", "--no-pager", "--no-legend"),
    "ufw": run("ufw", "status", "verbose"),
    "authorized_key_present": Path("/home/azureuser/.ssh/authorized_keys").is_file(),
    "private_ready": Path("/var/lib/cafenube/private-ready").is_file(),
}
print("CAFENUBE_AUDIT_JSON=" + json.dumps(result))
