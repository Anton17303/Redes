# Despliegue y validación reales · 17/11/2026

Se integró el paquete de seguridad en las fuentes del proyecto y se desplegó la web mediante Azure Cloud Shell autenticado. Los datos siguientes provienen de respuestas reales de Azure y de acceso público desde fuera de la VNet.

## Recursos y estado final

| Recurso o dato | Resultado observado |
|---|---|
| Grupo / región de los recursos | `RG-CafeNube` / `northcentralus` |
| Red / DMZ | `VNet-CafeNube` / `Subnet-DMZ=10.0.0.144/28` |
| VM / NIC | `VM-Web-Publica` / `NIC-Web-Publica` |
| Sistema y tamaño | Ubuntu 22.04 / `Standard_B2ats_v2`, 2 vCPU |
| Disco | `Disk-Web-Publica-OS`, 30 GiB, `Standard_LRS` |
| IP privada / pública | `10.0.0.148` / `40.116.80.26` |
| URL comprobada | `http://cafenube-ventas-publica.northcentralus.cloudapp.azure.com/` |
| Estado al terminar | **`PowerState/deallocated`**, confirmado después de las pruebas |
| Protección de gasto | **`On`**, sin modificación del plan ni del límite |

Se aplicaron 20 operaciones de seguridad: NSG/DMZ faltantes y 18 reglas propias entre cinco NSGs. El inventario posterior vuelve a producir `operations: []`; no creó recursos de cómputo, NAT ni IP. El despliegue posterior creó únicamente la VM pública y sus recursos previstos. Las VMs de Ventas existentes permanecieron desasignadas; no se iniciaron otras VMs.

## Pruebas reales

La ejecución final del runner empezó en `20261117T201227Z-bgZatC` y cerró a **2026-11-17 20:18:36 UTC**. Resultado original: **36 PASS, 5 PENDING, 3 INCONCLUSIVE, 0 FAIL**. El resumen publicable conserva esos estados y elimina únicamente identificadores privados: [resultados JSON](resultados-azure-20261117.json).

| Comprobación | Resultado y alcance |
|---|---|
| DNS del sistema, 1.1.1.1 y 8.8.8.8 | PASS; FQDN resuelve a `40.116.80.26` |
| `/`, `/styles.css`, `/healthz` desde Cloud Shell sin integración a VNet | PASS; HTTP 200 y contenido exacto |
| Acceso desde el equipo local fuera de Azure | PASS; HTML, CSS y salud verificados también después del reinicio |
| Cabeceras públicas | PASS; Nginx sin versión, nosniff, X-Frame-Options y CSP |
| Reglas efectivas de la NIC | PASS; NSG-DMZ y política administrativa adicional de denegación IPv6 conservada |
| Network Watcher: 19 casos de flujo | PASS; HTTP público permitido, SSH desde TI permitido, entradas restantes y salidas DMZ→internas denegadas según el catálogo |
| Guest Ubuntu | PASS; cloud-init `done`, sin errores; `nginx -t`, servicio activo, salud local, UFW, marcador bootstrap y SSH efectivo |
| Navegador externo | Completado por separado: capturas reales de escritorio y dos tamaños móviles, HTTP 200 y sin desborde horizontal |
| Aislamiento funcional DMZ→DNS/Intranet | INCONCLUSIVE; faltan servicios privados y control positivo sano desde TI |
| DNS/Intranet privados y publicación indirecta | PENDING; no existen las dos VMs, y la auditoría de intermediarios externos requiere cierre |
| Apagado al terminar | PASS; respuesta posterior con `PowerState/deallocated` |

El runner no captura el navegador automáticamente; su fila `browser-external-screenshot` permanece PENDING en el JSON original. La evidencia adicional la cierra en este informe sin alterar aquel registro. Las capturas seleccionadas se publican en [publicas/](publicas/), con URL, fecha UTC, origen y SHA-256 en [capturas-publicas.json](publicas/capturas-publicas.json): escritorio 1440×1000 y móviles 390×844 y 320×740. Su fecha es **2026-11-17 19:52:29 UTC**. El ZIP de entrega las incluye. Son capturas del endpoint real; las de `local-render/` corresponden a otra validación local.

Las decisiones de Network Watcher prueban la evaluación de reglas. Sin servidores privados activos ni un control positivo desde TI, no se presentan timeouts como evidencia suficiente de aislamiento funcional ni se declara SSH práctico desde TI aprobado.

## Incidencias corregidas y conservación de registros

El primer intento detectó incompatibilidades de consulta DNS, cuotas serializadas como texto y transporte de custom-data UTF-8 en Azure CLI. Se corrigieron sin duplicar recursos. cloud-init ahora transporta seis archivos mediante base64 ASCII y conserva sus bytes UTF-8 originales.

El primer arranque encontró una carrera al consultar `/healthz` inmediatamente después de recargar Nginx: respondió 404 antes de activarse la configuración. Se añadieron reintentos acotados, se repusieron únicamente las seis fuentes administradas, se validaron Nginx/SSH y se reinició exclusivamente la VM web. Se conservaron los fallos iniciales y la recuperación; no se editaron ni borraron estados de cloud-init. La ejecución final posterior al reinicio confirmó `done`, marcador de bootstrap y servicio sano.

Registros originales privados descargados: `evidencias/azure/cafenube-despliegue.tar.gz`, **113685 bytes**, SHA-256:

```text
df864528ee2e23bcb13d06bf80c045cc4ba0dcde02cb3c751da81a16a6caafed
```

El archivo contiene inventarios iniciales/finales, cambios, pruebas, diagnóstico, recuperación, transcripción y apagado. Se conserva fuera de Git y del ZIP público porque incluye identificadores de la cuenta. La desasignación consta en `20261117T201858Z-QB1AUO/vm-after.json`; su estado de aprovisionamiento registra **20:19:11 UTC**.

## Crédito y límites de la entrega

Se revisó crédito estudiantil vigente de forma privada y se mantuvo la protección de gasto. La ventana acordada usó un presupuesto operativo de hasta USD 6; ese presupuesto no es un corte automático. La prueba se cerró con la VM desasignada. Conservar disco e IP consume aproximadamente **USD 5.19 por 730 h**, más operaciones y conceptos variables según [las tarifas consultadas](../docs/COSTOS_Y_CREDITOS.md). No se afirma un cargo liquidado exacto: el consumo debe contrastarse después en Azure.

El inventario durante la validación mostró cuota regional de **6/6 vCPU**. DNS, Intranet y los clientes de TI/Visitas no están desplegados por esta entrega. El [listado de pendientes](../docs/PENDIENTES.md) describe lo necesario para terminar todo el escenario. TLS es opcional y no se publica 443.
