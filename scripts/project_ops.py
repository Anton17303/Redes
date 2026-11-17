"""Bounded CLI mutations with explicit subscription and unmodified result logs."""
import json
import os
from pathlib import Path
import shutil
import subprocess


def execute(output, label, *args, timeout=1200):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    command = [shutil.which("az") or "az", *args, "--subscription",
               os.environ["CAFENUBE_SUBSCRIPTION_ID"], "--only-show-errors", "-o", "json"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    record = {"command": command, "exit_code": result.returncode,
              "stdout": result.stdout, "stderr": result.stderr}
    (output / (label + ".json")).write_text(json.dumps(record, indent=2) + "\n", "utf-8")
    if result.returncode:
        raise RuntimeError("Azure CLI failed for " + label + ": " + result.stderr.strip())
    return json.loads(result.stdout) if result.stdout.strip() else None
