#!/usr/bin/env bash
# DNS e Intranet privados; la NIC de Azure debe estar preparada previamente.
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Se requiere root'; exit 1; }
[[ -s /home/azureuser/.ssh/authorized_keys ]] || { echo 'Sin clave SSH existente'; exit 1; }
ip -4 address show | grep -q '10\.0\.0\.132/' || { echo 'No está asignada la IP privada DNS esperada'; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=3 update
apt-get -y -o Dpkg::Options::=--force-confold install bind9 bind9-utils dnsutils nginx ufw curl ca-certificates
install -m 0755 /opt/cafenube/private-ip.sh /usr/local/sbin/cafenube-private-ip
install -m 0644 /opt/cafenube/private-ip.service /etc/systemd/system/cafenube-private-ip.service
systemctl daemon-reload
systemctl enable --now cafenube-private-ip.service
named-checkconf
named-checkzone cafenube.internal /etc/bind/db.cafenube.internal
named-checkzone 0.0.10.in-addr.arpa /etc/bind/db.10.0.0
if [[ -L /etc/nginx/sites-enabled/default ]]; then
    unlink /etc/nginx/sites-enabled/default
fi
ln -sfn /etc/nginx/sites-available/cafenube-intranet /etc/nginx/sites-enabled/cafenube-intranet
nginx -t
bash /usr/local/sbin/cafenube-hardening servicios 0
systemctl enable --now named nginx
systemctl restart named
systemctl reload nginx
dig @10.0.0.132 rrhh.cafenube.internal A +short | grep -qx '10.0.0.133'
dig @10.0.0.132 rrhh.cafenube.internal A +tcp +short | grep -qx '10.0.0.133'
health=$(curl --fail --silent --show-error --retry 20 --retry-all-errors --retry-delay 2 --retry-max-time 60 --max-time 5 http://10.0.0.133/healthz)
[[ "$health" == cafenube-intranet-ok ]]
install -d /var/lib/cafenube
date -u +%FT%TZ > /var/lib/cafenube/private-ready
echo CAFENUBE_PRIVATE_READY
