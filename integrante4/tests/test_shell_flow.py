"""Execute real Bash scripts against a fake CLI; all resources are fixtures."""
import json
import base64
import os
import shlex
import shutil
import subprocess
import struct
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from test_safety import ROOT, SUBSCRIPTION, fixture


class ShellFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bash = (r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else shutil.which("bash"))
        if not cls.bash or not Path(cls.bash).exists():
            raise unittest.SkipTest("Bash no disponible")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.state = self.folder / "state.json"
        self.state.write_text(json.dumps({"data": fixture(), "calls": []}), encoding="utf-8")
        python = sys.executable.replace("\\", "/")
        fake = str(Path(__file__).with_name("mock_az.py")).replace("\\", "/")
        (self.folder / "az").write_text(f"#!/usr/bin/env bash\nexec {shlex.quote(python)} {shlex.quote(fake)} \"$@\"\n", encoding="utf-8", newline="\n")
        (self.folder / "python3").write_text(f"#!/usr/bin/env bash\nexec {shlex.quote(python)} \"$@\"\n", encoding="utf-8", newline="\n")
        if os.name == "nt":
            (self.folder / "az.cmd").write_text(f'@"{sys.executable}" "{Path(__file__).with_name("mock_az.py")}" %*\n')
        else:
            (self.folder / "az").chmod(0o755)
            (self.folder / "python3").chmod(0o755)
        self.key = self.folder / "public.pub"
        public_blob = struct.pack('!I', 11) + b'ssh-ed25519' + struct.pack('!I', 32) + b'\x01' * 32
        self.key.write_text("ssh-ed25519 " + base64.b64encode(public_blob).decode('ascii') + " synthetic-public-key\n")
        self.credit_review = self.folder / "synthetic-credit-review.json"
        self.credit_review.write_text(json.dumps({
            'subscription_id':SUBSCRIPTION, 'reviewed_at_utc':datetime.now(timezone.utc).isoformat(),
            'expires_on':'2099-01-01', 'available_lower_bound_usd':'10.00'
        }), encoding='utf-8')
        self.env = {**os.environ, "PATH": str(self.folder) + os.pathsep + os.environ["PATH"],
                    "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
                    "CAFENUBE_TEST_STATE": str(self.state), "CAFENUBE_SUBSCRIPTION_ID": SUBSCRIPTION,
                    "CAFENUBE_DNS_LABEL": "cafenube-test", "CAFENUBE_VM_SIZE": "Standard_B2ats_v2",
                    "CAFENUBE_EVIDENCE_ROOT": str(self.folder / "synthetic-evidence").replace("\\", "/"),
                    "CAFENUBE_CREDIT_REVIEW": str(self.credit_review).replace("\\", "/"),
                    "CAFENUBE_SSH_PUBLIC_KEY": str(self.key).replace("\\", "/")}

    def run_script(self, script, *args):
        return subprocess.run([self.bash, "--noprofile", "--norc", str(ROOT / "scripts" / script).replace("\\", "/"), *args],
                              env=self.env, capture_output=True, text=True, encoding="utf-8", timeout=90)

    def calls(self):
        return json.loads(self.state.read_text("utf-8"))["calls"]

    def mutations(self):
        return [call for call in self.calls() if "create" in call or "deallocate" in call or "update" in call]

    def test_default_plan_performs_no_mutations(self):
        result = self.run_script("01_desplegar_web.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.mutations(), [])

    def test_apply_without_budget_stops_before_azure(self):
        result = self.run_script("01_desplegar_web.sh", "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_invalid_public_key_prevents_billable_mutations(self):
        self.key.write_text('ssh-ed25519 YWJj invalid-test-key\n')
        result = self.run_script("01_desplegar_web.sh", "--apply", "--budget-usd", "1", "--approved-by", "TEST ONLY")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_rbac_failure_cannot_be_treated_as_missing_resource(self):
        state = json.loads(self.state.read_text("utf-8"))
        state["fail_read"] = True
        self.state.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_script("01_desplegar_web.sh", "--apply", "--budget-usd", "1", "--approved-by", "TEST ONLY")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_unsafe_nsg_prevents_all_billable_mutations(self):
        state = json.loads(self.state.read_text("utf-8"))
        state["data"]["nsg"]["securityRules"][1]["sourceAddressPrefix"] = "Internet"
        self.state.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_script("01_desplegar_web.sh", "--apply", "--budget-usd", "1", "--approved-by", "TEST ONLY")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_apply_then_rerun_does_not_duplicate_resources(self):
        args = ("--apply", "--budget-usd", "1", "--approved-by", "TEST ONLY")
        first = self.run_script("01_desplegar_web.sh", *args)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(len(self.mutations()), 3)
        second = self.run_script("01_desplegar_web.sh", *args)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(len(self.mutations()), 3)

    def test_disabled_spending_protection_prevents_billable_mutations(self):
        state = json.loads(self.state.read_text('utf-8'))
        state['spending_limit'] = 'Off'
        self.state.write_text(json.dumps(state), encoding='utf-8')
        result = self.run_script('01_desplegar_web.sh', '--apply', '--budget-usd', '1', '--approved-by', 'TEST ONLY')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_shutdown_only_targets_owned_vm(self):
        state = {"data": fixture(True), "calls": []}
        self.state.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_script("03_apagar.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.mutations()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], ["vm", "deallocate"])
        self.assertIn("VM-Web-Publica", calls[0])

    def test_shutdown_does_not_touch_foreign_vm(self):
        data = fixture(True)
        data['vms'][0]['tags']['integrante'] = '2'
        self.state.write_text(json.dumps({'data':data,'calls':[]}), encoding='utf-8')
        result = self.run_script('03_apagar.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mutations(), [])


if __name__ == "__main__":
    unittest.main()
