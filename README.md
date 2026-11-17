# CaféNube · Proyecto Final de Redes

Implementación de una red segmentada en Microsoft Azure con una web pública en DMZ, controles NSG y hardening de servidores Ubuntu. El repositorio organiza el proyecto por componentes técnicos.

## Componentes

| Ruta | Contenido |
|---|---|
| `web/` | Sitio estático de ventas, adaptable a escritorio y móviles |
| `config/` | Configuración Nginx, cloud-init, hardening y variables de ejemplo |
| `scripts/` | Auditoría, política de red, despliegue, pruebas y desasignación |
| `tests/` | Pruebas locales con inventario sintético y validación web |
| `docs/` | Arquitectura, operación, seguridad, costos e informe técnico |
| `evidencias/` | Resultados verificables; registros privados de Azure excluidos de Git |

## Arquitectura

`VNet-CafeNube`: `10.0.0.0/16`, región `northcentralus`, grupo `RG-CafeNube`.

| Segmento | Red | Servicio |
|---|---|---|
| Visitas | `10.0.0.0/26` | Clientes invitados, sin acceso a redes internas |
| Ventas | `10.0.0.64/27` | Clientes de empleados |
| TI | `10.0.0.96/27` | Administración |
| Data Center | `10.0.0.128/28` | DNS `10.0.0.132`, Intranet `10.0.0.133` |
| DMZ | `10.0.0.144/28` | `VM-Web-Publica`, propuesta `10.0.0.148` |

El sitio público usa Nginx por HTTP TCP 80 y un FQDN de la IP pública de Azure. TLS no está implementado; TCP 443 no se publica. SSH se restringe a TI. Las conexiones iniciadas desde la DMZ hacia las redes internas se deniegan.

## Operación

Seguir [el procedimiento de Cloud Shell](docs/CLOUD_SHELL.md). La configuración local real, claves, registros completos de Azure y datos de crédito se excluyen de Git.

```bash
cp config/deployment.env.example config/deployment.env
# Completar la suscripción y revisar los valores.
bash scripts/04_seguridad.sh
bash scripts/00_preflight.sh
bash scripts/01_desplegar_web.sh
```

Los comandos sin `--apply` solo preparan un plan. El plan de seguridad contempla la DMZ y los NSGs del proyecto; no incorpora un NAT Gateway cobrable. El despliegue web exige una política segura, cuota disponible, clave pública válida, protección de gasto `On` y presupuesto aprobado cubierto por crédito verificado.

## Validación y estado

```bash
python3 -m unittest discover -s tests -v
python3 scripts/render_cloud_init.py
```

Consultar [la validación local](evidencias/VALIDACION_LOCAL.md), [la revisión real previa de Azure](evidencias/REVISION_AZURE_2026-11-17.md) y [los pendientes](docs/PENDIENTES.md). Los resultados con inventario simulado verifican el código; no representan pruebas de conectividad en Azure.

Documentación: [seguridad](docs/SEGURIDAD.md), [costos](docs/COSTOS_Y_CREDITOS.md), [informe](docs/INFORME.md) y [guía técnica](docs/GUIA_TECNICA.md).
