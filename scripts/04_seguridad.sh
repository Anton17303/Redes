#!/usr/bin/env bash
# Audita por defecto. --apply reconcilia solo los NSGs y la DMZ del proyecto.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# == 0 || ($# == 1 && $1 == --apply) ]] || die 'Uso: 04_seguridad.sh [--apply]'
require_azure
OUT=$(new_evidence_dir)
exec > >(tee "$OUT/security.log") 2>&1
python3 "$PROJECT_ROOT/scripts/security_policy.py" --output "$OUT" "$@"
