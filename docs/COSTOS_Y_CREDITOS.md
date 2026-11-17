# Costos y protección del crédito

## Alcance de «gratis»

Una cuota gratuita y un gasto cubierto por crédito son distintos. Un servicio dentro de su cuota gratuita no consume crédito por ese concepto; una IP/disco facturable puede descontarse del saldo promocional. No declarar que toda la publicación es gratuita solo porque la VM sea elegible para un beneficio.

La revisión de cuenta se realiza en **Azure Portal → Education → Información general**. En esta cuenta, Education Hub sí mostró el beneficio estudiantil, aunque el portal separado de Sponsorships no lo mostraba. El saldo y los identificadores personales se conservan de forma privada; no se publican en GitHub.

## Tarifas generales consultadas el 17/11/2026

Precios USD de la API oficial de Azure Retail Prices para `northcentralus`, consumo normal, sin Spot, Windows ni reservas:

| Componente previsto | Medidor | Tarifa general |
|---|---|---|
| Ubuntu `Standard_B2ats_v2` | B2ats v2, Virtual Machines Basv2 Series | USD 0.0094/h |
| IPv4 pública Standard regional | Standard IPv4 Static Public IP | USD 0.005/h |
| Disco Standard HDD, categoría S4 LRS | S4 LRS Disk | USD 1.536/mes |
| Operaciones S4 LRS | S4 LRS Disk Operations | USD 0.0005 por 10000 operaciones |

Con el diseño actual de disco de 30 GiB, se toma la categoría S4 para estimar. Usando 730 h/mes como conversión orientativa para ese disco, VM + IP + disco equivalen aproximadamente a **USD 0.0165/h**, **USD 0.40 por 24 h** o **USD 12.05 por 730 h**, antes de operaciones, tráfico u otros conceptos. Son estimaciones de tarifa general: una cuota gratuita aplicable puede reducirlas; no se contabiliza una cuota como confirmada sin revisar su medidor y uso en la cuenta.

Al desasignar la VM dejan de consumirse horas de cómputo, pero conservar IP y disco equivale aproximadamente a **USD 5.19 por 730 h**, más operaciones que correspondan. No se puede presentar la desasignación como eliminación de todo consumo.

El beneficio de disco P6 mostrado en servicios gratuitos no se aplica automáticamente al S4 del script. Cambiar tipo/tamaño requiere confirmar su elegibilidad, cuota restante y compatibilidad del SKU de VM. No se cambian recursos ajenos para aprovechar beneficios.

## Comprobaciones obligatorias antes de aplicar

1. DMZ/NSG seguros, SKU/cuota, conflictos y asociaciones: preflight completo.
2. Crédito vigente y saldo observado que cubra el presupuesto aprobado.
3. `subscriptionPolicies.spendingLimit == On` devuelto por Azure para la suscripción real.
4. Presupuesto y responsable aprobados, con ventana de pruebas y decisión sobre la conservación de IP/disco.

El despliegue ahora ejecuta `check_credit_guard.py` antes de la primera creación. Si Azure devuelve `Off`, `CurrentPeriodOff`, un valor desconocido, un error de lectura, un saldo insuficiente o una revisión de más de 24 horas, se detiene. No activa, retira ni modifica límites; tampoco actualiza el plan a pago por uso.

El monto aprobado **no es un corte automático de facturación**. La protección de gasto de Azure y el registro de presupuesto son controles distintos; el presupuesto requiere seguimiento de los recursos que permanezcan después de la prueba.

## Registro privado del saldo

```bash
cp config/credit-review.example.json config/credit-review.json
nano config/credit-review.json
```

Completar solamente valores observados: ID de la suscripción, hora UTC de revisión, fecha de vencimiento y un límite inferior conservador del saldo disponible. La revisión no autoriza por sí misma el consumo. No incluir contraseña, tokens, tarjetas ni claves. El archivo real se ignora por Git.

Después de aprobar el presupuesto, el comando de despliegue documentado vuelve a comprobar la política de gasto desde Azure. Si el proveedor no expone una protección confirmada, no se omite el control para cumplir una promesa de cero desembolso.

## Fuentes

- [Oferta oficial Azure for Students](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p/).
- [Crédito y uso en Education Hub](https://learn.microsoft.com/en-us/azure/education-hub/navigate-costs).
- [Protección de gasto](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit).
- [Tarifas y persistencia del cobro de IP pública](https://azure.microsoft.com/en-us/pricing/details/ip-addresses/).
- [API oficial Azure Retail Prices](https://prices.azure.com/api/retail/prices).
- [Azure CLI REST, consulta autenticada sin exportar tokens](https://learn.microsoft.com/en-us/cli/azure/reference-index?view=azure-cli-latest#az-rest).
