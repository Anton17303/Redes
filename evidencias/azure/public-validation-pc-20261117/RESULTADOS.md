# Resultados reales de Azure

| Prueba | Resultado | Detalle |
|---|---|---|
| dns-system | PASS | cafenube-ventas-publica.northcentralus.cloudapp.azure.com -> ['40.116.80.26']; esperado 40.116.80.26 |
| dns-public-1.1.1.1 | INCONCLUSIVE | [WinError 2] El sistema no puede encontrar el archivo especificado |
| dns-public-8.8.8.8 | INCONCLUSIVE | [WinError 2] El sistema no puede encontrar el archivo especificado |
| http/ | PASS | Esperado HTTP200 y contenido exacto; observado HTTP200, contenido_coincide=True; fuente: Local computer, direct HTTP, outside project VNet |
| nginx-public-headers | PASS | Esperado Nginx sin versión y cabeceras de seguridad; coincide=True |
| http/styles.css | PASS | Esperado HTTP200 y contenido exacto; observado HTTP200, contenido_coincide=True; fuente: Local computer, direct HTTP, outside project VNet |
| http/healthz | PASS | Esperado HTTP200 y contenido exacto; observado HTTP200, contenido_coincide=True; fuente: Local computer, direct HTTP, outside project VNet |
