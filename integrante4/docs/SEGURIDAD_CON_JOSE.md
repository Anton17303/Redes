# Coordinación con José Antón y José Ordóñez

Esta es la política requerida por la implementación de Nina. Se documenta para que los responsables de red y seguridad la integren; estos archivos **no cambian** sus recursos.

**Comprobación real del 17/11/2026:** faltan `Subnet-DMZ` y `NSG-DMZ`. El preflight se detuvo al consultar el NSG. No se han comprobado reglas efectivas de la DMZ porque todavía no existe su NIC/VM. Ver [la evidencia real](../evidencias/REVISION_AZURE_2026-11-17.md).

## Perfil que acepta el preflight

| Prioridad sugerida | Dirección | Origen | Destino | Protocolo / puerto | Acción |
|---|---|---|---|---|---|
| 100 | Entrada | `Internet` | `10.0.0.148` | TCP 80 | Permitir |
| 110 | Entrada | `10.0.0.96/27` | `10.0.0.148` | TCP 22 | Permitir |
| 120, opcional | Entrada | `10.0.0.96/27` | `10.0.0.148` | TCP 80 | Permitir |
| 4000 | Entrada | `*` | `*` | `*` / `*` | Denegar |
| 100 | Salida | `*` | `VirtualNetwork` | `*` / `*` | Denegar |
| 65001, predeterminada | Salida | `*` | `Internet` | `*` / `*` | Permitir, si no hay DenyAll-Out propio |

Todas usan puerto de origen `*`. Las prioridades reales pueden variar, pero los permisos de entrada deben preceder al bloqueo general y los bloqueos propios deben preceder a los predeterminados de prioridad 65000. `NSG-DMZ` debe estar asociado a `Subnet-DMZ=10.0.0.144/28`.

El validador acepta destino de entrada `*`, la DMZ o su IP privada, siempre dentro de este perfil. Admite la representación singular y plural de los campos de Azure. Rechaza ASGs, permisos más amplios, prioridades repetidas, excepciones de salida a redes internas y reglas no comprendidas. Esto es una comprobación conservadora, no un evaluador completo de todos los service tags de Azure.

Si se usa un DenyAll-Out propio, permitir antes TCP 80/443 hacia `Internet` para paquetes. Se aceptan permisos explícitos DNS TCP/UDP 53 hacia `AzurePlatformDNS` o `168.63.129.16`. No bloquear el DNS de la plataforma ni la comunicación necesaria del agente de Azure. Revisar por separado los flujos de plataforma: no todos se filtran igual que tráfico de aplicación.

La VM tendrá PIP Standard propia y DNS Azure explícito en la NIC; así no necesita iniciar consultas a BIND en Data Center para instalar paquetes. No se agrega NAT Gateway ni se modifica el DNS de la VNet.

## Aspectos que deben comprobarse juntos

- El bloqueo general de entrada evita que `AllowVnetInBound` permita visitas, ventas y Data Center hacia la DMZ. Las conexiones iniciadas desde TI quedan limitadas a los servicios aprobados.
- El Deny a `VirtualNetwork` de salida evita que `AllowVnetOutBound` permita iniciar conexiones hacia los segmentos privados. Los NSGs son stateful: la respuesta a una conexión permitida desde TI o Internet no necesita una nueva apertura hacia esas redes.
- UFW agrega defensa en la VM: entrada 80, SSH desde TI, denegación de entrada desde otras redes de la VNet y salida denegada a RFC1918. SSH solo usa claves, sin root ni contraseñas.
- No se publica TCP 443. El informe/NSG del equipo debe ajustar la regla HTTP/HTTPS a HTTP 80 mientras no exista TLS válido.
- Verificar reglas efectivas y rutas en la NIC con la VM activa. Si existe seguridad administrativa de Azure Virtual Network Manager, NVA, peering o rutas diferentes, revisar su efecto antes de dar por terminada la integración.
- Confirmar que las VMs privadas no tienen IP pública ni publicaciones por balanceador, gateway, firewall, proxy o túnel. La ausencia de una PIP directa es solo una de las comprobaciones.
- Un timeout desde DMZ necesita controles positivos de DNS/Intranet desde TI y una decisión Deny efectiva de Azure para atribuirlo a aislamiento.

## Correcciones del informe base que Diego debe integrar

1. La tabla de flujos de la sección 6.5 dice `Visitas → Subredes internas: Permitir`; debe decir **Denegar**, de acuerdo con los requisitos y la sección de seguridad.
2. El DNS interno acordado en la parte más reciente es `cafenube.internal`, con `rrhh.cafenube.internal → 10.0.0.133`. No mezclarlo con la propuesta anterior `.local`.
3. La matriz de DMZ menciona 80/443. La implementación entregada sirve **solo HTTP 80**; retirar 443 de los permisos públicos o completar TLS y todas sus pruebas en un trabajo posterior.
4. Las afirmaciones del informe sobre recursos ya creados requieren evidencia del estado real. Esta implementación local no demuestra que la configuración exista en la suscripción.
