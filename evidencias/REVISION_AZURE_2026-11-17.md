# Revisión real de Azure · 17 de noviembre de 2026

**Resultado: preflight detenido; servicio público no desplegado.** Se accedió a la sesión abierta de Azure Portal y a Cloud Shell Bash efímero, sin montar almacenamiento. Las consultas siguientes se ejecutaron contra la suscripción real del equipo, `Azure for Students`, cuyo estado devuelto fue `Enabled`.

## Estado comprobado

| Elemento | Resultado observado |
|---|---|
| Grupo | Existe `RG-CafeNube`; su ubicación de metadatos es `eastus` |
| Red | Existe `VNet-CafeNube`, en `northcentralus`, con `10.0.0.0/16` |
| Subredes | Solo están las cuatro subredes originales, enumeradas abajo |
| `Subnet-DMZ` | No existe en esa VNet |
| `NSG-DMZ` | La consulta devuelve `ResourceNotFound` en el grupo |
| IP propuesta `10.0.0.148` | Azure devuelve `PrivateIPAddressNotInAnySubnet`; no se puede declarar disponible ni asignada |
| VM/NIC/PIP de la web pública | No aparecen en el inventario del grupo |
| `VM-DNS` y `VM-Intranet` | No aparecen en el inventario del grupo |
| `VM-Ventas-1` y `VM-Ventas-2` | Ambas muestran `VM deallocated`; columnas PublicIps y Fqdns vacías |
| Bastion existente | `VNet-CafeNube-bastion`, SKU consultado `Developer`; no se modificó |

| Subred real | CIDR real | NSG asociado |
|---|---|---|
| `Subnet-Visitas` | `10.0.0.0/26` | `NSG-Visitas` |
| `Subnet-Ventas` | `10.0.0.64/27` | `NSG-Ventas` |
| `Subnet-TI` | `10.0.0.96/27` | `NSG-TI` |
| `Subnet-DataCenter` | `10.0.0.128/28` | `NSG-DataCenter` |

El listado completo de Azure CLI contiene 15 recursos, incluidas dos programaciones de apagado y el Bastion. La vista del portal mostró 13 elementos; las conclusiones sobre nombres de recursos se contrastaron con el listado CLI. No se consultaron las reglas internas de los cuatro NSGs existentes ni se modificaron.

## Comandos ejecutados

Después de clonar `ProyectoFinal-FASE2` y establecer explícitamente el ID real de la suscripción en la sesión, se ejecutó desde `./`:

```bash
bash scripts/00_preflight.sh evidencias/azure/revision-real-20261117
```

El script guardó `account.json`, `group.json`, `vnet.json` y `preflight.log`. Se detuvo al consultar el NSG, antes de generar un plan aprobado o ejecutar creación de recursos. El error observado fue:

```text
Code: ResourceNotFound
Microsoft.Network/networkSecurityGroups/NSG-DMZ
under resource group RG-CafeNube was not found.
```

También se registraron estas consultas en `inventario-terminal.txt`:

```bash
az resource list -g RG-CafeNube -o table
az vm list -d -g RG-CafeNube -o table
az resource show -g RG-CafeNube -n VNet-CafeNube-bastion \
  --resource-type Microsoft.Network/bastionHosts --query sku.name -o tsv
az network vnet check-ip-address -g RG-CafeNube -n VNet-CafeNube \
  --ip-address 10.0.0.148 -o json
```

La última consulta devolvió `PrivateIPAddressNotInAnySubnet`, de ahí el código de salida 1 al terminar ese registro. No fue una prueba de aislamiento ni una confirmación de IP libre. El registro adicional tiene marcas de tiempo de `13:12:14` a `13:14:08 UTC`, el 17/11/2026.

## Conservación de los originales

Los cinco archivos originales se empaquetaron en Cloud Shell y se descargaron a la computadora. Se verificó el contenido del archivo y se guardó en:

- `evidencias/azure/revision-real-20261117/`: JSON y registros originales.
- `evidencias/azure/cafenube-preflight.tar.gz`: paquete original descargado, 2110 bytes.
- SHA256 del paquete: `08579c778524354670d9e72d8b7947a429826ad60ab7f3a6838a0a563f0851d3`.

Los originales se ignoran por Git porque contienen identificadores completos de la suscripción. Este resumen conserva los resultados relevantes sin publicarlos. No se sustituyeron registros reales por fixtures ni se crearon capturas de servicios inexistentes.

## Qué falta para continuar

1. Coordinar con el área de redes la incorporación de `Subnet-DMZ=10.0.0.144/28` y con el área de seguridad la creación/asociación de `NSG-DMZ` con su política segura. No se realizaron esas tareas de otros responsables.
2. Repetir el preflight completo. La revisión se detuvo antes de comprobar SKU/cuota, propiedad de recursos propios, disponibilidad del nombre DNS y conflictos de IP en una DMZ ya existente.
3. Aprobar configuración, horas y presupuesto antes de ejecutar `01_desplegar_web.sh --apply`.
4. Desplegar y verificar Nginx/cloud-init/UFW/SSH, DNS público, HTTP externo y aislamiento con controles positivos internos sanos.
5. Integrar DNS/Intranet y consolidar las evidencias en el informe final. El reporte debe reflejar el Bastion existente y las dependencias aún ausentes.

No se iniciaron ni desasignaron las VMs ajenas, no se registraron proveedores de recursos ni se cambiaron redes, reglas, etiquetas o recursos existentes. No se creó PIP, NIC, disco ni VM durante esta revisión.

## Revisión posterior de crédito y costos

Se abrió Education Hub en la misma sesión autenticada y se observó el beneficio estudiantil activo, su saldo y vencimiento. El portal separado de Sponsorships no mostraba un patrocinio activo; no se usó ese mensaje para concluir que no existían créditos. Los valores financieros se conservaron únicamente en archivos locales ignorados por Git.

Se consultaron tarifas generales de la API oficial Azure Retail Prices para la configuración propuesta; ver [COSTOS_Y_CREDITOS.md](../docs/COSTOS_Y_CREDITOS.md). No se confirmó todavía el valor ARM `subscriptionPolicies.spendingLimit`, ni la cuota/SKU ni los beneficios gratuitos específicos de esa VM/disco. El nuevo control de despliegue exige protección `On`, revisión reciente del saldo y presupuesto explícito; las 26 pruebas locales usan datos sintéticos. La revisión no creó recursos ni autorizó consumo.
