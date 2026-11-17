# Operación en Azure Cloud Shell

Usar Bash en una sesión efímera sin almacenamiento, con la suscripción del proyecto. La autenticación y cualquier solicitud inesperada de permisos se revisan personalmente. No actualizar el plan a pago por uso ni retirar la protección de gasto.

## Preparación

```bash
git clone --branch ProyectoFinal-FASE2 --single-branch URL_DEL_REPOSITORIO Redes-fase2
cd Redes-fase2
cp config/deployment.env.example config/deployment.env
nano config/deployment.env
```

Completar el ID de suscripción real. Los scripts pasan `--subscription` explícitamente. El ejemplo no autoriza gasto. En una copia ya existente, revisar `git status` antes de actualizar; no sobrescribir trabajo local.

## Seguridad y DMZ

```bash
bash scripts/04_seguridad.sh
# Revisar security-plan.json y el inventario completo.
bash scripts/04_seguridad.sh --apply
bash scripts/00_preflight.sh
bash scripts/01_desplegar_web.sh
```

El primer comando solo audita. El segundo reconcilia los NSGs y crea únicamente la DMZ/NSG faltantes; no crea NAT, VM, disco ni IP pública. Una regla desconocida o conflicto detiene la ejecución. Las asociaciones de los segmentos existentes se comprueban antes de modificar reglas. Revisar [SEGURIDAD.md](SEGURIDAD.md).

El preflight de la web requiere la DMZ y su política completas. Comprueba además IP, asociaciones, nombre DNS, SKU y cuota. El comando web sin argumentos produce solamente un plan.

## Crédito y despliegue web

Revisar [COSTOS_Y_CREDITOS.md](COSTOS_Y_CREDITOS.md). Configuración prevista: Ubuntu 22.04, `Standard_B2ats_v2`, disco Standard HDD de 30 GiB e IPv4 pública Standard. Una VM gratuita no vuelve gratuitos automáticamente disco/IP. Desasignar conserva cargos de disco/IP.

```bash
cp config/credit-review.example.json config/credit-review.json
nano config/credit-review.json
```

Registrar saldo observado, fecha UTC y vencimiento reales. El archivo real queda fuera de Git. Antes de crear recursos se exige `subscriptionPolicies.spendingLimit == On`, revisión de menos de 24 h y presupuesto positivo cubierto por el saldo. No se cambia la facturación.

Utilizar una clave pública válida. Si es necesario generar otra, custodiar la privada fuera del repositorio y conservarla antes de cerrar Cloud Shell efímero:

```bash
ssh-keygen -t ed25519 -f "$HOME/.ssh/cafenube" -C cafenube
```

Después de aprobar configuración, horas y presupuesto:

```bash
read -r -p 'Presupuesto aprobado USD: ' PRESUPUESTO_USD
read -r -p 'Referencia de aprobación: ' APROBACION
bash scripts/01_desplegar_web.sh --apply --budget-usd "$PRESUPUESTO_USD" --approved-by "$APROBACION"
```

El monto registrado no es un corte automático de facturación. Los recursos propios usan `proyecto=CafeNube`, `componente=web-publica`, `gestion=cafenube-v1`. El script no retaggea recursos ajenos, no sobrescribe una VM existente ni la inicia si está desasignada. Conservar piezas de una creación parcial permite revisar y repetir sin duplicarlas.

## Hardening de otros servidores

```bash
bash scripts/05_hardening.sh --vm VM-DNS
bash scripts/05_hardening.sh --vm VM-DNS --apply
```

El primer comando inspecciona y el segundo aplica sobre esa VM activa, sin iniciarla. Se requiere `azureuser` y clave autorizada. Añadir `--update-packages` solo con salida a Internet comprobada y ventana de mantenimiento aprobada. No se crea NAT. La VM pública recibe la misma política automáticamente desde cloud-init.

## Pruebas y evidencias

```bash
bash scripts/02_pruebas.sh --external-source 'Cloud Shell estándar sin integración a la VNet'
bash scripts/06_pruebas_red.sh
```

Describir el origen externo únicamente si es cierto. Las pruebas guardan JSON originales y `RESULTADOS.md` bajo `evidencias/azure/`. Exigen resultados del guest, controles sanos y reglas efectivas; Run Command aprovisionado no prueba éxito de su script. No crean Network Watcher ni inician VMs.

Obtener la URL real desde Azure:

```bash
source config/deployment.env
az network public-ip show --subscription "$CAFENUBE_SUBSCRIPTION_ID" -g RG-CafeNube -n PIP-Web-Publica --query '{fqdn:dnsSettings.fqdn,ip:ipAddress}' -o table
```

Abrir `http://FQDN_REAL/` desde Internet y guardar captura auténtica con URL, fecha y origen. No hay TLS ni redirección HTTPS. Los códigos de pruebas son 0 sin pendientes, 1 con fallos y 2 con pendientes/inconclusos.

## Conservación y apagado

```bash
tar -czf cafenube-evidencias.tar.gz -C evidencias azure
bash scripts/03_apagar.sh
```

Descargar el paquete antes de terminar la sesión efímera. En el diálogo de descarga no duplicar el prefijo del directorio de inicio; hacer clic en el enlace final del archivo. Verificar `PowerState/deallocated` de la VM pública. Revisar los costos persistentes de disco/IP y acordar su conservación. Nunca eliminar el grupo para detener una demostración.
