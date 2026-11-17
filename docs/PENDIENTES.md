# Estado y pendientes del proyecto

## Implementación disponible

- Sitio estático público, Nginx HTTP 80 y cloud-init generado desde fuentes únicas.
- Auditoría y reconciliación segura de NSGs y DMZ.
- Hardening Ubuntu compartido por roles, sin NAT automático.
- Pruebas de publicación pública, aislamiento y matriz TCP entre segmentos.
- Controles de propiedad, idempotencia, crédito y protección de gasto.

## Comprobaciones pendientes en Azure

1. Completar el plan de seguridad contra el inventario real, resolver diferencias y aplicar la política/DMZ. La revisión inicial encontró ausentes `Subnet-DMZ` y `NSG-DMZ`; esa revisión histórica no describe automáticamente el estado posterior.
2. Confirmar SKU/cuota, nombre DNS, saldo vigente, horas y presupuesto antes de crear VM/PIP/disco. La protección `spendingLimit: On` fue observada en Cloud Shell durante la revisión de integración; el despliegue vuelve a consultarla.
3. Desplegar y verificar Ubuntu, cloud-init, Nginx, UFW, SSH y el dominio público. Registrar únicamente IP/FQDN realmente devueltos por Azure.
4. Tener DNS, Intranet y clientes de TI/Visitas activos y correctamente configurados para los controles positivos. No se declaran implementados a partir del paquete de seguridad.
5. Ejecutar DNS TCP/UDP, resolución de empleados, HTTP interno/externo, administración restringida, aislamiento y salida de Visitas a Internet. Completar los resultados pendientes/inconclusos.
6. Auditar publicación indirecta del DNS/Intranet, obtener capturas externas y cerrar el informe con datos comprobados.
7. Desasignar la VM pública tras las pruebas y decidir la conservación de disco/IP con seguimiento del consumo.

## Entrega formal

Consolidar diagrama, matriz NSG, configuración de servicios, resultados reales, costos y capturas. El registro académico de aportes y tiempos reales se completa por separado si la rúbrica lo solicita; no se inventan horas ni se incluyen atribuciones personales en el código técnico.

Consultar [INFORME.md](INFORME.md), [SEGURIDAD.md](SEGURIDAD.md) y [los resultados previos](../evidencias/REVISION_AZURE_2026-11-17.md). TLS es opcional y no bloquea el escenario base con HTTP y aislamiento demostrados.
