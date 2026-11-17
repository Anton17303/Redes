# CaféNube · Nina Nájera · Integrante 4

Página pública de Ventas, Nginx HTTP, cloud-init y automatización de publicación en la DMZ. Trabajo preparado en `ProyectoFinal-FASE2`, usando el HTML y la propuesta de scripts del ZIP como punto de partida.

**Estado al 17 de noviembre de 2026:** implementación y validación local completadas. Azure no fue inspeccionado ni desplegado: no hay Azure CLI autenticada en este equipo y el control del Chrome abierto se detuvo al no poder verificar su URL. No hay IP pública, FQDN ni evidencia de conectividad de Azure confirmados. No se crearon recursos cobrables.

## Archivos

| Carpeta | Entregable |
|---|---|
| `web/` | HTML del ZIP mejorado y CSS: empresa, orígenes y suscripción; sin dependencias externas |
| `config/` | Nginx, bootstrap Ubuntu, base cloud-init, diagnósticos y ejemplo de variables |
| `scripts/` | Preflight de solo lectura, plan/despliegue, pruebas y desasignación |
| `tests/` | Casos de seguridad, CLI simulada e inspección real de Nginx/web local |
| `evidencias/` | Estado y resultados locales; resultados reales de Azure se guardan en subcarpetas ignoradas por Git |
| `docs/` | Procedimiento Cloud Shell, coordinación, sección para Diego y evaluación individual |

## Ejecutar

Seguir [CLOUD_SHELL.md](docs/CLOUD_SHELL.md), con la suscripción del equipo. Primera comprobación:

```bash
cp config/deployment.env.example config/deployment.env
# Completar el ID de suscripción en deployment.env.
bash scripts/00_preflight.sh
bash scripts/01_desplegar_web.sh
```

El despliegue sin argumentos **solo produce un plan**. Para crear recursos hay que aprobar antes el costo, tener una clave SSH pública válida y usar los argumentos documentados. Los scripts nunca crean ni modifican VNet, subredes, NSGs o sus reglas. Una política que no puede comprobarse detiene el despliegue.

## Diseño previsto

| Recurso | Valor acordado, pendiente de verificar en Azure |
|---|---|
| Grupo / región | `RG-CafeNube` / `northcentralus` |
| VNet / DMZ | `VNet-CafeNube`, `10.0.0.0/16` / `Subnet-DMZ`, `10.0.0.144/28` |
| Seguridad / administración | `NSG-DMZ` / SSH solo TI `10.0.0.96/27` |
| VM / NIC / IP pública | `VM-Web-Publica` / `NIC-Web-Publica` / `PIP-Web-Publica` |
| IP privada | `10.0.0.148`, primera asignable del /28 de Azure |
| Servicio | Ubuntu 22.04 + Nginx, TCP 80; **TLS no implementado, 443 no publicado** |
| DNS público | FQDN devuelto por Azure para la IP pública; nunca se construye ni se inventa |
| DNS de la NIC pública | `168.63.129.16` de Azure; no se utiliza BIND privado |

La IP pública Standard de la NIC proporciona un método explícito de salida; las reglas deben permitir las descargas de Ubuntu por TCP 80/443. `cloud-init` actualiza paquetes e instala Nginx, UFW, curl y herramientas DNS. Un fallo de instalación impide crear el marcador de disponibilidad.

`web/`, `config/nginx_cafenube.conf` y `config/bootstrap.sh` son las fuentes únicas. `render_cloud_init.py` produce `build/cloud-init.yaml` con los archivos exactos y comprueba el límite de 64 KiB. El artefacto generado se ignora por Git y siempre se regenera antes del despliegue. JSON bajo `#cloud-config` es YAML válido.

## Validación local

```bash
python3 -m unittest discover -s tests -v
python3 scripts/render_cloud_init.py
for script in scripts/*.sh config/*.sh; do bash -n "$script" || exit; done
# Opcional, con nginx y Playwright instalados en un entorno local aislado:
python3 tests/validate_web.py
```

Los casos con datos ficticios prueban rechazos, propiedad de recursos, cuota e idempotencia; no son pruebas de Azure. [VALIDACION_LOCAL.md](evidencias/VALIDACION_LOCAL.md) registra lo ejecutado realmente.

## Seguridad y límites

- Las reglas admitidas por el preflight son deliberadamente estrictas. Revisar [SEGURIDAD_CON_JOSE.md](docs/SEGURIDAD_CON_JOSE.md) antes de integrar. Una política equivalente pero de otra forma puede requerir ampliar el validador y probarlo; no se omite la comprobación con una variable.
- La validación previa comprueba la configuración de la subred. Las reglas **efectivas**, rutas, Nginx y UFW se comprueban después con la VM activa. No se promete disponibilidad a partir de un plan.
- `02_pruebas.sh` distingue `PASS`, `FAIL`, `PENDING` e `INCONCLUSIVE`. Necesita controles positivos desde TI: un servicio apagado no demuestra aislamiento.
- Reejecutar no actualiza el contenido de una VM existente ni la inicia si está desasignada. Conserva los recursos propios validados. Un cambio posterior de contenido requiere una actualización controlada y otra validación.
- No se crean claves privadas automáticamente, no se guardan credenciales y no hay operaciones para eliminar el grupo. `03_apagar.sh` solo desasigna la VM pública identificada como propia.
- Los datos brutos de Azure y capturas se guardan localmente. Revisarlos y seleccionar qué adjuntar al informe antes de publicarlos; nunca subir credenciales.

Para Diego: [SECCION_PARA_INFORME.md](docs/SECCION_PARA_INFORME.md). Para la evaluación: [EVALUACION_INDIVIDUAL.md](docs/EVALUACION_INDIVIDUAL.md). Para pendientes del equipo: [PENDIENTES.md](docs/PENDIENTES.md).
