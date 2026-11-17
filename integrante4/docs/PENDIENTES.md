# Pendientes para terminar el proyecto

## Parte de Nina

1. Acceder a la suscripción real y ejecutar el preflight de solo lectura. Actualmente no están comprobados recursos, IPs, FQDN ni reglas reales.
2. Acordar con José Ordóñez la DMZ y con José Antón el perfil de seguridad, incluidos defaults, salida y administración. Ajustar la regla 443 del informe si aún no hay TLS.
3. Revisar precios/crédito y aprobar tamaño, horas y presupuesto antes de crear PIP, disco y VM.
4. Desplegar desde Cloud Shell. Verificar cloud-init, Nginx, UFW y SSH en Ubuntu, que no se han ejecutado en una VM real durante la preparación local.
5. Ejecutar DNS público/HTTP desde una red externa, reglas efectivas y controles de aislamiento con los servidores internos activos. Guardar logs y capturas auténticas.
6. Confirmar con Adrián/José que no existe publicación directa ni indirecta del DNS privado y la Intranet.
7. Entregar datos reales y evidencias a Diego; completar tiempo real de trabajo.
8. Desasignar únicamente `VM-Web-Publica` y revisar cargos persistentes de disco/IP. Decidir con el dueño la ventana de demostración.

## Integración del equipo, fuera de esta implementación

| Responsable | Trabajo necesario para cerrar Fase 2 |
|---|---|
| José Ordóñez | Contrastar red real con diseño; DMZ sin traslapes y diagrama final |
| Adrián González | DNS interno e Intranet operativos; resolución de empleados; controles positivos; ausencia de publicación externa |
| José Antón | Matriz completa de NSGs: Visitantes, TI, Ventas, Data Center y DMZ; hardening y pruebas de todas las restricciones |
| Diego Ramírez | Integración reproducible, pruebas conjuntas, costos, informe actualizado, capturas y tabla Word de aportes/tiempos |
| Todos | Revisar datos reales, corregir contradicciones del informe y preparar evaluación individual |

No se puede declarar completado el escenario Cloud a partir de los scripts entregados. TLS es opcional y no bloquea la entrega base si se demuestra HTTP y el dominio público con aislamiento correcto.
