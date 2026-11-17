# Procedimiento reproducible en Azure Cloud Shell (Bash)

**Ejecución real del 17/11/2026:** este procedimiento ya permitió inspeccionar la suscripción. El preflight se detuvo porque no existe `NSG-DMZ`; tampoco está creada la subred DMZ. Repetir la comprobación después de resolver esas dependencias. No omitirla ni ejecutar `--apply` para intentar compensarlas. Ver [la revisión real](../evidencias/REVISION_AZURE_2026-11-17.md).

## 1. Obtener la rama y elegir la suscripción

Entrar a Azure Portal → Cloud Shell → **Bash** con la cuenta del equipo. Preferir una sesión efímera sin almacenamiento si está disponible; no crear almacenamiento ni otros recursos cobrables sin presupuesto aprobado. Si Cloud Shell solicita autenticación, completarla personalmente.

```bash
git clone --branch ProyectoFinal-FASE2 --single-branch https://github.com/Anton17303/Redes.git Redes-fase2
cd Redes-fase2/integrante4
az account list --query '[].{name:name,id:id,state:state}' -o table
cp config/deployment.env.example config/deployment.env
nano config/deployment.env
```

Completar `CAFENUBE_SUBSCRIPTION_ID` con el ID real. Confirmar la etiqueta DNS y el tamaño de VM con el equipo. El ejemplo no contiene un ID real ni una autorización de gasto. Los scripts pasan `--subscription` en cada petición y no cambian la suscripción predeterminada global.

Si la rama ya existe en una copia de trabajo, ejecutar `git status` y actualizarla sin sobrescribir cambios ajenos. No ejecutar los scripts extraídos del ZIP original: usar esta carpeta revisada.

## 2. Inspeccionar sin crear recursos

```bash
bash scripts/00_preflight.sh
bash scripts/01_desplegar_web.sh
```

Ambos comandos consultan recursos; el segundo genera también cloud-init. Se guarda una carpeta con fecha UTC bajo `evidencias/azure/`. Leer `plan.json`, `nsg.json`, `vnet.json`, `skus.json` y `usage.json`.

El inventario incluye NICs/IPs/VMs de toda la suscripción para detectar asociaciones con otros grupos. Si faltan permisos de lectura, se detiene; un error RBAC no se interpreta como recurso inexistente.

Debe existir la DMZ con su NSG seguro. Si falta, coordinar con José Ordóñez y José Antón. No añadir redes alternativas para evadir el fallo. Se rechazan UDRs, peerings y delegaciones no revisadas; se detiene ante reglas no comprendidas. Los recursos existentes solo se reutilizan si coinciden grupo, región, asociaciones y etiquetas propias:

```text
proyecto=CafeNube
integrante=4
gestion=cafenube-i4-v1
```

Si un recurso del ZIP anterior existe sin esa identificación, revisar su propietario y contenido con el equipo. No retaggearlo automáticamente para forzar el preflight. Los recursos fallidos o discos de despliegues incompletos requieren revisión manual.

## 3. Aprobar configuración y presupuesto antes de aplicar

Revisar en Azure Pricing Calculator o en el portal el tamaño `Standard_B2ats_v2`, Linux en `northcentralus`, disco de SO Standard HDD de 30 GiB, IPv4 pública Standard, horas de prueba y transferencia de datos. El precio de Fase 1 no se toma como cotización vigente.

Registrar con el dueño de la suscripción: tamaño, horas máximas, monto total en USD, crédito disponible y responsable del apagado. **`--budget-usd` registra el monto aprobado; no establece un corte automático de facturación.** No se han creado alertas de costo ni un recurso Budget desde estos scripts.

Revisar [COSTOS_Y_CREDITOS.md](COSTOS_Y_CREDITOS.md) y completar `config/credit-review.json` a partir del ejemplo, con un saldo real vigente observado hace menos de 24 horas. `check_credit_guard.py` consulta además la política de la suscripción y exige `spendingLimit: On`. Un valor distinto o desconocido bloquea las creaciones; el script no cambia el plan ni retira protecciones de gasto.

Preparar una clave pública existente y válida. Si hace falta una nueva, crearla fuera del repositorio y protegerla personalmente:

```bash
ssh-keygen -t ed25519 -f "$HOME/.ssh/cafenube-i4" -C 'cafenube-i4'
```

No pegar la clave privada ni la frase de protección en un chat, informe o archivo del proyecto. En Cloud Shell efímero, descargarla y custodiarla de forma segura antes de terminar la sesión; otra opción es aportar una clave pública ya disponible.

Solo después de la aprobación explícita, ejecutar este comando sustituyendo los dos valores:

```bash
read -r -p 'Monto total aprobado en USD: ' PRESUPUESTO_USD
read -r -p 'Nombre del responsable que aprobó el gasto: ' RESPONSABLE
bash scripts/01_desplegar_web.sh --apply \
  --budget-usd "$PRESUPUESTO_USD" --approved-by "$RESPONSABLE"
```

El script vuelve a inspeccionar Azure antes de la primera creación. Crea solo los recursos que falten; no crea subredes ni NSGs. No inicia una VM existente desasignada. Si falla después de crear la PIP/NIC, esas piezas se conservan para repetir el preflight y continuar. No ejecutar limpiezas globales.

