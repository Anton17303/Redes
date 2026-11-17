# Evidencias y criterios de aceptación

`VALIDACION_LOCAL.md` registra comprobaciones realmente ejecutadas en este equipo. Las capturas de `local-render/` muestran una instancia de prueba en loopback y **no** demuestran acceso público desde Azure.

[DESPLIEGUE_AZURE_2026-11-17.md](DESPLIEGUE_AZURE_2026-11-17.md) registra la aplicación de seguridad, el despliegue y las pruebas finales. Las revisiones anteriores conservan el estado histórico previo a la DMZ. Los inventarios completos, registros y archivos descargados permanecen en `azure/`, ignorados por Git. El resumen público y las capturas seleccionadas se entregan por separado.

Al ejecutar los scripts conectados a Azure, los inventarios, resultados y aprobaciones se guardan en `azure/<fecha-UTC>-<identificador>/`. Las capturas manuales pueden guardarse en `capturas/`. Ambas carpetas se ignoran en Git: revisar datos y elegir qué adjuntar al reporte, sin credenciales. Los fixtures offline se mantienen en temporales de prueba, separados de las evidencias reales.

Las tres capturas externas seleccionadas y su manifiesto revisado se incluyen en [publicas/](publicas/). No contienen datos de la cuenta ni imágenes del portal.

## Estado de aceptación del escenario Azure

| Prueba | Resultado real actual | Evidencia requerida |
|---|---|---|
| FQDN resuelve a la PIP | PASS | DNS sistema, 1.1.1.1 y 8.8.8.8 |
| HTTP desde fuera de la VNet | PASS | 200, contenido exacto; Cloud Shell externo y equipo local |
| Nginx/cloud-init sanos | PASS | Guest real después del reinicio; `done`, servicio activo, marcador y salud |
| Página visible en navegador externo | PASS por evidencia adicional | Capturas reales y manifiesto con URL, fecha, origen y hashes |
| DMZ no inicia hacia redes privadas | INCONCLUSIVE funcional | Deny efectivo PASS; faltan servicios sanos y control desde TI |
| SSH restringido a TI | PASS de reglas/guest; prueba práctica PENDING | Allow/Deny y SSH efectivo confirmados; falta cliente TI |
| DNS/Intranet no publicados | PENDING | VMs ausentes; revisión completa de intermediarios y prueba conjunta pendiente |
| VM pública desasignada al terminar | PASS | Respuesta real `PowerState/deallocated` |

## Registro mínimo por prueba

Guardar fecha UTC, autor, origen real, destino real, comando, resultado esperado, resultado observado, regla efectiva cuando corresponda y nombre del archivo/captura. No incluir contraseñas, tokens ni claves privadas.

- `PASS`: observación coherente con todos los requisitos de esa prueba.
- `FAIL`: resultado contrario, como conexión inesperada a un servicio privado o contenido incorrecto.
- `PENDING`: no se ejecutó o depende de una pieza no disponible.
- `INCONCLUSIVE`: se ejecutó, pero no permite atribuir la causa o confirmar el requisito.

No escribir «bloqueado» solo por timeout, `connection refused`, servicio detenido o VM desasignada. Las pruebas de red del runner requieren una decisión Deny de Azure y controles positivos sanos. Un HTTP200 aislado tampoco prueba que se sirva el sitio correcto: se comparan hashes del HTML y del CSS.
