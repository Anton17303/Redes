#!/usr/bin/env bash
# Solo lectura en Azure. Un error de autenticación/RBAC nunca equivale a «no existe».
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_azure
if [[ $# -gt 1 ]]; then die 'Uso: bash 00_preflight.sh [directorio-de-evidencia]'; fi
OUT="${1:-$(new_evidence_dir)}"
mkdir -p "$OUT"
exec > >(tee "$OUT/preflight.log") 2>&1
python3 "$I4_ROOT/scripts/azure_snapshot.py" "$OUT"
python3 "$I4_ROOT/scripts/validate_azure.py" "$OUT"
printf 'Preflight aprobado. Inventario y plan: %s\n' "$OUT"
