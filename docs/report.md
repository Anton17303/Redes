# Reporte — Proyecto 1: Uso de un protocolo existente (CC3067 Redes)

**Nombre:** Alejandro Anton
**Fecha:** 21 de septiembre de 2026

> Este reporte cubre los incisos 8, 9 y 10 del enunciado. El proyecto
> se entrega en dos partes:
> - **Entrega parcial (esta):** incisos 8 y 10, alcance únicamente
>   LOCAL (Filesystem MCP, Git MCP, y el servidor propio `car_rental`
>   corriendo por stdio). El inciso 9 (Wireshark) **no aplica todavía**,
>   porque requiere el servidor remoto.
> - **Entrega final:** se agrega el servidor `car_rental` en su versión
>   REMOTA, se completa el inciso 9 con el análisis de Wireshark, y los
>   incisos 8 y 10 se amplían para incluir esa parte remota.

---

## Parte 1 — Entrega parcial (alcance local)

### 8. Especificación de los servidores MCP desarrollados (alcance local)

**a) Servidores oficiales usados**

| Servidor | Fuente | Transporte | Cómo se invoca |
|---|---|---|---|
| Filesystem MCP server | `@modelcontextprotocol/server-filesystem` (oficial, Anthropic) | stdio | `npx -y @modelcontextprotocol/server-filesystem <WORKSPACE_DIR>` |
| Git MCP server | `mcp-server-git` (oficial, Anthropic) | stdio | `uvx mcp-server-git` |

Ambos se integran al chatbot mediante el cliente MCP implementado a
mano en `mcp_protocol/client.py` (handshake `initialize` →
`notifications/initialized` → `tools/list`), sin usar ningún SDK de
MCP del lado del chatbot.

**b) Servidor propio: `car_rental` (versión local)**

- **Caso de uso de industria:** agencia de renta de autos (car
  rental). El chatbot permite a un cliente buscar vehículos
  disponibles, consultar el detalle de uno, crear una reservación,
  cancelarla o listar sus reservaciones.
- **Transporte:** stdio (`servers/car_rental/server.py`), implementado
  a mano: lee líneas JSON de `stdin`, responde líneas JSON por
  `stdout`, usa `stderr` solo para logging de diagnóstico.
- **Herramientas expuestas:**

| Tool | Parámetros | Descripción |
|---|---|---|
| `search_cars` | `category?`, `min_seats?`, `max_price_per_day?` | Busca autos disponibles según filtros opcionales |
| `get_car_details` | `car_id` (requerido) | Detalle completo de un auto |
| `create_reservation` | `car_id`, `customer_name`, `start_date`, `end_date` (todos requeridos) | Crea una reservación y marca el auto como no disponible |
| `cancel_reservation` | `reservation_id` (requerido) | Cancela una reservación y libera el auto |
| `list_reservations` | `customer_name?` | Lista reservaciones, opcionalmente filtradas por cliente |

- **Ejemplo de intercambio JSON-RPC real** (capturado del log de la
  aplicación, `mcp_interactions.log.jsonl`):

```json
--> {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"uvg-redes-mcp-chatbot","version":"1.0.0"}}}
<-- {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18","capabilities":{"tools":{}},"serverInfo":{"name":"car-rental-mcp-server","version":"1.0.0"}}}
--> {"jsonrpc":"2.0","method":"notifications/initialized"}
--> {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
<-- {"jsonrpc":"2.0","id":2,"result":{"tools":[ ... 5 tools ... ]}}
--> {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_cars","arguments":{"category":"suv"}}}
<-- {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"Autos disponibles:\n- suv-001: ..."}],"isError":false}}
```

> Ver `docs/architecture.md` para la especificación técnica completa
> (esquemas de entrada de cada tool, códigos de error JSON-RPC
> manejados, diagrama de arquitectura del host).

### 9. Análisis de la comunicación (Wireshark)

**No aplica en esta entrega.** El servidor `car_rental` corre
únicamente en local (stdio) por ahora; no hay tráfico de red que
capturar todavía. Este inciso se completa en la entrega final, cuando
`car_rental` esté desplegado como servidor remoto (ver
`docs/wireshark_analysis_template.md`).

### 10. Conclusiones y comentarios sobre el proyecto (avance local)

> _Borrador basado en lo observado durante el desarrollo — ajústalo a
> tu propia voz antes de entregarlo._

