# Política de seguridad

La configuración se organiza por segmento. `scripts/security_policy.py` integra la política NSG y `config/hardening_vm.sh` aplica controles de Ubuntu por rol. Ambos usan los nombres, CIDR y servicios de la arquitectura del proyecto.

## NSGs

| Segmento | Entradas y salidas previstas |
|---|---|
| Visitas | Administración desde TI; denegar el inicio de conexiones a VirtualNetwork; conservar salida a Internet según conectividad disponible |
| Ventas | Administración desde TI; bloquear entradas de Visitas/DMZ y salidas iniciadas hacia TI |
| TI | Denegar conexiones iniciadas desde Visitas, Ventas, Data Center y DMZ |
| Data Center | Ventas accede a DNS 53 TCP/UDP y a Intranet TCP 80; administración TI y tráfico del segmento; denegar el resto de la VNet y salidas iniciadas hacia TI |
| DMZ | Internet TCP 80; TI TCP 22/80; denegar el resto de las entradas y las salidas hacia VirtualNetwork |

Los NSGs son stateful: una respuesta a una conexión permitida no constituye una conexión nueva. Las reglas propias tienen prioridad sobre `AllowVnetInBound` y `AllowVnetOutBound` (65000).

El plan rechaza reglas fuera del catálogo, prioridades ocupadas, cambios de CIDR, NSGs compartidos inesperadamente, peerings y rutas no revisadas. No borra reglas desconocidas. La regla histórica amplia de Ventas en Data Center se restringe en su mismo nombre a DNS 53; la regla específica de Intranet permite únicamente HTTP 80. Los nombres técnicos históricos se conservan cuando corresponda para evitar recreaciones innecesarias.

La DMZ nueva se asocia al NSG después de configurar sus reglas. No se cambia el direccionamiento de las cuatro subredes existentes. Se guardan inventarios antes/después y cada respuesta de modificación. Un error detiene el proceso; revisar cambios parciales antes de repetir.

## Hardening de Ubuntu

- SSH con clave, sin root, contraseña, X11, agent forwarding ni TCP forwarding. Usuario `azureuser`, máximo tres intentos y espera de inicio de 30 segundos.
- Se requiere una clave autorizada existente antes de cambiar SSH. No se inicia ni reinicia automáticamente una VM.
- Se deshabilitan servicios prescindibles presentes y se aplican parámetros contra redirects/source routing y SYN floods.
- UFW deniega entradas por defecto, permite administración desde TI y servicios según rol. En web se conserva el bloqueo de salida RFC1918. No se resetea el firewall ni se abre TCP 443.
- Las reglas UFW existentes deben auditarse: añadir restricciones no demuestra que una regla antigua más permisiva haya desaparecido. Contrastar estado efectivo y conectividad después de ejecutar.
- Las actualizaciones de paquetes requieren salida disponible. El mantenimiento no crea NAT automáticamente. Un NAT Gateway supone costos y necesita una decisión adicional; queda fuera del despliegue de costo mínimo.

## Pruebas y límites

`02_pruebas.sh` verifica la web, DNS público, Nginx, cloud-init, SSH/UFW, NSGs efectivos y aislamiento con controles positivos. `06_pruebas_red.sh` agrega la matriz TCP de Visitas, Ventas, TI, Data Center y DMZ.

Un timeout solo se considera aislamiento aprobado si el servicio responde desde TI y Azure devuelve una regla Deny efectiva. Una conexión rechazada por el servidor demuestra alcance de red y no se cuenta como bloqueo NSG. Sin VM activa, control sano o Network Watcher existente, se conserva `PENDING`/`INCONCLUSIVE`.

La matriz TCP no sustituye DNS UDP, resolución funcional de empleados ni pruebas de Internet desde Visitas. No se publica el DNS privado ni la Intranet. Deben revisarse también balanceadores, proxies, túneles y nombres públicos fuera del inventario directo de NICs.

## Correcciones del informe base

1. El flujo Visitas → redes internas debe figurar como denegado.
2. HTTPS no está implementado: retirar la afirmación de servicio TCP 443 funcional.
3. Incorporar DMZ, NSG, reglas efectivas, direccionamiento y resultados comprobados.
4. Separar resultados locales, inventario de Azure y pruebas de conectividad reales.

Referencias: [reglas y defaults NSG](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview), [filtrado acumulado](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-group-how-it-works) y [salida explícita](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access).
