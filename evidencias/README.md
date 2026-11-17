# Evidencias y criterios de aceptación

`VALIDACION_LOCAL.md` registra comprobaciones realmente ejecutadas en este equipo. Las capturas de `local-render/` muestran una instancia de prueba en loopback y **no** demuestran acceso público desde Azure.

[REVISION_AZURE_2026-11-17.md](REVISION_AZURE_2026-11-17.md) registra la inspección real posterior: preflight detenido por ausencia de NSG-DMZ y Subnet-DMZ. Los logs originales descargados se conservan en `azure/revision-real-20261117/` y en `azure/cafenube-preflight.tar.gz`, ignorados por Git. Los resultados del servicio público continúan pendientes.

Al ejecutar los scripts conectados a Azure, los inventarios, resultados y aprobaciones se guardan en `azure/<fecha-UTC>-<identificador>/`. Las capturas manuales pueden guardarse en `capturas/`. Ambas carpetas se ignoran en Git: revisar datos y elegir qué adjuntar al reporte, sin credenciales. Los fixtures offline se mantienen en temporales de prueba, separados de las evidencias reales.

## Estado de aceptación del escenario Azure

| Prueba | Resultado real actual | Evidencia requerida |
|---|---|---|
| FQDN resuelve a la PIP | PENDING | DNS sistema + resolvedores públicos |
| HTTP desde fuera de la VNet | PENDING |200, contenido esperado, origen externo declarado |
| Nginx/cloud-init sanos | PENDING | Configuración válida, servicio activo, marcador bootstrap y `/healthz` |
| Página visible en navegador externo | PENDING | Captura con URL real y fecha |
| DMZ no inicia hacia redes privadas | PENDING | Deny efectivo + probes DMZ + servicios sanos desde TI |
| SSH restringido a TI | PENDING | Allow/Deny de flujo, SSH guest y banner desde TI |
| DNS/Intranet no publicados | PENDING | NICs sin PIP, revisión de intermediarios y prueba externa conjunta |
| VM pública desasignada al terminar | PENDING | Estado `PowerState/deallocated` |

## Registro mínimo por prueba

Guardar fecha UTC, autor, origen real, destino real, comando, resultado esperado, resultado observado, regla efectiva cuando corresponda y nombre del archivo/captura. No incluir contraseñas, tokens ni claves privadas.

- `PASS`: observación coherente con todos los requisitos de esa prueba.
- `FAIL`: resultado contrario, como conexión inesperada a un servicio privado o contenido incorrecto.
- `PENDING`: no se ejecutó o depende de una pieza no disponible.
- `INCONCLUSIVE`: se ejecutó, pero no permite atribuir la causa o confirmar el requisito.

No escribir «bloqueado» solo por timeout, `connection refused`, servicio detenido o VM desasignada. Las pruebas de red del runner requieren una decisión Deny de Azure y controles positivos sanos. Un HTTP200 aislado tampoco prueba que se sirva el sitio correcto: se comparan hashes del HTML y del CSS.
