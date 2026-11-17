# Revisión de integración · 17/11/2026

## Consultas reales de solo lectura

Se retomó la sesión autenticada de Azure Portal y Cloud Shell Bash efímero. ARM devolvió:

```json
{"quotaId":"AzureForStudents_2018-01-01","spendingLimit":"On"}
```

La consulta se realizó con `az rest --method get --uri /subscriptions/ID_REAL --url-parameters api-version=2022-12-01 --query subscriptionPolicies -o json`. El identificador completo se conserva únicamente en registros privados. No se modificó facturación ni protección de gasto.

La auditoría de reglas propias mostró:

| NSG | Regla real inicial |
|---|---|
| `NSG-Visitas` | `Deny-Visitas-Interno`, prioridad 100, salida, denegar hacia `10.0.0.0/16` |
| `NSG-Ventas` | `Deny-Visitas-Ventas`, prioridad 100, entrada desde `10.0.0.0/26`, denegar |
| `NSG-TI` | Lista de reglas propias vacía |
| `NSG-DataCenter` | Lista de reglas propias vacía |

El catálogo integrado conserva los nombres de esas dos reglas reales y sus prioridades. Añade la administración de Ventas en prioridad 110 y amplía el bloqueo de Visitas/DMZ según el diseño. El paquete original asumía reglas de Data Center que no aparecieron en la consulta; no se presentan como reglas ya desplegadas.

## Integración del paquete de seguridad

Se revisó el contenido de `fase2_nsg_hardening.zip`. Se corrigieron DMZ propuesta distinta, nombre de VM incompatible, apertura de 443 sin TLS, administración demasiado amplia de la DMZ, falta de interrupción ante errores y clasificación de bloqueos sin controles efectivos.

La funcionalidad queda integrada por componentes: catálogo NSG, plan/aplicación, matriz CSV generada, hardening compartido por rol y pruebas de red con controles positivos. El NAT de mantenimiento no se incorpora al flujo automático por su costo. La actualización de servidores privados requiere definir su salida a Internet por separado.

Esta revisión registra el estado inicial. La política y la DMZ se aplicaron después; consultar los [resultados posteriores del despliegue](DESPLIEGUE_AZURE_2026-11-17.md) para el dominio y las pruebas reales.
