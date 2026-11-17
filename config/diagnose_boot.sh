#!/usr/bin/env bash
# Diagnóstico de lectura para Run Command; no imprime claves ni credenciales.
set -u
echo '--- cloud-init output (last 65 lines)'
tail -n 65 /var/log/cloud-init-output.log
echo '--- bootstrap marker'
if test -f /var/lib/cafenube-ready; then echo READY; else echo NOT_READY; fi
echo '--- SSH syntax'
sshd -t
