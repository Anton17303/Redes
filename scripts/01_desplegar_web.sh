#!/usr/bin/env bash
# Sin argumentos: solo plan. --apply requiere aprobación explícita y preflight nuevo.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
APPLY=0
BUDGET=''
APPROVER=''
while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply) APPLY=1; shift ;;
        --budget-usd) [[ $# -ge 2 ]] || die 'Falta monto'; BUDGET="$2"; shift 2 ;;
        --approved-by) [[ $# -ge 2 ]] || die 'Falta responsable'; APPROVER="$2"; shift 2 ;;
        *) die "Argumento desconocido: $1" ;;
    esac
done
if [[ "$APPLY" == 1 ]]; then
    [[ "$BUDGET" =~ ^[0-9]+([.][0-9]{1,2})?$ && -n "$APPROVER" ]] || die 'Requiere --budget-usd MONTO --approved-by RESPONSABLE.'
    python3 -c 'import sys; sys.exit(0 if float(sys.argv[1]) > 0 else 1)' "$BUDGET" || die 'Presupuesto debe ser mayor que cero.'
fi
require_azure
OUT=$(new_evidence_dir)
exec > >(tee "$OUT/deployment.log") 2>&1
python3 "$PROJECT_ROOT/scripts/render_cloud_init.py"
bash "$PROJECT_ROOT/scripts/00_preflight.sh" "$OUT"
if [[ "$APPLY" == 0 ]]; then
    printf 'Solo plan. No se crearon recursos. Revisar %s/plan.json y docs/CLOUD_SHELL.md\n' "$OUT"
    exit 0
fi
[[ -f "$CAFENUBE_SSH_PUBLIC_KEY" ]] || die 'No existe la clave pública configurada. Ver docs/CLOUD_SHELL.md.'
command -v ssh-keygen >/dev/null || die 'Falta ssh-keygen para validar la clave pública antes de crear recursos.'
ssh-keygen -lf "$CAFENUBE_SSH_PUBLIC_KEY" >/dev/null || die 'La clave pública OpenSSH es inválida.'
python3 "$PROJECT_ROOT/scripts/check_credit_guard.py" \
    --review "$CAFENUBE_CREDIT_REVIEW" --budget-usd "$BUDGET" --output "$OUT"
python3 - "$CAFENUBE_SSH_PUBLIC_KEY" "$OUT" "$BUDGET" "$APPROVER" <<'PY'
import base64, json, sys
from datetime import datetime, timezone
from pathlib import Path
key=Path(sys.argv[1]).read_text().strip().split()
if len(key) < 2 or key[0] not in {'ssh-ed25519','ssh-rsa'}:
    raise SystemExit('Usar una clave pública OpenSSH RSA/Ed25519; nunca una clave privada')
base64.b64decode(key[1], validate=True)
Path(sys.argv[2], 'approval.json').write_text(json.dumps({
    'approved_by':sys.argv[4], 'budget_usd':sys.argv[3],
    'utc':datetime.now(timezone.utc).isoformat(),
    'notice':'Monto autorizado registrado; no es un límite de facturación automático.'
}, indent=2)+'\n')
PY
state() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["resources"][sys.argv[2]])' "$OUT/plan.json" "$1"; }
TAGS=('proyecto=CafeNube' 'componente=web-publica' 'gestion=cafenube-v1')
# El preflight valida TODO recurso existente antes de esta primera mutación.
# Si ocurre un fallo parcial, se conservan los recursos propios para reintentar.
trap 'printf "Despliegue interrumpido. No se borró nada. Revisar recursos propios y repetir preflight. Evidencia: %s\n" "$OUT" >&2' ERR
if [[ "$(state pip)" == create ]]; then
    az_project network public-ip create -g "$RG" -n "$PIP" -l "$LOC" \
        --sku Standard --tier Regional --allocation-method Static --version IPv4 \
        --dns-name "$CAFENUBE_DNS_LABEL" --tags "${TAGS[@]}" -o none
fi
if [[ "$(state nic)" == create ]]; then
    az_project network nic create -g "$RG" -n "$NIC" -l "$LOC" \
        --vnet-name VNet-CafeNube --subnet Subnet-DMZ --private-ip-address 10.0.0.148 \
        --public-ip-address "$PIP" --dns-servers 168.63.129.16 \
        --ip-forwarding false --tags "${TAGS[@]}" -o none
fi
if [[ "$(state vm)" == create ]]; then
    az_project vm create -g "$RG" -n "$VM" -l "$LOC" --image Ubuntu2204 \
        --nics "$NIC" --size "$CAFENUBE_VM_SIZE" --admin-username azureuser \
        --authentication-type ssh --ssh-key-values "$CAFENUBE_SSH_PUBLIC_KEY" \
        --custom-data "$PROJECT_ROOT/build/cloud-init.yaml" --storage-sku Standard_LRS \
        --os-disk-name Disk-Web-Publica-OS --os-disk-size-gb 30 \
        --tags "${TAGS[@]}" -o none
else
    printf 'VM existente validada; no se modifica, reinicia ni inicia automáticamente.\n'
fi
az_project network public-ip show -g "$RG" -n "$PIP" \
    --query '{fqdn:dnsSettings.fqdn,ip:ipAddress}' -o json > "$OUT/public-endpoint.json"
cat "$OUT/public-endpoint.json"
printf 'Creación de recursos terminada. La disponibilidad de Nginx aún debe probarse.\n'
printf 'Ejecutar 02_pruebas.sh; después de la sesión, 03_apagar.sh.\n'
