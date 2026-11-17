#!/usr/bin/env bash
# Se ejecuta como root al final de cloud-init, después de instalar paquetes.
set -euo pipefail
rm -f /etc/nginx/sites-enabled/default
ln -sfn /etc/nginx/sites-available/cafenube /etc/nginx/sites-enabled/cafenube
chmod 0755 /var/www/cafenube
nginx -t

# La VM nace en una subred ya protegida: no se cambian NSGs compartidos.
ufw default deny incoming
ufw default allow outgoing
ufw allow from 10.0.0.96/27 to any port 22 proto tcp
ufw allow from 10.0.0.96/27 to any port 80 proto tcp
ufw deny from 10.0.0.0/16
ufw allow 80/tcp
ufw deny out to 10.0.0.0/8
ufw deny out to 172.16.0.0/12
ufw deny out to 192.168.0.0/16
ufw --force enable
sshd -t
systemctl reload ssh
systemctl enable --now nginx
systemctl reload nginx
curl --fail --silent --show-error http://127.0.0.1/healthz
printf 'cafenube-bootstrap-ok\n' > /var/lib/cafenube-ready