Implementar JSON-RPC a mano (sin ningún SDK de MCP) obliga a entender
el protocolo en un nivel que un SDK normalmente esconde: la diferencia
entre un *request* (tiene `id`, espera respuesta), una *notification*
(no tiene `id`, no espera respuesta — como
`notifications/initialized`) y una *response* (tiene `id` y
`result`/`error`) deja de ser un detalle abstracto y se vuelve algo
que hay que parsear y distinguir línea por línea. Usar los servidores
oficiales (Filesystem y Git) fue mucho más rápido que escribir el
propio desde cero — probé pedirle al chatbot crear un archivo y hacer
commit, y funcionó de punta a punta sin tener que tocar código del
servidor — pero también sirvió para confirmar que mi cliente MCP
(escrito a mano) es compatible con implementaciones de terceros, no
solo con mi propio servidor `car_rental`, que era justo el punto del
protocolo: interoperabilidad real entre cliente y servidor
independientemente de quién los escribió.

La mayor dificultad del lado del framing no fue tanto stdio en sí,
sino el "modo strict" de tool calling del LLM: cuando el modelo
mandaba `null` explícito para parámetros opcionales que no quería
usar, el proveedor del LLM rechazaba la llamada porque el JSON Schema
de la tool no declaraba esos campos como nullable. Hubo que ajustar
cómo se generan los schemas que se le pasan al modelo (agregando
`"null"` como tipo válido y metiendo todos los parámetros —incluso los
opcionales— en `required`) para que el ciclo LLM → tool → LLM no
tronara a medio camino.

Para la siguiente entrega, lo que espero resolver es la parte de
Wireshark contra el servidor remoto: sé que HTTPS va a cifrar todo el
tráfico por default, así que voy a necesitar `SSLKEYLOGFILE` desde el
principio para poder ver el JSON-RPC real y no solo tráfico TLS
opaco.

---

## Parte 2 — Entrega final (servidor remoto)

### 8. Especificación — ampliación con el servidor remoto

- **Plataforma de despliegue:** Google Cloud Run (proyecto
  `proyecto-redes-509217`, región `us-central1`), desplegado con
  `gcloud run deploy --source .` a partir del `Dockerfile` en
  `servers/car_rental_remote/`.
- **URL pública:**
  `https://car-rental-mcp-server-709686944502.us-central1.run.app`
  (endpoint MCP: `POST /mcp`).
- **Diferencias de transporte (HTTP vs stdio):** la versión local
  (`servers/car_rental/server.py`) lee/escribe líneas JSON-RPC
  directamente sobre los pipes `stdin`/`stdout` del proceso hijo que
  el host lanza. La versión remota (`servers/car_rental_remote/app.py`)
  expone el mismo conjunto de *tools* (`search_cars`,
  `get_car_details`, `create_reservation`, `cancel_reservation`,
  `list_reservations`) sobre un servidor HTTP: cada mensaje JSON-RPC
  (`initialize`, `tools/list`, `tools/call`, ...) se envía como el
  cuerpo de un `POST /mcp` y la respuesta llega como el cuerpo de un
  `200 OK`, en vez de como una línea más en un pipe. El host se
  conecta a uno u otro según la variable de entorno
  `CAR_RENTAL_REMOTE_URL` (implementado en `mcp_protocol/http_transport.py`
  vs `mcp_protocol/stdio_transport.py`), sin que el resto del código
  del chatbot (sesión, LLM, logging) note la diferencia — ambos
  transportes implementan la misma interfaz de cliente MCP.
- **Cifrado:** Cloud Run fuerza HTTPS; la conexión negocia TLS 1.3
  (`TLS_AES_256_GCM_SHA384`) con HTTP/2 sobre TLS (ALPN `h2`). Ver
  inciso 9 para el detalle completo.
- **Permisos de despliegue:** el proyecto de GCP requirió otorgar
  manualmente tres roles de IAM a la cuenta de servicio por defecto de
  Compute (`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`)
  antes de que `gcloud run deploy --source .` funcionara:
  `roles/storage.objectViewer` (leer el código fuente subido a Cloud
  Storage para el build), `roles/logging.logWriter` (que Cloud Build
  pudiera escribir sus logs) y `roles/artifactregistry.writer` (subir
  la imagen Docker construida a Artifact Registry). Sin estos tres
  roles, el deploy falla en distintos pasos (`storage.objects.get`
  denegado, luego sin permiso para logs, luego `failed to push`)
  aunque la cuenta sea dueña (`roles/owner`) del proyecto — son
  permisos separados que Cloud Build necesita para su propia cuenta de
  servicio, no para la del usuario.

### 9. Análisis de la comunicación (Wireshark)

