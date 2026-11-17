#!/usr/bin/env bash
# =====================================================================
# Paso 1: aplica la política de Fase 2 en los NSG.  Es idempotente
# (crea o actualiza cada regla por nombre).  Probar antes con:
#     DRY_RUN=1 ./01_nsg_reglas.sh
# Los NSG son stateful: lo que se bloquea es INICIAR la conexión;
# las respuestas de conexiones permitidas vuelven solas.
# =====================================================================
set -uo pipefail
set -f                                  # que '*' no se expanda
cd "$(dirname "$0")"; source ./variables.env
mkdir -p evidencias
LOG="evidencias/01_nsg_reglas_$(date +%Y%m%d_%H%M).txt"
exec > >(tee -a "$LOG") 2>&1
AZ=az; [ "${DRY_RUN:-0}" = "1" ] && AZ="echo [dry-run] az"

nsg_de() {  # nsg_de <subred> <nombre_por_defecto>
  [ "${DRY_RUN:-0}" = "1" ] && { echo "$2"; return; }
  az network vnet subnet show -g "$RG" --vnet-name "$VNET" -n "$1" \
     --query "networkSecurityGroup.id" -o tsv 2>/dev/null | awk -F/ 'NF{print $NF}'
}

regla() {  # regla NSG NOMBRE PRIO DIRECCION ACCESO PROTO ORIGEN DESTINO PUERTOS
  local nsg="$1" nom="$2" prio="$3" dir="$4" acc="$5" proto="$6" src="$7" dst="$8" ports="$9" op=create
  if [ "${DRY_RUN:-0}" != "1" ] && az network nsg rule show -g "$RG" --nsg-name "$nsg" -n "$nom" -o none 2>/dev/null; then op=update; fi
  echo "-- $nsg | $nom | $op | prio $prio | $dir | $acc"
  $AZ network nsg rule $op -g "$RG" --nsg-name "$nsg" --name "$nom" --priority "$prio" \
      --direction "$dir" --access "$acc" --protocol "$proto" \
      --source-address-prefixes $src --source-port-ranges '*' \
      --destination-address-prefixes $dst --destination-port-ranges $ports -o none \
    || echo "   !! FALLÓ $nom (¿prioridad $prio ya usada por otra regla? mirar 00_auditar.sh)"
}
borrar() { # borrar NSG NOMBRE
  [ "${DRY_RUN:-0}" = "1" ] && { echo "[dry-run] borrar $1/$2"; return; }
  az network nsg rule show -g "$RG" --nsg-name "$1" -n "$2" -o none 2>/dev/null && \
    { echo "-- $1 | borrando regla vieja $2"; az network nsg rule delete -g "$RG" --nsg-name "$1" -n "$2"; }
}

V="$RED_VISITAS"; S="$RED_VENTAS"; T="$RED_TI"; D="$RED_DC"; Z="$RED_DMZ"

NSG_V=$(nsg_de "$SUBNET_VISITAS" NSG-Visitas)
NSG_S=$(nsg_de "$SUBNET_VENTAS"  NSG-Ventas)
NSG_T=$(nsg_de "$SUBNET_TI"      NSG-TI)
NSG_D=$(nsg_de "$SUBNET_DC"      NSG-DataCenter)
for X in "$NSG_V" "$NSG_S" "$NSG_T" "$NSG_D"; do
  [ -n "$X" ] || { echo "ERROR: una subred no tiene NSG asociado o el nombre en variables.env no existe. Correr 00_auditar.sh"; exit 1; }
done
echo "NSGs: Visitas=$NSG_V Ventas=$NSG_S TI=$NSG_T DC=$NSG_D"

# ---------------- VISITAS: Internet sí, subredes internas no ----------------
regla "$NSG_V" Allow-TI-In         100  Inbound  Allow '*' "$T"            "$V" '*'
regla "$NSG_V" Deny-VNet-In        4000 Inbound  Deny  '*' VirtualNetwork  "$V" '*'
regla "$NSG_V" Deny-Internas-Out   100  Outbound Deny  '*' "$V"  "$S $T $D $Z" '*'
# Internet: queda la regla por defecto AllowInternetOutBound (65001)

