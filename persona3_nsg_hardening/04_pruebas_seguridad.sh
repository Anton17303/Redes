#!/usr/bin/env bash
# =====================================================================
# Paso 4: matriz de pruebas de acceso (permitido / bloqueado).
# Correr DESPUÉS de 01 y 03, con las VMs encendidas.
# Un BLOQUEADO solo vale si el control PERMITIDO desde TI al mismo
# destino dio OPEN (así sabemos que el servicio está arriba y lo que
# lo corta es el NSG, no un servicio apagado).
# =====================================================================
set -uo pipefail
cd "$(dirname "$0")"; source ./variables.env
mkdir -p evidencias
FECHA=$(date +%Y%m%d_%H%M)
CSV="evidencias/04_resultados_${FECHA}.csv"
echo "fecha,origen,destino,esperado,obtenido,resultado" > "$CSV"
OK=0; MAL=0

ip() { az vm show -d -g "$RG" -n "$1" --query privateIps -o tsv 2>/dev/null; }
IPV=$(ip "$VM_VENTAS"); IPT=$(ip "$VM_TI"); IPVIS=$(ip "$VM_VISITAS"); IPW=$(ip "$VM_WEB")
echo "IPs -> Ventas=$IPV TI=$IPT Visitas=$IPVIS DMZ-web=${IPW:-no existe} DNS=$IP_DNS Intranet=$IP_INTRANET"

registrar() { # origen destino esperado obtenido
  local exp="$3" got="$4" res
  [ "$exp" = PERMITIDO ] && exp_n=OPEN || exp_n=CLOSED
  [ "$got" = "$exp_n" ] && { res=PASS; OK=$((OK+1)); } || { res=FAIL; MAL=$((MAL+1)); }
  printf '%-4s %-13s -> %-26s esperado=%-9s obtenido=%s\n' "$res" "$1" "$2" "$3" "$4"
  echo "$(date '+%F %H:%M'),$1,$2,$3,$4,$res" >> "$CSV"
}

read -r -d '' REMOTO <<'SCRIPT'
for t in __LISTA__; do
  h=${t%%:*}; p=${t#*:}
  if [ "$p" = icmp ]; then ping -c1 -W3 "$h" >/dev/null 2>&1 && e=OPEN || e=CLOSED
  else timeout 5 bash -c "</dev/tcp/$h/$p" 2>/dev/null && e=OPEN || e=CLOSED; fi
  echo "RES $h:$p $e"
done
SCRIPT

desde() { # desde <vm> host:puerto:ESPERADO ...   (puerto = número o icmp)
  local vm="$1"; shift
  if ! az vm show -g "$RG" -n "$vm" -o none 2>/dev/null; then echo "SKIP $vm no existe"; return; fi
  local lista="" s; for s in "$@"; do lista+="${s%:*} "; done
  echo "--- desde $vm"
  local salida; salida=$(az vm run-command invoke -g "$RG" -n "$vm" --command-id RunShellScript \
        --scripts "${REMOTO/__LISTA__/$lista}" --query "value[0].message" -o tsv)
  for s in "$@"; do
    local hp="${s%:*}" exp="${s##*:}" got
    got=$(grep -m1 "RES ${hp} " <<<"$salida" | awk '{print $3}'); got=${got:-SIN_DATO}
    registrar "$vm" "$hp" "$exp" "$got"
  done
}

# ---- Controles: TI alcanza todo (prueba "Acceso TI") ----
desde "$VM_TI" "$IPV:22:PERMITIDO" "$IPV:icmp:PERMITIDO" "$IPVIS:22:PERMITIDO" \
  "$IP_DNS:53:PERMITIDO" "$IP_DNS:22:PERMITIDO" "$IP_INTRANET:80:PERMITIDO" \
  ${IPW:+"$IPW:22:PERMITIDO" "$IPW:80:PERMITIDO"}

# ---- Visitas: Internet sí, interno no ----
desde "$VM_VISITAS" "www.google.com:443:PERMITIDO" \
  "$IP_DNS:53:BLOQUEADO" "$IP_INTRANET:80:BLOQUEADO" "$IPT:22:BLOQUEADO" "$IPT:icmp:BLOQUEADO" \
  "$IPV:22:BLOQUEADO" ${IPW:+"$IPW:80:BLOQUEADO"}

# ---- Ventas: Intranet/DNS sí, TI no ----
desde "$VM_VENTAS" "$IP_INTRANET:80:PERMITIDO" "$IP_DNS:53:PERMITIDO" \
  "$IP_DNS:22:BLOQUEADO" "$IPT:22:BLOQUEADO" "$IPT:icmp:BLOQUEADO"

# ---- Data Center: no inicia hacia TI ----
desde "$VM_DNS" "$IP_INTRANET:80:PERMITIDO" "$IPT:22:BLOQUEADO" "$IPT:icmp:BLOQUEADO"

# ---- DMZ: no inicia hacia lo interno ----
[ -n "$IPW" ] && desde "$VM_WEB" "www.google.com:443:PERMITIDO" \
  "$IPV:22:BLOQUEADO" "$IPT:22:BLOQUEADO" "$IP_DNS:53:BLOQUEADO" "$IP_INTRANET:80:BLOQUEADO" "$IPVIS:22:BLOQUEADO"

# ---- Desde Internet (esta computadora, fuera de Azure) ----
PUB=$(az vm show -d -g "$RG" -n "$VM_WEB" --query publicIps -o tsv 2>/dev/null)
echo "--- desde Internet (esta PC)"
if [ -n "$PUB" ]; then
  for pt in 80:PERMITIDO 443:PERMITIDO 22:BLOQUEADO 3389:BLOQUEADO; do
    p="${pt%%:*}"; e="${pt##*:}"
    (timeout 5 bash -c "</dev/tcp/$PUB/$p") 2>/dev/null && g=OPEN || g=CLOSED
    registrar "internet" "$PUB:$p" "$e" "$g"
  done
  echo "HTTP del sitio público: $(curl -s -o /dev/null -m 8 -w '%{http_code}' "http://$PUB/")"
else
  echo "SKIP: la VM de la DMZ no tiene IP pública todavía (Nina)"
fi
echo "--- VMs con IP pública (solo debe aparecer la de la DMZ)"
az vm list -g "$RG" -d --query "[?publicIps!=''].{VM:name,IP:publicIps}" -o table
for V in $VM_DNS $VM_INTRANET $VM_VENTAS $VM_TI $VM_VISITAS; do
  P=$(az vm show -d -g "$RG" -n "$V" --query publicIps -o tsv 2>/dev/null)
  [ -n "$P" ] && { echo "FAIL $V tiene IP pública $P"; MAL=$((MAL+1)); }
done

echo; echo "RESUMEN: $OK PASS, $MAL FAIL  -> $CSV"
echo "Los FAIL son la lista de correcciones para el reporte (causa + arreglo)."
