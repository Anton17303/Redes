#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_azure
OUT=$(new_evidence_dir)
exec > >(tee "$OUT/network-tests.log") 2>&1
python3 "$PROJECT_ROOT/scripts/verify_network.py" --output "$OUT" "$@"
