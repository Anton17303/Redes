# Análisis de captura Wireshark — servidor MCP remoto (car_rental_remote)

## 0. Metodología de la captura

El servidor `car_rental_remote` está desplegado en **Google Cloud Run**
(`https://car-rental-mcp-server-709686944502.us-central1.run.app`), que
fuerza HTTPS. Para poder inspeccionar el contenido JSON-RPC (y no solo
tráfico TLS cifrado), se generó la captura de la siguiente forma:

1. Se exportó la variable de entorno `SSLKEYLOGFILE` en la terminal:
   ```bash
   export SSLKEYLOGFILE=$(pwd)/sslkeys.log
   ```
   (Se comprobó que `curl` respeta esta variable de forma nativa —
   Python/`requests` no lo hace automáticamente sin cambios de código
   — así que las tres peticiones MCP se replicaron con `curl` en la
   misma terminal, contra el mismo endpoint `/mcp` que usa el
   chatbot.)
2. Con Wireshark capturando en la interfaz Wi-Fi (`wlo1`), se
   ejecutaron tres peticiones JSON-RPC reales contra el servidor
   remoto: `initialize`, `tools/list` y `tools/call` (`search_cars`).
   Cada una abrió una conexión TCP/TLS nueva (Cloud Run reparte el
   tráfico entre varias IPs de backend: `34.143.75.2`, `34.143.77.2`,
   `34.143.79.2`).
3. Se cargó `sslkeys.log` en Wireshark
   (*Edit → Preferences → Protocols → TLS → (Pre)-Master-Secret log
   filename*), lo que permitió descifrar el tráfico TLS 1.3 y ver el
   HTTP/2 + JSON-RPC en texto plano.
4. Se guardó la captura completa como `captura_redes.pcapng`.

Detalles de la sesión TLS negociada (las tres conexiones son
idénticas en esto):
- **TLS 1.3**, cipher suite `0x1302` = `TLS_AES_256_GCM_SHA384`.
- **ALPN**: el cliente ofrece `h2, http/1.1`; el servidor elige `h2`
  (HTTP/2), confirmado por el preface `PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n`
  al inicio de los datos de aplicación descifrados.

## 1. Las tres conexiones capturadas

| Stream TCP | IP destino (backend Cloud Run) | Puerto origen | Mensaje MCP |
|---|---|---|---|
| 3  | 34.143.75.2 | 40548 | `initialize` |
| 12 | 34.143.77.2 | 44174 | `tools/list` |
| 16 | 34.143.79.2 | 42982 | `tools/call` (`search_cars`) |

Cada una es una conexión TCP/TLS **independiente** (Cloud Run no
reutiliza la conexión entre invocaciones separadas de `curl`), por lo
que las tres repiten el patrón completo: 3-way handshake → TLS
handshake → datos de aplicación (HTTP/2 + JSON-RPC) → cierre.

## 2. Clasificación de mensajes JSON-RPC observados

Usando el stream 3 (`initialize`) como ejemplo detallado — los otros
dos streams siguen exactamente el mismo patrón:

| # Paquete (frame) | Evento | Mensaje JSON-RPC | Tipo |
|---|---|---|---|
| 366 | `40548 → 443 [SYN]` | — | Sincronización TCP (3-way handshake, 1/3) |
| 374 | `443 → 40548 [SYN, ACK]` | — | Sincronización TCP (2/3) |
| 375 | `40548 → 443 [ACK]` | — | Sincronización TCP (3/3) |
| 377 | `Client Hello (SNI=car-rental-mcp-server-...)` | — | Sincronización TLS (1/2) |
| 385 | `Server Hello, Change Cipher Spec` | — | Sincronización TLS (2/2) |
| 391–393 | `Application Data` (cliente → servidor) | `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"wireshark-test","version":"1.0"}}}` | **Solicitud (Request)** |
| 404–406 | `Application Data` (servidor → cliente) | `{"id":1,"jsonrpc":"2.0","result":{"capabilities":{"tools":{}},"protocolVersion":"2025-06-18","serverInfo":{"name":"car-rental-mcp-server-remote","version":"1.0.0"}}}` | **Respuesta (Response)** |
| 412 | `40548 → 443 [FIN, ACK]` | — | Cierre TCP (cliente) |
| 424 | `443 → 40548 [FIN, ACK]` | — | Cierre TCP (servidor) |

> Nota: dentro de TLS 1.3, los primeros paquetes "Application Data"
> que manda el servidor tras el *Server Hello* (frame 387 en este
> stream) en realidad transportan el resto del handshake TLS cifrado
> (`Certificate`, `CertificateVerify`, `Finished`) — Wireshark los
> etiqueta igual que los datos de aplicación reales porque, a
> diferencia de TLS 1.2, en TLS 1.3 esos mensajes también van
> cifrados. El primer `Application Data` que contiene HTTP/2 real
> (el preface `PRI * HTTP/2.0`) es el que se identificó arriba.

