"""Read actual private service state and effective guest hardening."""
import hashlib
import http.client
import json
from pathlib import Path
import subprocess


def run(*args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=35)
        return {"code": r.returncode, "out": r.stdout[:550], "err": r.stderr[-150:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"code": -1, "error": str(e)}


def main():
    connection = http.client.HTTPConnection("10.0.0.133", 80, timeout=8)
    connection.request("GET", "/", headers={"Host": "rrhh.cafenube.internal"})
    response = connection.getresponse(); body = response.read(131072)
    actual = {"status": response.status, "sha256": hashlib.sha256(body).hexdigest(),
              "expected_sha256": EXPECTED_SHA, "matches_source": hashlib.sha256(body).hexdigest() == EXPECTED_SHA,
              "server": response.getheader("Server"), "nosniff": response.getheader("X-Content-Type-Options")}
    connection.close()
    result = {
        "http": actual,
        "named_config": run("named-checkconf", "-z"),
        "nginx_config": run("nginx", "-t"),
        "named_service": run("systemctl", "is-active", "named"),
        "nginx_service": run("systemctl", "is-active", "nginx"),
        "dns_udp": run("dig", "@10.0.0.132", "rrhh.cafenube.internal", "A", "+short", "+time=3", "+tries=1"),
        "dns_tcp": run("dig", "@10.0.0.132", "rrhh.cafenube.internal", "A", "+tcp", "+short", "+time=3", "+tries=1"),
        "reverse_dns": run("dig", "@10.0.0.132", "-x", "10.0.0.133", "+short", "+time=3", "+tries=1"),
        "ready": Path("/var/lib/cafenube/private-ready").is_file(),
        "ssh_config": run("sshd", "-t"),
    }
    print("CAFENUBE_PRIVATE_VERIFY=" + json.dumps(result))


if __name__ == "__main__":
    main()