Una VM existente fallida no se sobrescribe. Una VM válida existente no se actualiza con el nuevo cloud-init: cloud-init se aplica en el primer arranque. Las verificaciones HTTP comparan el contenido servido con los archivos locales para detectar versiones distintas.

## 4. Verificar servicio, DNS y aislamiento

Dar tiempo a que termine la instalación. El diagnóstico espera cloud-init con un límite de 300 segundos dentro del guest. Ante una demora o fallo, consultar su estado y logs; no marcar la prueba como exitosa.

```bash
bash scripts/02_pruebas.sh --external-source 'Cloud Shell estándar sin integración a la VNet'
```

Usar esa descripción **únicamente si es cierta**. Un Cloud Shell integrado a la VNet no demuestra acceso desde Internet. Alternativamente ejecutar las pruebas HTTP desde un equipo externo con Azure CLI autenticada o abrir el sitio desde un navegador en red móvil.

El runner:

1. Revisa nuevamente la identidad de los recursos y su política.
2. Obtiene el FQDN/IP reales, consulta el resolvedor del sistema y los públicos `1.1.1.1` y `8.8.8.8`.
3. Comprueba HTTP 200, SHA256 exacto del HTML/CSS, `/healthz` y cabeceras Nginx.
4. Guarda NSGs efectivos y rutas de la NIC.
5. Usa un Network Watcher **ya existente** para `test-ip-flow`, con decisión Allow/Deny y nombre de regla. No lo crea ni instala la extensión del agente.
6. Ejecuta diagnósticos de cloud-init, Nginx, SSH y UFW mediante Run Command. Exige un resultado JSON del guest; el estado de aprovisionamiento de Run Command no es un PASS.
7. Compara consultas DNS TCP/UDP y acceso HTTP a la Intranet desde DMZ con los mismos servicios sanos desde `VM-TI-1`. Una respuesta DNS `REFUSED` sigue siendo conectividad y falla el aislamiento de red.
8. Revisa las NICs de `VM-DNS` y `VM-Intranet` y el inventario de posibles balanceadores, gateways o firewalls públicos. Una publicación indirecta requiere revisión conjunta.

`VM-TI-1`, `VM-DNS` y `VM-Intranet` deben existir y estar activas para los controles positivos. El script no las crea, configura ni inicia. Las herramientas remotas son Python estándar y comandos de lectura.

El código de salida es `0` sin pendientes, `1` si hay fallos y `2` si queda algo pendiente o inconcluso. La captura externa y la revisión completa de publicación privada requieren evidencia manual y aparecen pendientes en el resultado automático.

Obtener la URL real sin construir un nombre supuesto:

```bash
source config/deployment.env
az network public-ip show --subscription "$CAFENUBE_SUBSCRIPTION_ID" \
  -g RG-CafeNube -n PIP-Web-Publica \
  --query '{fqdn:dnsSettings.fqdn,ip:ipAddress}' -o table
```

Abrir `http://FQDN_REAL/` desde fuera de la VNet. Usar HTTP explícitamente; no hay redirección ni certificado HTTPS. Guardar captura con URL, fecha y origen de la prueba. No ignorar advertencias de certificados ni presentar HTTPS como implementado.

## 5. Conservar evidencias y desasignar

Revisar `RESULTADOS.md`, los JSON originales y las capturas. Adjuntar al informe solo resultados ejecutados. Descargar las evidencias antes de cerrar una sesión efímera; los logs no se sincronizan solos con GitHub. Se puede empaquetar la carpeta desde `integrante4/`:

```bash
tar -czf cafenube-evidencias.tar.gz -C evidencias azure
```

En **Administrar archivos → Descargar**, revisar si el formulario ya muestra el prefijo del directorio de inicio: no duplicarlo en la parte editable. Después de preparar la descarga, hacer clic en el enlace del archivo que aparece en Cloud Shell; completar el formulario por sí solo no lo guarda en la computadora.

```bash
bash scripts/03_apagar.sh
```

Debe confirmar `PowerState/deallocated` únicamente para `VM-Web-Publica`. El disco y la PIP Standard pueden seguir generando cargos; no se borran automáticamente. Para la demostración posterior, el dueño de la suscripción debe aprobar las horas y encender la VM; luego repetir pruebas y desasignarla.

## Referencias técnicas

- [NSGs, prioridades y reglas predeterminadas](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview).
- [Filtrado acumulado en subred y NIC](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-group-how-it-works).
- [IP pública Standard y DNS público](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/public-ip-addresses).
- [Azure CLI: IP pública](https://learn.microsoft.com/en-us/cli/azure/network/public-ip?view=azure-cli-latest), [NIC](https://learn.microsoft.com/en-us/cli/azure/network/nic?view=azure-cli-latest), [VM](https://learn.microsoft.com/en-us/cli/azure/vm?view=azure-cli-latest).
- [Network Watcher test-ip-flow](https://learn.microsoft.com/en-us/cli/azure/network/watcher?view=azure-cli-latest#az-network-watcher-test-ip-flow).
- [Módulos cloud-init](https://docs.cloud-init.io/en/latest/reference/modules.html).
