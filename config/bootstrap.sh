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
health=$(curl --fail --silent --show-error --retry 20 --retry-all-errors \
    --retry-delay 2 --retry-max-time 60 --max-time 5 http://127.0.0.1/healthz)
[[ "$health" == cafenube-ok ]] || { echo 'Respuesta de salud inesperada'; exit 1; }
printf 'cafenube-bootstrap-ok\n' > /var/lib/cafenube-ready
