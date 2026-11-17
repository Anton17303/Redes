#!/usr/bin/env bash
# Se ejecuta como root al final de cloud-init, después de instalar paquetes.
set -euo pipefail
rm -f /etc/nginx/sites-enabled/default
ln -sfn /etc/nginx/sites-available/cafenube /etc/nginx/sites-enabled/cafenube
chmod 0755 /var/www/cafenube
nginx -t

# La misma política por rol se usa en cloud-init y mantenimiento.
bash /usr/local/sbin/cafenube-hardening web 0
systemctl enable --now nginx
systemctl reload nginx
curl --fail --silent --show-error http://127.0.0.1/healthz
printf 'cafenube-bootstrap-ok\n' > /var/lib/cafenube-ready
