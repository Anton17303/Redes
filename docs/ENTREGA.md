# Entrega técnica unificada

Rama publicada: **`ProyectoFinal-FASE2`**. No se modificó `main` ni se creó un Pull Request. Las atribuciones de carpetas y documentos se sustituyeron por componentes técnicos; el historial Git original se conservó. Los commits de implementación de esta entrega usan mensajes en inglés.

## Archivos y funcionalidades

| Ruta | Función |
|---|---|
| `web/index.html`, `web/styles.css` | Página pública adaptable de CaféNube |
| `config/cloud-init.base.json`, `scripts/render_cloud_init.py` | Generación sincronizada de seis archivos UTF-8 para Ubuntu |
| `config/nginx_cafenube.conf`, `config/bootstrap.sh` | Nginx HTTP 80, cabeceras y salud con reintentos |
| `config/hardening_vm.sh`, `config/ssh_hardening.conf` | UFW, SSH por clave y parámetros de Ubuntu según rol |
| `config/matriz_nsg.csv`, `scripts/security_policy.py` | Catálogo de 18 reglas y reconciliación verificada de cinco NSGs |
| `scripts/00_preflight.sh`, `01_desplegar_web.sh`, `03_apagar.sh` | Inventario, controles previos, despliegue idempotente y desasignación propia |
| `scripts/check_credit_guard.py`, `validate_azure.py`, `azure_snapshot.py` | Crédito, protección de gasto, propiedad, cuota y consultas ARM |
| `scripts/02_pruebas.sh`, `06_pruebas_red.sh` | Publicación, guest, reglas efectivas y matriz de conectividad |
| `scripts/05_hardening.sh`, `hardening.py` | Plan/aplicación deliberada de hardening por VM activa |
| `config/diagnose_boot.sh`, `scripts/repair_web.py` | Diagnóstico y recuperación controlada de las fuentes web |
| `tests/` | 38 pruebas locales, inventario sintético claramente separado |
| `evidencias/` | Resultado real resumido, validación local y capturas públicas revisadas |

## Material para el reporte

Entregar [INFORME.md](INFORME.md), [SEGURIDAD.md](SEGURIDAD.md), [COSTOS_Y_CREDITOS.md](COSTOS_Y_CREDITOS.md), la matriz CSV y las configuraciones usadas. Incorporar [la validación real](../evidencias/DESPLIEGUE_AZURE_2026-11-17.md), [los resultados JSON](../evidencias/resultados-azure-20261117.json) y [las capturas públicas](../evidencias/publicas/). Estos materiales sirven para actualizar el documento académico de Fase 1; no sustituyen la integración final de sus secciones ni la tabla de tiempos reales exigida por la rúbrica.

El paquete `build/cafenube-fase2.zip` contiene las fuentes de la rama y las evidencias públicas seleccionadas. Los registros originales de Azure, la revisión financiera y la clave SSH privada permanecen fuera del ZIP y de Git. El archivo raw descargado se conserva localmente para consulta autorizada.

## Commits de esta integración

| Hash | Cambio |
|---|---|
| `3629d79` | Unificación de fuentes e integración de seguridad |
| `8bd625d` | Arquitectura y documentación formal |
| `6b94def` | Inventario regional SKU con paginación acotada |
| `79835a1` | Consulta DNS pública mediante API de red |
| `748eb73` | Validación de cuotas serializadas como texto |
| `ac48a4d` | Transporte seguro de cloud-init UTF-8 |
| `f8c9be3` | Diagnóstico de arranque de solo lectura |
| `d16937f` | Integración del cambio concurrente, conservando su historial |
| `7c80233` | Retiro del paquete duplicado ya integrado |
| `548df8c` | Validación de la política administrativa restrictiva efectiva |
| `e1be0c0` | Salud con reintentos y recuperación del bootstrap |

El commit de documentación final se consulta con `git log -1`. Los commits anteriores de web, despliegue y pruebas también permanecen en la misma rama.

## Evaluación y trabajo restante

[GUIA_TECNICA.md](GUIA_TECNICA.md) cubre subneteo, ruta HTTP, DNS TCP/UDP, prioridad/statefulness NSG, UFW, claves SSH, cloud-init, idempotencia, diagnóstico y costos. Preparar una demostración que distinga pruebas de reglas de conectividad funcional y explique los resultados pendientes sin atribuirlos automáticamente a bloqueos.

[PENDIENTES.md](PENDIENTES.md) enumera DNS/Intranet, capacidad regional, clientes, hardening restante, salida de Visitas, pruebas integrales y reporte. La VM web está desasignada y solo responde tras un inicio deliberado para otra demostración.
