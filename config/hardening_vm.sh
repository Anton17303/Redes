#!/usr/bin/env bash
# Hardening Ubuntu por rol, ejecutado mediante Run Command o cloud-init.
set -euo pipefail
ROLE="${1:-}"
UPDATE_PACKAGES="${2:-0}"
[[ $(id -u) == 0 ]] || { echo 'Se requiere root'; exit 1; }
case "$ROLE" in dns|intranet|cliente|visitas|web) ;; *) echo 'Rol inválido'; exit 1;; esac
[[ "$UPDATE_PACKAGES" == 0 || "$UPDATE_PACKAGES" == 1 ]] || exit 1
[[ -s /home/azureuser/.ssh/authorized_keys ]] || { echo 'Sin clave autorizada; se detiene antes de cambiar SSH'; exit 1; }
if [[ "$UPDATE_PACKAGES" == 1 ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get -y -o Dpkg::Options::=--force-confold upgrade
    apt-get -y install unattended-upgrades ufw
fi
command -v ufw >/dev/null || { echo 'Falta UFW; preparar salida y aprobar actualizaciones'; exit 1; }
# El contenido SSH es embebido por el runner desde la fuente única.
[[ -f /etc/ssh/sshd_config.d/00-cafenube.conf ]] || { echo 'Falta configuración SSH revisada'; exit 1; }
sshd -t
systemctl reload ssh
for service in avahi-daemon cups cups-browsed rpcbind snmpd ModemManager; do
    if systemctl list-unit-files "$service.service" --no-legend 2>/dev/null | grep -q "^$service.service"; then
        systemctl disable --now "$service.service"
    fi
done
cat > /etc/sysctl.d/99-cafenube-hardening.conf <<'CFG'
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.tcp_syncookies = 1
net.ipv6.conf.all.accept_redirects = 0
CFG
sysctl -p /etc/sysctl.d/99-cafenube-hardening.conf
# Se añaden restricciones sin resetear reglas existentes ni abrir SSH público.
ufw default deny incoming
ufw default allow outgoing
ufw allow from 10.0.0.96/27 to any port 22 proto tcp
case "$ROLE" in
    dns)
        for network in 10.0.0.64/27 10.0.0.96/27 10.0.0.128/28; do
            ufw allow from "$network" to any port 53 proto tcp
            ufw allow from "$network" to any port 53 proto udp
        done ;;
    intranet)
        for network in 10.0.0.64/27 10.0.0.96/27 10.0.0.128/28; do
            ufw allow from "$network" to any port 80 proto tcp
        done ;;
    web)
        ufw allow from 10.0.0.96/27 to any port 80 proto tcp
        ufw deny from 10.0.0.0/16
        ufw allow 80/tcp
        ufw deny out to 10.0.0.0/8
        ufw deny out to 172.16.0.0/12
        ufw deny out to 192.168.0.0/16 ;;
esac
ufw logging low
ufw --force enable
if systemctl list-unit-files unattended-upgrades.service --no-legend | grep -q '^unattended-upgrades.service'; then
    systemctl enable --now unattended-upgrades
fi
ufw status verbose
sshd -T | grep -E '^(passwordauthentication|permitrootlogin|maxauthtries|allowusers|x11forwarding) '
[[ ! -f /var/run/reboot-required ]] || echo 'Reinicio pendiente; no se reinicia automáticamente'
echo 'CAFENUBE_HARDENING_OK'
