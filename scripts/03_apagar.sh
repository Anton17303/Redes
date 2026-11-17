#!/usr/bin/env bash
# Únicamente la VM pública propia; no elimina discos, IPs ni el grupo.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_azure
OUT=$(new_evidence_dir)
exec > >(tee "$OUT/deallocate.log") 2>&1
az_project vm show -g "$RG" -n "$VM" -o json > "$OUT/vm-before.json"
python3 - "$OUT/vm-before.json" <<'PY'
import json,sys
vm=json.load(open(sys.argv[1]))
expected={'proyecto':'CafeNube','componente':'web-publica','gestion':'cafenube-v1'}
if any((vm.get('tags') or {}).get(k)!=v for k,v in expected.items()):
    raise SystemExit('Recurso sin identificación propia; se cancela desasignación')
PY
az_project vm deallocate -g "$RG" -n "$VM"
az_project vm get-instance-view -g "$RG" -n "$VM" -o json > "$OUT/vm-after.json"
python3 - "$OUT/vm-after.json" <<'PY'
import json,sys
view=json.load(open(sys.argv[1]))
if not any(s.get('code')=='PowerState/deallocated' for s in view.get('instanceView',{}).get('statuses',view.get('statuses',[]))):
    raise SystemExit('No se confirmó PowerState/deallocated; revisar Azure')
print('CONFIRMADO: VM-Web-Publica desasignada. Disco e IP Standard siguen siendo facturables.')
PY
