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
| effective-nsg-association | PASS | {'nsg_ids': ['/subscriptions/c9467ad7-558e-42f5-8d3f-a0349dfc2ec8/resourcegroups/rg-cafenube/providers/microsoft.network/networksecuritygroups/nsg-dmz'], 'additional_admin_denies': ['securityRules/DefaultIPv6OutboundDeny']} |
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
| guest-cloud_init | PASS | {'exit_code': 0, 'stdout': 'status: done\nextended_status: done\nboot_status_code: enabled-by-generator\nlast_update: Thu, 01 Jan 1970 00:00:12 +0000\ndetail: DataSourceAzure [seed=/var/lib/waagent]\nerrors: []\nrecoverable_errors: {}\n', 'stderr': ''} |
| guest-nginx_config | PASS | {'exit_code': 0, 'stdout': '', 'stderr': 'nginx: the configuration file /etc/nginx/nginx.conf syntax is ok\nnginx: configuration file /etc/nginx/nginx.conf test is successful\n'} |
| guest-nginx_service | PASS | {'exit_code': 0, 'stdout': 'active\n', 'stderr': ''} |
| guest-http_loopback | PASS | {'exit_code': 0, 'stdout': 'cafenube-ok\n', 'stderr': ''} |
| guest-hardening | PASS | UFW, marcador de bootstrap y configuración efectiva de sshd |
| positive-controls | PENDING | Requiere VM-TI-1 activa y servicios privados sanos; un timeout desde DMZ no prueba aislamiento |
| dmz-isolation-dns_udp | INCONCLUSIVE | Falta control positivo sano, prueba guest o Deny efectivo; no atribuirlo a NSG |
| dmz-isolation-dns_tcp | INCONCLUSIVE | Falta control positivo sano, prueba guest o Deny efectivo; no atribuirlo a NSG |
| dmz-isolation-intranet_http | INCONCLUSIVE | Falta control positivo sano, prueba guest o Deny efectivo; no atribuirlo a NSG |
| browser-external-screenshot | PENDING | Abrir FQDN en navegador externo y guardar captura real con fecha/origen |
