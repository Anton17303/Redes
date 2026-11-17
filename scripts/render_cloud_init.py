#!/usr/bin/env python3
"""Build deterministic cloud-config YAML (JSON is a YAML subset), no dependencies."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "web/index.html": ("/var/www/cafenube/index.html", "0644"),
    "web/styles.css": ("/var/www/cafenube/styles.css", "0644"),
    "config/nginx_cafenube.conf": ("/etc/nginx/sites-available/cafenube", "0644"),
    "config/bootstrap.sh": ("/usr/local/sbin/cafenube-bootstrap", "0755"),
    "config/hardening_vm.sh": ("/usr/local/sbin/cafenube-hardening", "0755"),
    "config/ssh_hardening.conf": ("/etc/ssh/sshd_config.d/00-cafenube.conf", "0644"),
}


def render():
    config = json.loads((ROOT / "config/cloud-init.base.json").read_text("utf-8"))
    config["write_files"] = [
        {"path": dest, "permissions": mode, "owner": "root:root",
         "content": (ROOT / source).read_text("utf-8")}
        for source, (dest, mode) in SOURCES.items()
    ]
    payload = "#cloud-config\n" + json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    if len(payload.encode("utf-8")) >= 65536:
        raise ValueError("Azure custom-data debe ocupar menos de 64 KiB")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/cloud-init.yaml")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(), encoding="utf-8", newline="\n")
    print(f"Generado {args.output} ({args.output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
