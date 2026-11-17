# Pendientes para terminar el proyecto

## Parte de Nina

1. Resolver los bloqueos comprobados en Azure: faltan `Subnet-DMZ` y `NSG-DMZ`. El preflight ya se ejecutó en la suscripción real y se detuvo con `ResourceNotFound`, sin crear recursos. Ver [registro de revisión](../evidencias/REVISION_AZURE_2026-11-17.md).
2. Acordar la creación de la DMZ con José Ordóñez y las reglas/asociación del NSG con José Antón, incluidos defaults, salida y administración. Ajustar la regla 443 del informe si aún no hay TLS. Repetir el preflight después de integrar esas dependencias.
3. Revisar precios/crédito y aprobar tamaño, horas y presupuesto antes de crear PIP, disco y VM.
4. Desplegar desde Cloud Shell. Verificar cloud-init, Nginx, UFW y SSH en Ubuntu, que no se han ejecutado en una VM real durante la preparación local.
5. Ejecutar DNS público/HTTP desde una red externa, reglas efectivas y controles de aislamiento con los servidores internos activos. Guardar logs y capturas auténticas.
6. Confirmar con Adrián/José que no existe publicación directa ni indirecta del DNS privado y la Intranet.
7. Entregar datos reales y evidencias a Diego; completar tiempo real de trabajo.
8. Desasignar únicamente `VM-Web-Publica` y revisar cargos persistentes de disco/IP. Decidir con el dueño la ventana de demostración.

## Integración del equipo, fuera de esta implementación

| Responsable | Trabajo necesario para cerrar Fase 2 |
|---|---|
| José Ordóñez | Incorporar la DMZ, ausente en la revisión real, sin traslapes; actualizar el diagrama |
| Adrián González | DNS interno e Intranet operativos; resolución de empleados; controles positivos; ausencia de publicación externa |
| José Antón | Incorporar NSG-DMZ y asociarlo; completar matriz, hardening y pruebas de las restricciones |
| Diego Ramírez | Integración reproducible, pruebas conjuntas, costos, informe actualizado, capturas y tabla Word de aportes/tiempos |
| Todos | Revisar datos reales, corregir contradicciones del informe y preparar evaluación individual |

No se puede declarar completado el escenario Cloud a partir de los scripts entregados. TLS es opcional y no bloquea la entrega base si se demuestra HTTP y el dominio público con aislamiento correcto.
