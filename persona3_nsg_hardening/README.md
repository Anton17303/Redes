# Integrante 3 · NSGs, firewall, ACL y hardening (CaféNube Fase 2)

Complementa el paquete de Adrián (DNS + Intranet). Mismos nombres e IPs (`variables.env`).

## Orden
```bash
az login
./00_auditar.sh                  # estado REAL vs reporte de Fase 1 (NSG asociados, reglas, IPs públicas)
DRY_RUN=1 ./01_nsg_reglas.sh     # ver qué comandos se van a ejecutar
./01_nsg_reglas.sh               # aplica la política (idempotente; se puede repetir cuando exista la DMZ)
./02_nat_mantenimiento.sh on     # salida temporal a Internet para actualizar Ventas/TI/DC
./03_hardening.sh                # updates, SSH, ufw, servicios, sysctl en cada VM
./02_nat_mantenimiento.sh off    # quitar el NAT (cobra por hora)
./04_pruebas_seguridad.sh        # matriz PASS/FAIL -> evidencias/*.csv
```

## Qué depende de los demás
| Necesito | De quién | Mientras tanto |
|---|---|---|
| CIDR y nombre de la subred DMZ (`RED_DMZ`, `SUBNET_DMZ`) | Jose (1) | `10.0.1.0/27` es solo una propuesta; reglas de DMZ se aplican al re-correr el paso 1 |
| VM web de la DMZ + IP pública (`VM_WEB`) | Nina (4) | Se saltan hardening y pruebas de DMZ |
| VM-TI-1 y VM-Visitas-1 | Adrián (`00_vms_prueba.sh`) o Diego | Sin ellas no hay pruebas de TI/Visitas |
| Orden de despliegue y ventana de integración | Diego (5) | — |

## Notas de diseño
- Los NSG son *stateful*: se bloquea quién **inicia**. Se aplica en origen (Outbound) y destino (Inbound) para tener doble capa.
- `Allow-Ventas` (cualquier puerto) de NSG-DataCenter se reemplaza por dos reglas de puerto específico (DNS 53, Intranet 80/443). `Allow-TI`, `Allow-DC-Interno` y `Deny-Resto-VNet` se conservan (Adrián depende de ellas).
- `ufw` en cada VM es una segunda capa: SSH solo desde TI.
- `hardening_vm.sh` usa `00-` en el drop-in de sshd porque sshd toma el **primer** valor y `50-cloud-init.conf` puede dejar la contraseña activa.
- Sin secretos en los scripts (llaves SSH las genera `az vm create`).
- `matriz_nsg.csv`: matriz final para el reporte.
