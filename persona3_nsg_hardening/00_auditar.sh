#!/usr/bin/env bash
# Paso 0: foto del estado REAL en Azure antes de tocar nada.
# Compara con el reporte de Fase 1 y deja la salida en evidencias/.
set -uo pipefail
cd "$(dirname "$0")"; source ./variables.env
mkdir -p evidencias
LOG="evidencias/00_auditoria_$(date +%Y%m%d_%H%M).txt"
exec > >(tee -a "$LOG") 2>&1

echo "== Subredes de $VNET (esperado: Visitas /26, Ventas /27, TI /27, DC /28) =="
az network vnet subnet list -g "$RG" --vnet-name "$VNET" \
  --query "[].[name,addressPrefix,networkSecurityGroup.id,defaultOutboundAccess,natGateway.id]" -o tsv |
awk -F'\t' 'BEGIN{printf "%-20s %-16s %-16s %-10s %s\n","SUBRED","PREFIJO","NSG","SALIDA_DEF","NAT"}
{n=split($3,a,"/"); g=split($5,b,"/"); printf "%-20s %-16s %-16s %-10s %s\n",$1,$2,(n>1?a[n]:"(sin NSG)"),$4,(g>1?b[g]:"-")}'

for NSG in $(az network nsg list -g "$RG" --query "[].name" -o tsv); do
  echo; echo "== Reglas propias de $NSG =="
  az network nsg rule list -g "$RG" --nsg-name "$NSG" \
    --query "sort_by([],&priority)[].{Prio:priority,Dir:direction,Nombre:name,Acc:access,Prot:protocol,Origen:join(',',[sourceAddressPrefix,join(',',sourceAddressPrefixes)]),Destino:join(',',[destinationAddressPrefix,join(',',destinationAddressPrefixes)]),Puerto:join(',',[destinationPortRange,join(',',destinationPortRanges)])}" -o table
done

echo; echo "== VMs (la columna publica SOLO debe tener valor en la VM de la DMZ) =="
az vm list -g "$RG" -d --query "[].{VM:name,Privada:privateIps,Publica:publicIps,Estado:powerState}" -o table

echo; echo "== Recursos de salida a Internet (NAT / IPs públicas) =="
az network nat gateway list -g "$RG" --query "[].{NAT:name}" -o table
az network public-ip list -g "$RG" --query "[].{IP:name,Direccion:ipAddress,SKU:sku.name}" -o table

echo; echo "== Revisión rápida =="
az network vnet subnet show -g "$RG" --vnet-name "$VNET" -n "$SUBNET_DMZ" -o none 2>/dev/null \
  && echo "OK  existe $SUBNET_DMZ" || echo "FALTA $SUBNET_DMZ (la crea Jose; ajustar SUBNET_DMZ/RED_DMZ en variables.env)"
echo "Evidencia: $LOG"