# ---------------- TI: llega a todo; nadie inicia hacia TI ----------------
regla "$NSG_T" Deny-Otras-A-TI     100  Inbound  Deny  '*' "$V $S $D $Z"  "$T" '*'

# ---------------- VENTAS ----------------
regla "$NSG_S" Allow-TI-In         100  Inbound  Allow '*' "$T"            "$S" '*'
regla "$NSG_S" Deny-Visitas-DMZ-In 110  Inbound  Deny  '*' "$V $Z"         "$S" '*'
regla "$NSG_S" Deny-TI-Out         100  Outbound Deny  '*' "$S"            "$T" '*'

# ---------------- DATA CENTER (DNS + Intranet) ----------------
# Reemplaza Allow-Ventas (cualquier puerto) por reglas de puerto específico
regla "$NSG_D" Allow-Ventas-DNS      101 Inbound Allow '*'   "$S" "$IP_DNS"      '53'
regla "$NSG_D" Allow-Ventas-Intranet 105 Inbound Allow Tcp   "$S" "$IP_INTRANET" '80 443'
regla "$NSG_D" Allow-TI              110 Inbound Allow '*'   "$T" "$D"           '*'
regla "$NSG_D" Allow-DC-Interno      120 Inbound Allow '*'   "$D" "$D"           '*'
regla "$NSG_D" Deny-Resto-VNet       200 Inbound Deny  '*'   VirtualNetwork "$D" '*'
regla "$NSG_D" Deny-TI-Out           100 Outbound Deny '*'   "$D" "$T"           '*'
borrar "$NSG_D" Allow-Ventas

# ---------------- DMZ ----------------
if [ "${DRY_RUN:-0}" = "1" ] || az network vnet subnet show -g "$RG" --vnet-name "$VNET" -n "$SUBNET_DMZ" -o none 2>/dev/null; then
  NSG_Z=$(nsg_de "$SUBNET_DMZ" "$NSG_DMZ")
  if [ -z "$NSG_Z" ]; then
    echo "== Creando $NSG_DMZ y asociándolo a $SUBNET_DMZ =="
    $AZ network nsg create -g "$RG" -n "$NSG_DMZ" -l "$REGION" -o none
    $AZ network vnet subnet update -g "$RG" --vnet-name "$VNET" -n "$SUBNET_DMZ" --network-security-group "$NSG_DMZ" -o none
    NSG_Z="$NSG_DMZ"
  fi
  regla "$NSG_Z" Allow-Web-Internet  100  Inbound  Allow Tcp Internet        "$Z" '80 443'
  regla "$NSG_Z" Allow-TI-Admin      110  Inbound  Allow '*' "$T"            "$Z" '*'
  [ -n "$ADMIN_IP_PUBLICA" ] && \
  regla "$NSG_Z" Allow-Admin-Externo 115  Inbound  Allow Tcp "$ADMIN_IP_PUBLICA" "$Z" '22'
  regla "$NSG_Z" Deny-VNet-In        4000 Inbound  Deny  '*' VirtualNetwork "$Z" '*'
  regla "$NSG_Z" Deny-Internas-Out   100  Outbound Deny  '*' "$Z" "$V $S $T $D" '*'
else
  NSG_Z=""
  echo "!! $SUBNET_DMZ no existe todavía: reglas de DMZ pendientes (esperar a Jose y volver a correr este script)."
fi

[ "${DRY_RUN:-0}" = "1" ] && { echo "(dry-run: nada se aplicó)"; exit 0; }
echo; echo "================ RESULTADO FINAL POR NSG ================"
for N in "$NSG_V" "$NSG_S" "$NSG_T" "$NSG_D" $NSG_Z; do
  echo; echo "## $N"
  az network nsg rule list -g "$RG" --nsg-name "$N" \
    --query "sort_by([],&priority)[].{Prio:priority,Dir:direction,Nombre:name,Acc:access,Prot:protocol,Origen:join(',',[sourceAddressPrefix,join(',',sourceAddressPrefixes)]),Destino:join(',',[destinationAddressPrefix,join(',',destinationAddressPrefixes)]),Puerto:join(',',[destinationPortRange,join(',',destinationPortRanges)])}" -o table
done
echo; echo "Log: $LOG   |   Siguiente: ./02_nat_mantenimiento.sh on  y  ./03_hardening.sh"
