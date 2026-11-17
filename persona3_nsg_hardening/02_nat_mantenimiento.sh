#!/usr/bin/env bash
# =====================================================================
# Salida a Internet SOLO mientras se actualizan las VMs.
# Ventas, TI y Data Center son privadas y no tienen salida por defecto.
#   ./02_nat_mantenimiento.sh on     # crea NAT Gateway y lo pone en esas 3 subredes
#   ./02_nat_mantenimiento.sh off    # lo quita y lo borra (cuesta por hora: NO olvidar)
# =====================================================================
set -uo pipefail
cd "$(dirname "$0")"; source ./variables.env
NAT="nat-mantenimiento"; PIP="pip-nat-mantenimiento"
case "${1:-}" in
  on)
    az network public-ip create -g "$RG" -n "$PIP" -l "$REGION" --sku Standard -o none
    az network nat gateway create -g "$RG" -n "$NAT" -l "$REGION" --public-ip-addresses "$PIP" --idle-timeout 4 -o none
    for SN in "$SUBNET_VENTAS" "$SUBNET_TI" "$SUBNET_DC"; do
      ACTUAL=$(az network vnet subnet show -g "$RG" --vnet-name "$VNET" -n "$SN" --query natGateway.id -o tsv 2>/dev/null)
      if [ -n "$ACTUAL" ]; then echo "$SN ya tiene NAT ($ACTUAL), se deja igual"; continue; fi
      az network vnet subnet update -g "$RG" --vnet-name "$VNET" -n "$SN" --nat-gateway "$NAT" -o none && echo "NAT en $SN"
    done
    echo "Esperar ~1 min y correr ./03_hardening.sh" ;;
  off)
    for SN in "$SUBNET_VENTAS" "$SUBNET_TI" "$SUBNET_DC"; do
      ACTUAL=$(az network vnet subnet show -g "$RG" --vnet-name "$VNET" -n "$SN" --query natGateway.id -o tsv 2>/dev/null)
      case "$ACTUAL" in *"/$NAT") az network vnet subnet update -g "$RG" --vnet-name "$VNET" -n "$SN" --remove natGateway -o none && echo "NAT quitado de $SN";; esac
    done
    az network nat gateway delete -g "$RG" -n "$NAT"
    az network public-ip delete -g "$RG" -n "$PIP"
    echo "NAT de mantenimiento eliminado." ;;
  *) echo "uso: $0 on|off"; exit 1 ;;
esac
