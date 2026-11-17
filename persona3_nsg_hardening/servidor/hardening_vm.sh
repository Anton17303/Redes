#!/usr/bin/env bash
# =====================================================================
# Hardening básico de UNA VM Ubuntu 22.04. Corre DENTRO de la VM (root)
# mandado por 03_hardening.sh con "az vm run-command" (no usa SSH).
# Uso: hardening_vm.sh <rol> <RED_TI> <ADMIN_IP|-> <usuario> <redes_empleados,separadas,por,coma>
# Roles: dns | intranet | cliente | visitas | web
# =====================================================================
set -uo pipefail
ROL="${1:-cliente}"; RED_TI="${2:-10.0.0.96/27}"; ADMIN_IP="${3:--}"
USUARIO="${4:-azureuser}"; NETS="${5:-10.0.0.64/27,10.0.0.96/27,10.0.0.128/28}"
export DEBIAN_FRONTEND=noninteractive
echo "##### HARDENING $(hostname) rol=$ROL $(date '+%F %H:%M')"

echo "[1/6] Actualizaciones"
if curl -s -o /dev/null --max-time 8 http://azure.archive.ubuntu.com || curl -s -o /dev/null --max-time 8 http://archive.ubuntu.com; then
  apt-get update -qq && apt-get -y -qq -o Dpkg::Options::=--force-confold upgrade
  apt-get -y -qq install unattended-upgrades ufw >/dev/null
  systemctl enable --now unattended-upgrades >/dev/null 2>&1
  echo "  actualizado; pendientes: $(apt list --upgradable 2>/dev/null | grep -vc Listing)"
  [ -f /var/run/reboot-required ] && echo "  AVISO: requiere reinicio (reiniciar al terminar)"
else
  echo "  SIN SALIDA A INTERNET: se omiten actualizaciones (correr ./02_nat_mantenimiento.sh on)"
fi

echo "[2/6] SSH"
mkdir -p /etc/ssh/sshd_config.d
{
  echo "# CaféNube hardening (00- para ganar sobre 50-cloud-init.conf: sshd toma el primer valor)"
  if [ -s "/home/$USUARIO/.ssh/authorized_keys" ]; then echo "PasswordAuthentication no"
  else echo "# sin llave en /home/$USUARIO/.ssh: se deja la contraseña para no bloquear el acceso"; fi
  cat <<CFG
PermitRootLogin no
PubkeyAuthentication yes
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers $USUARIO
CFG
} > /etc/ssh/sshd_config.d/00-cafenube-hardening.conf
if sshd -t; then systemctl reload ssh 2>/dev/null || systemctl reload sshd; echo "  sshd recargado"
else echo "  ERROR en sshd_config, se revierte"; rm -f /etc/ssh/sshd_config.d/00-cafenube-hardening.conf; fi

echo "[3/6] Servicios innecesarios"
for s in avahi-daemon cups cups-browsed rpcbind snmpd ModemManager; do
  if systemctl list-unit-files "$s.service" 2>/dev/null | grep -q "$s"; then
    systemctl disable --now "$s" >/dev/null 2>&1 && echo "  deshabilitado: $s"
  fi
done

echo "[4/6] Parámetros de red (sysctl)"
cat > /etc/sysctl.d/99-cafenube-hardening.conf <<CFG
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.tcp_syncookies = 1
net.ipv6.conf.all.accept_redirects = 0
CFG
sysctl --system >/dev/null 2>&1

echo "[5/6] Firewall local (ufw) - segunda capa además del NSG"
ufw --force reset >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow from "$RED_TI" to any port 22 proto tcp comment 'SSH solo desde TI' >/dev/null
[ "$ADMIN_IP" != "-" ] && ufw allow from "$ADMIN_IP" to any port 22 proto tcp comment 'SSH admin externo' >/dev/null
IFS=',' read -ra REDES <<< "$NETS"
case "$ROL" in
  dns)      for r in "${REDES[@]}"; do ufw allow from "$r" to any port 53 comment 'DNS empleados' >/dev/null; done ;;
  intranet) for r in "${REDES[@]}"; do ufw allow from "$r" to any port 80 proto tcp comment 'Intranet empleados' >/dev/null; done ;;
  web)      ufw allow 80/tcp comment 'Web publica' >/dev/null; ufw allow 443/tcp comment 'Web publica TLS' >/dev/null ;;
  *)        : ;;   # cliente / visitas: solo SSH desde TI
esac
ufw logging low >/dev/null
ufw --force enable >/dev/null
ufw status numbered

echo "[6/6] Resultado"
echo "--- Puertos en escucha"; ss -lntup | awk 'NR==1 || /LISTEN|UNCONN/ {print $1,$5,$7}' | column -t
echo "--- sshd efectivo"; sshd -T 2>/dev/null | grep -E '^(passwordauthentication|permitrootlogin|maxauthtries|allowusers|x11forwarding) '
echo "##### FIN $(hostname)"
