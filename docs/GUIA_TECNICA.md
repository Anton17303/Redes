# Qué explicar y demostrar

1. **Componentes:** el proyecto implementa el sitio estático de Ventas, Nginx, inicialización Ubuntu, automatización y pruebas. La red, las reglas compartidas y el DNS privado se coordinan con sus dueños. Distinguir preparación local de despliegue real.
2. **DMZ:** aloja el servidor accesible desde Internet en un segmento separado de DNS/Intranet. Tener otra subred no basta: los NSGs de Azure permiten tráfico interno por defecto y hay que anularlo con reglas propias.
3. **Subneteo:** `/28` tiene 16 direcciones. Azure reserva 5; quedan 11 asignables, `.148` a `.158` dentro de `10.0.0.144/28`. No traslapa Data Center `.128/28`, que termina en `.143`.
4. **Ruta de una solicitud:** el cliente resuelve el FQDN público a la PIP; Azure entrega el tráfico a la IP privada de la NIC; el NSG decide; Nginx atiende TCP 80 y sirve HTML/CSS. El nombre público no depende del BIND interno.
5. **Puertos y protocolos:** HTTP es TCP 80; HTTPS usa TCP 443 y exige TLS/certificado; DNS puede usar UDP o TCP 53; SSH usa TCP 22. Esta entrega no tiene HTTPS. HTTP transporta el contenido sin cifrado y aquí no recibe credenciales ni pagos.
6. **Prioridad y estado:** número menor gana. `AllowVnetInBound/OutBound` tiene prioridad 65000. Las reglas propias deniegan antes. Los NSGs son stateful, así que la respuesta de una conexión permitida no es una nueva conexión iniciada desde la DMZ.
7. **Administración:** SSH solo desde TI; claves públicas, root y contraseña deshabilitados. Run Command se gestiona por el plano de control de Azure con permisos de la cuenta, sin abrir SSH a Internet. Esos permisos deben cuidarse también.
8. **Bootstrap:** cloud-init instala paquetes, escribe archivos y ejecuta el bootstrap. `web/` y la configuración son fuentes únicas. El generador no duplica manualmente HTML y limita el tamaño de custom-data. Un cloud-init fallido no equivale a un servidor publicado.
9. **Salida:** descargar paquetes requiere DNS y salida TCP 80/443. La PIP propia permite salida explícita; no se depende de la salida predeterminada de una subred privada. La NIC usa `168.63.129.16`, mientras que las redes RFC1918 se bloquean desde el guest y `VirtualNetwork` desde el NSG.
10. **Pruebas fiables:** un timeout puede significar bloqueo, ruta rota o servidor apagado. Primero demostrar que DNS/Intranet están sanos desde TI y después comprobar intentos desde DMZ y la regla Deny efectiva. Una respuesta `REFUSED` de BIND prueba que hubo conectividad, aunque la consulta no se autorizó.
11. **Idempotencia y propiedad:** se reutilizan únicamente recursos propios que coinciden con el diseño. Un recurso con otro propietario o una IP ocupada detiene la creación. Un fallo de permisos no se interpreta como ausencia. Reejecutar no actualiza cloud-init de una VM ya creada.
12. **Costos:** plan no crea recursos; aplicar exige presupuesto aprobado. El monto registrado no es un límite automático. Desasignar detiene el cómputo, pero quedan disco e IP. Nunca ejecutar una eliminación global del grupo para detener el servicio público.

## Demostración práctica

- Mostrar las fuentes del sitio y la configuración Nginx HTTP 80.
- Generar cloud-init y explicar cómo se mantiene sincronizado.
- Ejecutar el preflight y explicar el motivo exacto si se detiene.
- Si ya está desplegado: mostrar FQDN real, resolución y sitio desde Internet, estado Nginx, reglas efectivas y controles positivos/negativos.
- Explicar cada `FAIL`, `PENDING` o `INCONCLUSIVE` sin convertirlo en una prueba aprobada.
- Cerrar con la desasignación de la VM pública y comprobar su estado.
