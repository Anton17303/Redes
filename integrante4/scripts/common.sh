#!/usr/bin/env bash
set -euo pipefail
I4_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$I4_ROOT/config/deployment.env" ]]; then
    # Archivo local de confianza editado por el operador, nunca descargado de Azure.
    source "$I4_ROOT/config/deployment.env"
fi
export CAFENUBE_SUBSCRIPTION_ID="${CAFENUBE_SUBSCRIPTION_ID:-}"
export CAFENUBE_DNS_LABEL="${CAFENUBE_DNS_LABEL:-cafenube-ventas-nina-231088}"
export CAFENUBE_VM_SIZE="${CAFENUBE_VM_SIZE:-Standard_B2ats_v2}"
export CAFENUBE_SSH_PUBLIC_KEY="${CAFENUBE_SSH_PUBLIC_KEY:-$HOME/.ssh/cafenube-i4.pub}"
RG='RG-CafeNube'
LOC='northcentralus'
VM='VM-Web-Publica'
NIC='NIC-Web-Publica'
PIP='PIP-Web-Publica'
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
require_azure() {
    command -v az >/dev/null || die 'Falta Azure CLI. Usar Azure Cloud Shell (Bash).'
    command -v python3 >/dev/null || die 'Falta python3.'
    [[ -n "$CAFENUBE_SUBSCRIPTION_ID" ]] || die 'Configurar CAFENUBE_SUBSCRIPTION_ID explícitamente.'
}
az_i4() { az "$@" --subscription "$CAFENUBE_SUBSCRIPTION_ID" --only-show-errors; }
new_evidence_dir() {
    local evidence_base="${CAFENUBE_EVIDENCE_ROOT:-$I4_ROOT/evidencias/azure}"
    mkdir -p "$evidence_base"
    mktemp -d "$evidence_base/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX"
}