Ver `docs/wireshark_analysis.md` (documento completo, ya lleno con la
captura real). Resumen:

- Se capturó tráfico real con Wireshark en la interfaz Wi-Fi (`wlo1`)
  mientras se enviaban tres peticiones MCP (`initialize`, `tools/list`,
  `tools/call`) al servidor remoto en Cloud Run.
- Como Cloud Run fuerza HTTPS, se exportó `SSLKEYLOGFILE` (con `curl`,
  que sí soporta esta variable de forma nativa) para poder descifrar
  el TLS en Wireshark y ver los mensajes JSON-RPC reales en texto
  plano.
- Se identificó y clasificó cada mensaje: sincronización TCP (3-way
  handshake), sincronización TLS (Client Hello/Server Hello), y las
  solicitudes/respuestas JSON-RPC de cada método.
- Se hizo el análisis por las 4 capas pedidas (enlace, red, transporte,
  aplicación), concluyendo que la pila real es
  `JSON-RPC → HTTP/2 → TLS 1.3 → TCP → IPv4 → Ethernet`, contra
  únicamente pipes `stdin`/`stdout` en la versión local (sin ninguna
  capa de red de por medio).

### 10. Conclusiones — ampliación

> _Borrador basado en las dificultades reales que surgieron durante el
> desarrollo de este proyecto — ajústalo a tu propia voz antes de
> entregarlo; es tuyo, no una reflexión inventada._

Lo que más trabajo me costó no fue escribir el protocolo MCP en sí
(una vez entendido JSON-RPC, el handshake `initialize` →
`notifications/initialized` → `tools/list` → `tools/call` es bastante
directo), sino todo lo que rodea a integrarlo con un LLM real y
desplegarlo en la nube. Cambié el LLM del chatbot dos veces durante el
proyecto (primero a Gemini, luego a Groq), y en ambos casos me topé
con que la documentación de "cómo se usa la API" no es suficiente:
cada proveedor tiene su propio formato de tool calling (`functionCall`
vs `tool_calls`), sus propios límites de tasa, y sus propios modelos
que se deprecan sin previo aviso (tuve que cambiar de modelo dos veces
por errores 404 de "modelo ya no disponible"). Aprendí que el "modo
strict" de tool calling en varios proveedores exige que todos los
parámetros —incluso los opcionales— aparezcan en `required`, y que la
forma de marcarlos como opcionales es permitiendo `null` en su tipo;
sin eso, el modelo terminaba mandando `tool_calls` que el propio
proveedor rechazaba por no cumplir su schema.

El despliegue a Google Cloud Run también me enseñó algo que no
esperaba: ser dueño (`roles/owner`) de un proyecto de GCP no es
suficiente para que `gcloud run deploy` funcione. Cloud Build usa su
propia cuenta de servicio, y esa cuenta necesita permisos explícitos
por separado (`storage.objectViewer` para leer el código fuente,
`logging.logWriter` para poder escribir sus propios logs, y
`artifactregistry.writer` para subir la imagen Docker construida) —
permisos que no vienen habilitados por default en un proyecto nuevo,
y que solo se descubren leyendo el log de cada build fallido uno por
uno.

La parte de Wireshark fue la que más paciencia requirió: entender que
Cloud Run cifra todo con TLS 1.3 y que Python (`requests`) no escribe
el archivo de `SSLKEYLOGFILE` automáticamente aunque la variable de
entorno esté exportada (a diferencia de `curl`, que sí lo hace de
forma nativa), y que Cloud Run reparte las conexiones entre varias IPs
de backend, así que filtrar por una sola IP fija no funciona — hay que
filtrar por el nombre del servidor (SNI) en el `Client Hello` en su
lugar. Una vez resuelto eso, ver el JSON-RPC real en texto plano
dentro de Wireshark —después de tanto tráfico cifrado— fue el momento
más satisfactorio del proyecto: confirmar con mis propios ojos que
"por debajo" de MCP remoto solo hay HTTP/2 sobre TLS sobre TCP, exactamente
como predice la teoría de capas del curso.

Si empezara de nuevo, elegiría un solo proveedor de LLM desde el
inicio (evitando la migración doble) y prepararía el `SSLKEYLOGFILE`
desde la primera prueba contra el servidor remoto, en vez de
descubrir a mitad del proyecto que Python no lo soporta igual que
`curl`.

---

*Este reporte se complementa con la presentación oral, donde se deben
cubrir: características implementadas, dificultades y lecciones
aprendidas, según el enunciado del proyecto.*
