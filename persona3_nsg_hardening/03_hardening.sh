#!/usr/bin/env bash
# Paso 3: hardening en todas las VMs existentes (ver VMS en variables.env).
# ANTES: ./02_nat_mantenimiento.sh on  (para que Ventas/TI/DC puedan actualizar)
# DESPUÉS: ./02_nat_mantenimiento.sh off
set -uo pipefail
cd "$(dirname "$0")"; source ./variables.env
mkdir -p evidencias
FECHA=$(date +%Y%m%d_%H%M)
NETS="$RED_VENTAS,$RED_TI,$RED_DC"
for par in $VMS; do
  VM="${par%%:*}"; ROL="${par##*:}"
  if ! az vm show -g "$RG" -n "$VM" -o none 2>/dev/null; then echo "== $VM no existe, se salta"; continue; fi
  ESTADO=$(az vm get-instance-view -g "$RG" -n "$VM" --query "instanceView.statuses[1].displayStatus" -o tsv)
  [ "$ESTADO" = "VM running" ] || { echo "== $VM está '$ESTADO', se salta (iniciarla)"; continue; }
  echo "== Hardening de $VM ($ROL)"
  az vm run-command invoke -g "$RG" -n "$VM" --command-id RunShellScript \
    --scripts @servidor/hardening_vm.sh \
    --parameters "$ROL" "$RED_TI" "${ADMIN_IP_PUBLICA:--}" "$ADMIN_USER" "$NETS" \
    --query "value[0].message" -o tsv | tee "evidencias/03_hardening_${VM}_${FECHA}.txt"
done
echo; echo "Listo. Evidencias en evidencias/03_hardening_*"
echo "No olvidar: ./02_nat_mantenimiento.sh off  y reiniciar las VMs que lo pidan."
