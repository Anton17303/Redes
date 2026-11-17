#!/usr/bin/env python3
"""Read guest service state; run through Azure Run Command as root."""
import json
import subprocess
from pathlib import Path


def command(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=310)
        stdout = result.stdout
        if args[0] == "sshd":
            stdout = "\n".join(line for line in stdout.splitlines() if line.split(" ")[0] in {
                "passwordauthentication", "permitrootlogin", "kbdinteractiveauthentication", "x11forwarding"})
        return {"exit_code": result.returncode, "stdout": stdout[:900], "stderr": result.stderr[-300:]}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"exit_code": -1, "error": str(error)}


def main():
    results = {
        "cloud_init": command("timeout", "300", "cloud-init", "status", "--wait", "--long"),
        "nginx_config": command("nginx", "-t"),
        "nginx_service": command("systemctl", "is-active", "nginx"),
        "http_loopback": command("curl", "--noproxy", "*", "--fail", "--silent", "--show-error",
                                 "--max-time", "8", "http://127.0.0.1/healthz"),
        "ufw": command("ufw", "status", "verbose"),
        "ssh": command("sshd", "-T"),
        "listeners": command("ss", "-H", "-lntup"),
        "bootstrap_ready": Path("/var/lib/cafenube-ready").is_file(),
    }
    print("I4_GUEST_JSON=" + json.dumps(results, ensure_ascii=True))


if __name__ == "__main__":
    main()
