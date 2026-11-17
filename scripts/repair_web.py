#!/usr/bin/env python3
"""Recover the managed web bootstrap without recreating its VM or credentials."""
import argparse
import base64
import json
from pathlib import Path

from azure_snapshot import request
from render_cloud_init import SOURCES
from validate_azure import RG, owned

ROOT = Path(__file__).resolve().parents[1]


def remote_script():
    files = [{"path": target, "mode": mode,
              "content": base64.b64encode((ROOT / source).read_text("utf-8").encode("utf-8")).decode("ascii")}
             for source, (target, mode) in SOURCES.items()]
    return "python3 - <<'CAFENUBE_REPAIR'\n" + '''import base64, json, os, subprocess
from pathlib import Path
files = ''' + repr(files) + '''
for item in files:
    p=Path(item['path'])
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(base64.b64decode(item['content'],validate=True))
    p.chmod(int(item['mode'],8))
def run(args,limit=240):
    try:
        r=subprocess.run(args,capture_output=True,text=True,timeout=limit)
        return {'exit_code':r.returncode,'stdout':r.stdout[-900:],'stderr':r.stderr[-350:]}
    except (OSError,subprocess.TimeoutExpired) as e:
        return {'exit_code':-1,'error':str(e)}
results={}
results['nginx_config']=run(['nginx','-t'])
results['ssh_config']=run(['sshd','-t'])
if all(r['exit_code']==0 for r in results.values()):
    results['retry_cloud_final']=run(['systemctl','restart','cloud-final.service'])
    results['bootstrap']=run(['bash','/usr/local/sbin/cafenube-bootstrap'])
results['cloud_init']=run(['cloud-init','status','--long'])
results['ready']=Path('/var/lib/cafenube-ready').is_file()
print('CAFENUBE_REPAIR_JSON='+json.dumps(results))
CAFENUBE_REPAIR
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        vm = request("vm", "show", "-g", RG, "-n", "VM-Web-Publica")
        owned(vm)
        (args.output / "vm-before.json").write_text(json.dumps(vm, indent=2) + "\n", encoding="utf-8")
        if not args.apply:
            print("Plan: actualizar fuentes administradas y reintentar cloud-final en VM-Web-Publica. Sin cambios.")
            return 0
        result = request("vm", "run-command", "invoke", "-g", RG, "-n", "VM-Web-Publica",
                         "--command-id", "RunShellScript", "--scripts", remote_script())
        (args.output / "repair-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        for item in result.get("value", []):
            for line in item.get("message", "").splitlines():
                if line.startswith("CAFENUBE_REPAIR_JSON="):
                    data = json.loads(line.split("=", 1)[1])
                    (args.output / "repair-parsed.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps(data, ensure_ascii=False, indent=2))
                    return 0 if data.get("ready") and all(v.get("exit_code") == 0 for v in data.values() if isinstance(v, dict)) else 1
        raise ValueError("Run Command no devolvió resultado completo del guest")
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"DETENIDO: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
