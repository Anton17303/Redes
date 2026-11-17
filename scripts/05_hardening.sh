#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_azure
OUT=$(new_evidence_dir)
exec > >(tee "$OUT/hardening.log") 2>&1
python3 "$PROJECT_ROOT/scripts/hardening.py" --output "$OUT" "$@"
