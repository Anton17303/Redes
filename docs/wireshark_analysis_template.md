# Análisis de captura Wireshark — servidor MCP remoto (car_rental_remote)

> Este documento es una PLANTILLA. Debes completarla con tu propia
> captura real (`.pcapng`) hecha mientras tu chatbot conversa con el
> servidor `car_rental_remote` ya desplegado. No se incluye una
> captura real porque este entorno de desarrollo no tiene acceso a tu
> despliegue en la nube ni a tu interfaz de red.

## 1. Cómo generar la captura

1. Despliega `servers/car_rental_remote` (ver su README) y obtén su
   URL pública.
2. Abre Wireshark y empieza a capturar en la interfaz de red activa
   (ej. `wlan0`, `Wi-Fi`). Aplica el filtro:
   ```
   tcp.port == 443 && ip.addr == <IP del servidor remoto>
   ```
   (usa `nslookup`/`dig` sobre el hostname de tu despliegue para
   obtener la IP, o filtra por `http` si pruebas sin TLS en local).
3. Corre `python main.py` con `CAR_RENTAL_REMOTE_URL` apuntando a tu
   despliegue y ejecuta una conversación que dispare varias tools
   (`search_cars`, `create_reservation`, etc.).
4. Detén la captura y guárdala como `docs/capture_car_rental.pcapng`.

## 2. Clasificación de mensajes JSON-RPC observados

Completa esta tabla con los números de paquete (`No.`) de tu captura:

| # Paquete Wireshark | Frame TCP/TLS | Mensaje JSON-RPC | Tipo |
|---|---|---|---|
| _(pendiente)_ | SYN / SYN-ACK / ACK | — | Sincronización TCP (3-way handshake) |
| _(pendiente)_ | Client Hello / Server Hello / ... | — | Sincronización TLS (si usas HTTPS) |
| _(pendiente)_ | HTTP POST /mcp | `{"method":"initialize", "id":1, ...}` | Solicitud (Request) |
| _(pendiente)_ | HTTP 200 | `{"id":1,"result":{...}}` | Respuesta (Response) |
| _(pendiente)_ | HTTP POST /mcp | `{"method":"notifications/initialized"}` | Notificación (sin id, sin respuesta esperada) |
| _(pendiente)_ | HTTP POST /mcp | `{"method":"tools/list","id":2}` | Solicitud |
| _(pendiente)_ | HTTP 200 | `{"id":2,"result":{"tools":[...]}}` | Respuesta |
| _(pendiente)_ | HTTP POST /mcp | `{"method":"tools/call","id":3,...}` | Solicitud |
| _(pendiente)_ | HTTP 200 | `{"id":3,"result":{...}}` | Respuesta |
| _(pendiente)_ | FIN / ACK | — | Cierre de conexión TCP |

**Cómo distinguir cada tipo dentro de Wireshark:**
- Sigue el stream TCP completo con clic derecho → *Follow → HTTP
  Stream* (o *TLS Stream* si es HTTPS, requiere las llaves de sesión —
  ver sección 4).
- Los mensajes con `"id"` **y sin** `"result"`/`"error"` son Requests.
- Los mensajes con `"id"` **y con** `"result"`/`"error"` son Responses.
- Los mensajes **sin** `"id"` son Notifications.
- El *3-way handshake* (SYN, SYN-ACK, ACK) y, si aplica, el *TLS
  handshake* (Client Hello, Server Hello, Certificate, ...) son los
  mensajes de sincronización de las capas de transporte/aplicación,
  no forman parte de MCP en sí.

## 3. Análisis por capa (deliverable #9 del enunciado)

Completa cada sección explicando lo observado en tu propia captura.

### Capa de enlace
- ¿Qué protocolo de capa de enlace se observa (Ethernet, Wi-Fi/802.11)?
- Direcciones MAC origen/destino relevantes.

### Capa de red
- Direcciones IP origen (tu máquina) y destino (servidor remoto / IP
  del proveedor cloud).
- ¿IPv4 o IPv6? ¿Cuántos saltos aproximados (TTL)?

### Capa de transporte
- Puerto origen (efímero) y destino (443 para HTTPS, u 8080 si
  pruebas sin TLS).
- Evidencia del 3-way handshake (SYN → SYN/ACK → ACK) y del cierre
  (FIN/ACK o RST).
- Si usas HTTPS: evidencia del TLS handshake (Client Hello, Server
  Hello, Certificate, Change Cipher Spec, ...).

### Capa de aplicación
- Método HTTP (`POST /mcp`), headers relevantes (`Content-Type`,
  `Mcp-Session-Id`).
- Cuerpo JSON-RPC de cada request/response, relacionándolos con la
  tabla de la sección 2.

## 4. Nota sobre HTTPS y Wireshark

Si tu despliegue usa HTTPS (Cloud Run lo fuerza por defecto), el
cuerpo de las peticiones estará cifrado a nivel de TLS. Para poder
inspeccionar el JSON-RPC dentro de Wireshark tienes dos opciones:
1. Exportar la variable de entorno `SSLKEYLOGFILE` antes de correr
   `python main.py` y cargar ese archivo en Wireshark
   (*Preferences → Protocols → TLS → (Pre)-Master-Secret log filename*).
2. Probar temporalmente contra una copia local del servidor remoto
   sin TLS (`python app.py`, puerto 8080) para simplificar el análisis
   de la capa de aplicación, y documentar explícitamente que fue una
   prueba local sin cifrado.