Para `tools/list` (stream 12) y `tools/call` (stream 16) el patrón de
frames es idéntico; solo cambia el contenido JSON-RPC:

- **`tools/list`** — Request: `{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`.
  Response: incluye el arreglo completo de las 5 herramientas del
  servidor (`search_cars`, `get_car_details`, `create_reservation`,
  `cancel_reservation`, `list_reservations`) con su `inputSchema`
  completo.
- **`tools/call`** — Request:
  `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_cars","arguments":{}}}`.
  Response: `{"id":3,"jsonrpc":"2.0","result":{"content":[{"type":"text","text":"Autos disponibles:\n- eco-001: Toyota Yaris ... $25.00/día\n..."}],"isError":false}}`
  — el catálogo completo de 7 autos.

No se observó ninguna *notification* (mensaje sin `id`) en esta
captura porque las 3 peticiones se hicieron de forma aislada con
`curl`; en una conversación real del chatbot sí aparecería
`notifications/initialized` inmediatamente después de la respuesta a
`initialize`.

## 3. Análisis por capa

### Capa de enlace
- Protocolo: **Ethernet II** (interfaz Wi-Fi `wlo1`, encapsulada como
  Ethernet por el driver).
- MAC origen (equipo del alumno): `28:2e:89:1b:d6:18`.
- MAC destino: `00:09:0f:09:00:1d` (fabricante *Fortinet* — el
  gateway/firewall de la red local, no el servidor remoto: en una LAN
  con enrutamiento a Internet, la capa de enlace solo llega hasta el
  siguiente salto, no hasta el destino final).

### Capa de red
- **IPv4**. Origen: `10.100.17.178` (IP privada del equipo dentro de
  la red local). Destino: una de `34.143.75.2` / `34.143.77.2` /
  `34.143.79.2` (IPs públicas de los backends de Cloud Run — Google
  reparte las conexiones entre varias IPs de su infraestructura,
  probablemente vía un *load balancer* anycast).
- TTL de salida: 64 (valor típico de Linux). Cloud Run también expone
  registros DNS **AAAA** (IPv6, ej. `2600:1900:4240:200::`), pero en
  esta red la resolución usada fue IPv4.

### Capa de transporte
- **TCP**, puerto destino `443` (HTTPS) y puerto origen efímero
  distinto por conexión (`40548`, `44174`, `42982`).
- 3-way handshake completo y visible en cada stream: `SYN` → `SYN,ACK`
  → `ACK` (frames 366/374/375 en el stream de ejemplo).
- Cierre ordenado con `FIN,ACK` en ambos sentidos (frames 412 y 424).
- Encima de TCP corre **TLS 1.3**: `Client Hello` → `Server Hello +
  Change Cipher Spec` → intercambio de claves cifrado → `Change
  Cipher Spec + Application Data` del cliente (fin del handshake TLS
  de su lado). Cipher suite negociada: `TLS_AES_256_GCM_SHA384`.

### Capa de aplicación
- Encima de TLS corre **HTTP/2** (negociado vía la extensión ALPN del
  `Client Hello`, confirmado por el *connection preface* `PRI *
  HTTP/2.0\r\n\r\nSM\r\n\r\n` al inicio de los datos descifrados).
- Cada request es un `POST /mcp` con header `Content-Type:
  application/json` y cuerpo JSON-RPC 2.0 (`jsonrpc`, `id`, `method`,
  `params`). Cada response es un `200 OK` con cuerpo JSON-RPC
  (`jsonrpc`, `id`, `result`).
- El cuerpo JSON-RPC de cada mensaje se detalla en la sección 2.

## 4. Conclusión de esta sección

La captura confirma que el transporte real de MCP en modo remoto es:

```
JSON-RPC 2.0  (capa de aplicación del protocolo MCP en sí)
     │
   HTTP/2      (transporte del JSON-RPC — POST /mcp)
     │
   TLS 1.3     (cifrado, negociado vía ALPN: h2, TLS_AES_256_GCM_SHA384)
     │
    TCP        (puerto 443, 3-way handshake visible)
     │
    IPv4       (10.100.17.178 ↔ 34.143.7x.2, Cloud Run)
     │
   Ethernet    (capa de enlace local hasta el gateway Fortinet)
```

Esto contrasta con el servidor MCP **local** (`car_rental` sobre
stdio, y los servidores oficiales Filesystem/Git), donde no hay
ninguna de estas capas de red: los mensajes JSON-RPC se intercambian
directamente por los pipes `stdin`/`stdout` del proceso hijo.
