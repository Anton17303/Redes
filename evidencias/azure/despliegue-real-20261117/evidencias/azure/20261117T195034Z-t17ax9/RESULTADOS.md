# Resultados reales de Azure

| Prueba | Resultado | Detalle |
|---|---|---|
| configured-security | PASS | Perfil conservador NSG validado incluyendo reglas predeterminadas |
| private-VM-DNS | PENDING | No existe en el inventario de la suscripción |
| private-VM-Intranet | PENDING | No existe en el inventario de la suscripción |
| private-indirect-load-balancers | PASS | No hay recursos de este tipo en la suscripción |
| private-indirect-app-gateways | PASS | No hay recursos de este tipo en la suscripción |
| private-indirect-firewalls | PASS | No hay recursos de este tipo en la suscripción |
| private-publication-scope | PENDING | las áreas de servicios y seguridad deben confirmar ausencia de proxies/túneles/DNS público ajenos a este inventario y aportar prueba externa |
| dns-system | PASS | cafenube-ventas-publica.northcentralus.cloudapp.azure.com -> ['40.116.80.26']; esperado 40.116.80.26 |
| dns-public-1.1.1.1 | PASS | Respuesta pública guardada; cotejada con IP de Azure |
| dns-public-8.8.8.8 | PASS | Respuesta pública guardada; cotejada con IP de Azure |
| http/ | PASS | Esperado HTTP200 y contenido exacto; observado HTTP200, contenido_coincide=True; fuente: CloudShell-standard-outside-VNet |
| nginx-public-headers | PASS | Esperado Nginx sin versión y cabeceras de seguridad; coincide=True |
| http/styles.css | PASS | Esperado HTTP200 y contenido exacto; observado HTTP200, contenido_coincide=True; fuente: CloudShell-standard-outside-VNet |
| http/healthz | PASS | Esperado HTTP200 y contenido exacto; observado HTTP200, contenido_coincide=True; fuente: CloudShell-standard-outside-VNet |
| effective-nsg-association | FAIL | Reglas efectivas guardadas y NSG esperado único |
| ip-flow-http-internet | PASS | Esperado Allow; resultado {'access': 'Allow', 'ruleName': 'securityRules/Allow-Web-Internet'} |
| ip-flow-ssh-ti | PASS | Esperado Allow; resultado {'access': 'Allow', 'ruleName': 'securityRules/Allow-TI-Admin'} |
| ip-flow-internet-22 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-internet-443 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-internet-53 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-internet-3389 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-internet-dns-udp | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-visitas-in-22 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-visitas-in-80 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-ventas-in-22 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-ventas-in-80 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-dc-in-22 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-dc-in-80 | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-All-In'} |
| ip-flow-dmz-to-ventas | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-Internas-Out'} |
| ip-flow-dmz-to-ti | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-Internas-Out'} |
| ip-flow-dmz-to-dns-tcp | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-Internas-Out'} |
| ip-flow-dmz-to-dns-udp | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-Internas-Out'} |
| ip-flow-dmz-to-intranet | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-Internas-Out'} |
| ip-flow-dmz-to-visitas | PASS | Esperado Deny; resultado {'access': 'Deny', 'ruleName': 'securityRules/Deny-Internas-Out'} |
| guest-cloud_init | FAIL | {'exit_code': 1, 'stdout': "status: error\nextended_status: error - done\nboot_status_code: enabled-by-generator\nlast_update: Thu, 01 Jan 1970 00:03:00 +0000\ndetail: DataSourceAzure [seed=/dev/sr0]\nerrors:\n\t- ('scripts_user', RuntimeError('Runparts: 1 failures (runcmd) in 1 attempted commands'))\nrecoverable_errors:\nWARNING:\n\t- Failed to run module scripts_user (scripts in /var/lib/cloud/instance/scripts)\n\t- Running module scripts_user (<module 'cloudinit.config.cc_scripts_user' from '/usr/lib/python3/dist-packages/cloudinit/config/cc_scripts_user.py'>) failed\n", 'stderr': ''} |
| guest-nginx_config | PASS | {'exit_code': 0, 'stdout': '', 'stderr': 'nginx: the configuration file /etc/nginx/nginx.conf syntax is ok\nnginx: configuration file /etc/nginx/nginx.conf test is successful\n'} |
| guest-nginx_service | PASS | {'exit_code': 0, 'stdout': 'active\n', 'stderr': ''} |
| guest-http_loopback | PASS | {'exit_code': 0, 'stdout': 'cafenube-ok\n', 'stderr': ''} |
| guest-hardening | FAIL | UFW, marcador de bootstrap y configuración efectiva de sshd |
| positive-controls | PENDING | Requiere VM-TI-1 activa y servicios privados sanos; un timeout desde DMZ no prueba aislamiento |
| dmz-isolation-dns_udp | INCONCLUSIVE | Falta control positivo sano, prueba guest o Deny efectivo; no atribuirlo a NSG |
| dmz-isolation-dns_tcp | INCONCLUSIVE | Falta control positivo sano, prueba guest o Deny efectivo; no atribuirlo a NSG |
| dmz-isolation-intranet_http | INCONCLUSIVE | Falta control positivo sano, prueba guest o Deny efectivo; no atribuirlo a NSG |
| browser-external-screenshot | PENDING | Abrir FQDN en navegador externo y guardar captura real con fecha/origen |
