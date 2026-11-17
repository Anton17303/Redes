# Estado y pendientes del proyecto

## Completado y probado el 17/11/2026

- Repositorio unificado por componentes, sin carpetas ni atribuciones personales en los entregables técnicos.
- Política de 18 reglas propias en cinco NSGs, con inventario posterior convergente y DMZ `10.0.0.144/28` asociada a `NSG-DMZ`.
- Web pública en Ubuntu/Nginx, IP privada `10.0.0.148`, IPv4 pública `40.116.80.26` y FQDN `cafenube-ventas-publica.northcentralus.cloudapp.azure.com`.
- DNS público, HTTP externo con contenido exacto, cabeceras, cloud-init, Nginx, UFW y SSH efectivo comprobados. Capturas reales de escritorio y móviles conservadas.
- Decisiones Allow/Deny de Azure comprobadas para administración, publicación y salidas de DMZ.
- VM pública desasignada al terminar, con `PowerState/deallocated` confirmado. Disco e IP se conservan y siguen siendo facturables.

Consultar [la evidencia final](../evidencias/DESPLIEGUE_AZURE_2026-11-17.md). El runner final conserva 36 PASS, 5 PENDING y 3 INCONCLUSIVE; la captura externa se completó por separado. No hay FAIL en esa ejecución.

## Para terminar el escenario completo

1. **DNS e Intranet:** implementar y activar los servidores privados previstos (`10.0.0.132` y `10.0.0.133`), zona/registro interno de RR. HH. y página estática. Configurar los clientes empleados para resolver mediante ese DNS. No existían `VM-DNS` ni `VM-Intranet` en el inventario final.
2. **Capacidad y clientes de prueba:** preparar TI y Visitas; `VM-TI-1` y `VM-Visitas-1` no existían. Las dos VMs de Ventas existentes estaban desasignadas. Se observó cuota regional de **6/6 vCPU** durante la prueba; revisar cuota y tamaños antes de crear más VMs, mediante reutilización o reducción planificada de recursos, o una ampliación admitida por la suscripción. Desasignar no debe asumirse equivalente a liberar cuota.
3. **Hardening y salida:** aplicar y verificar el hardening en todas las instancias restantes. Definir salida de mantenimiento y de Visitas a Internet; no se ha creado NAT Gateway. El script por sí solo no prueba hardening aplicado ni conectividad.
4. **Pruebas integrales:** DNS TCP/UDP y nombre interno desde empleados, HTTP de Intranet, administración desde TI, denegación hacia TI y desde Visitas/DMZ, y salida de Visitas a Internet. Repetir `02_pruebas.sh` y `06_pruebas_red.sh` con servicios sanos y controles positivos. Completar además la revisión de proxies/túneles/DNS público para demostrar que los servicios privados no se publican indirectamente.
5. **Reporte académico:** actualizar el documento de Fase 1 con el diagrama final, servicios, matriz NSG, resultados y capturas auténticas. Completar la tabla de Word de aportes y tiempos reales solicitada por la rúbrica como registro académico separado del código técnico. Preparar la explicación y demostración de protocolos, reglas y recuperación.

## Costos y próxima demostración

La web está **desasignada** y su URL no responde hasta iniciar la VM. Disco e IP conservados cuestan aproximadamente **USD 5.19 por 730 h**, más conceptos variables, con las tarifas consultadas. La protección de gasto `On` permaneció activada; no se cambió a pago por uso. Registrar una fecha de revisión de la conservación y comprobar crédito vigente antes de otra ventana de pruebas.

TLS es opcional: HTTP 80 cumple el escenario base de publicación; TCP 443 permanece cerrado. Consultar [costos](COSTOS_Y_CREDITOS.md), [informe](INFORME.md) y [seguridad](SEGURIDAD.md).
