#!/usr/bin/env bash
# Ejecuta diagnósticos y Run Command sin instalar extensiones ni iniciar VMs.
# La fuente externa debe declararse: Cloud Shell puede estar integrado a una VNet.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_azure
OUT=$(new_evidence_dir)
python3 "$PROJECT_ROOT/scripts/verify_deployment.py" --output "$OUT" "$@"
