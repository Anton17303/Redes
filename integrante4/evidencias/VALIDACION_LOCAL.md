# Validación local ejecutada

Fecha: **17 de noviembre de 2026**, zona del trabajo: America/Guatemala. Alcance: archivos de `integrante4/`, Bash de Git para Windows, Python3, Nginx oficial para Windows y Chromium de prueba aislado.

**Azure: PENDING.** No se inspeccionó la suscripción ni se desplegaron recursos. Azure CLI no está instalada/autenticada en el entorno y el acceso automatizado al Chrome abierto se detuvo porque no pudo comprobar su URL. No se generaron IPs/FQDN ni se atribuyeron éxitos de red a Azure.

| Comprobación realmente ejecutada | Resultado |
|---|---|
| 21 pruebas `unittest`, incluyendo subcasos de seguridad | PASS, registro en `pruebas-locales.txt` |
| Plan por defecto sin mutaciones, aprobación de costo obligatoria | PASS contra CLI ficticia aislada |
| Aplicar y repetir sin duplicar PIP/NIC/VM | PASS contra CLI ficticia aislada |
| SSH público, 443 sin TLS y excepciones hacia redes privadas | Rechazados por el validador |
| Recursos ajenos, conflicto de IP, cuota insuficiente, disco huérfano | Rechazados por el validador |
| Error RBAC y clave pública inválida | Detienen la creación antes de mutaciones cobrables |
| Desasignación de la VM propia; rechazo de la ajena | PASS contra CLI ficticia aislada |
| Run Command «succeeded» sin resultado del guest | Se registra INCONCLUSIVE, nunca PASS |
| Sintaxis de los 6 archivos Bash | PASS con `bash -n` |
| Compilación de módulos Python | PASS con `compileall` |
| Generación determinista de cloud-config y correspondencia exacta con fuentes | PASS |
| Parseo independiente de YAML | PASS: 5 archivos, 10476 bytes, por debajo de 64 KiB |
| `nginx -t` con configuración entregada, cambiando solo puerto/root para loopback | PASS en Nginx 1.28.0 para Windows |
| `/`, `/styles.css`, `/healthz` | HTTP 200; HTML/CSS exactos y marcador de salud correcto |
| Ruta inexistente y archivo oculto | 404 y 403, respectivamente |
| Server sin versión, nosniff, X-Frame-Options y CSP | PASS en respuestas locales |
| Chromium: 1440×1000, 390×844 y 320×740 | Sin desborde horizontal; navegación/idioma/texto comprobados |
| Capturas locales de escritorio y móviles | Generadas en `local-render/` y revisadas visualmente |
| Revisión de whitespace y búsqueda de claves privadas/tokens en entregables | Sin hallazgos |

Los recursos, IDs y respuestas del mock son datos sintéticos contenidos en `tests/`; sus salidas no se presentan como inventario de Azure. El monto usado en pruebas automáticas es ficticio y no autoriza gasto real.

La validación de Nginx en Windows confirma la configuración HTTP y el contenido local. **No valida** arranque en Ubuntu, instalación de paquetes, cloud-init en Azure, UFW real, SSH del guest ni reglas efectivas. Esos puntos se ejecutan con `02_pruebas.sh` después del despliegue aprobado.

Las capturas locales y resultados web detallados permanecen en `local-render/`, ignorado por Git. No sustituyen las capturas externas requeridas para el informe. Consultar [README de evidencias](README.md) y [pendientes del proyecto](../docs/PENDIENTES.md).
