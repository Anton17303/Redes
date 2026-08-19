# Arquitectura y especificación del servidor MCP propio (car_rental)

## 1. Arquitectura general

```
┌─────────────────────────────── Anfitrión (host/) ───────────────────────────────┐
│                                                                                    │
│   Session (contexto)   MCPLogger (log JSON-RPC)      LLMClient (API Anthropic)    │
│                                                                                    │
│   MCPManager                                                                      │
│     ├── MCPClient "filesystem" ──stdio──> npx @modelcontextprotocol/server-fs     │
│     ├── MCPClient "git"        ──stdio──> uvx mcp-server-git                      │
│     └── MCPClient "car_rental" ──stdio o HTTP──> servers/car_rental{,_remote}     │
└────────────────────────────────────────────────────────────────────────────────┘
```

- El **Anfitrión** es `main.py` + el paquete `host/`.
- Cada **Cliente** (`mcp_protocol/client.py`, instanciado una vez por
  servidor) mantiene su propia conexión 1:1 con un **Servidor**.
- Los tres servidores exponen "tools" que, en conjunto, se le
  presentan al LLM como el parámetro `tools` de la API de Anthropic.
  Cuando el LLM decide usar una, el host la ejecuta contra el servidor
  correcto y le devuelve el resultado (bloque `tool_result`).

## 2. Especificación del servidor `car_rental`

**Caso de uso de industria:** agencia de renta de autos que ofrece un
chatbot para que los clientes busquen vehículos disponibles, consulten
detalles y hagan/cancelen reservaciones sin hablar con un agente
humano.

**Transporte:**
- Local: stdio (`servers/car_rental/server.py`)
- Remoto: HTTP, un único endpoint `POST /mcp` (`servers/car_rental_remote/app.py`)

**Protocolo:** JSON-RPC 2.0 sobre el formato estándar de MCP
(`initialize` → `notifications/initialized` → `tools/list` /
`tools/call`).

### 2.1 Herramientas expuestas

| Tool | Parámetros | Descripción |
|---|---|---|
| `search_cars` | `category?` (economico\|sedan\|suv\|van\|lujo), `min_seats?` (int), `max_price_per_day?` (number) | Busca autos disponibles según filtros opcionales. |
| `get_car_details` | `car_id` (string, requerido) | Retorna el detalle completo de un auto. |
| `create_reservation` | `car_id`, `customer_name`, `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD) — todos requeridos | Crea una reservación y marca el auto como no disponible. |
| `cancel_reservation` | `reservation_id` (string, requerido) | Cancela una reservación y libera el auto. |
| `list_reservations` | `customer_name?` (string) | Lista reservaciones, opcionalmente filtradas por cliente. |

### 2.2 Ejemplo de intercambio JSON-RPC completo

**1) Handshake**
```json
--> {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"uvg-redes-mcp-chatbot","version":"1.0.0"}}}
<-- {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18","capabilities":{"tools":{}},"serverInfo":{"name":"car-rental-mcp-server","version":"1.0.0"}}}
--> {"jsonrpc":"2.0","method":"notifications/initialized"}
```

**2) Listar herramientas**
```json
--> {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
<-- {"jsonrpc":"2.0","id":2,"result":{"tools":[ ... 5 tools ... ]}}
```

**3) Invocar una herramienta**
```json
--> {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_cars","arguments":{"category":"suv"}}}
<-- {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"Autos disponibles:\n- suv-001: ..."}],"isError":false}}
```

### 2.3 Endpoint remoto (HTTP)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Health check |
| POST | `/mcp` | Único endpoint MCP: recibe cualquier mensaje JSON-RPC (`initialize`, `tools/list`, `tools/call`, `notifications/initialized`) |

Headers relevantes:
- Request: `Content-Type: application/json`, `Mcp-Session-Id` (tras el primer `initialize`)
- Response: `Mcp-Session-Id` (asignado en la respuesta de `initialize`)

## 3. Errores JSON-RPC manejados

| Código | Significado | Cuándo se usa |
|---|---|---|
| -32700 | Parse error | JSON malformado |
| -32601 | Method not found | Método JSON-RPC desconocido (ej. typo en el `method`) |
| -32603 | Internal error | Excepción no controlada al ejecutar una tool |

Los errores de negocio (auto no encontrado, no disponible, etc.) **no**
se modelan como errores JSON-RPC, sino como resultados de
`tools/call` con `isError: true`, siguiendo la convención de MCP de
que el LLM debe poder leer el motivo del fallo y decidir cómo
continuar la conversación.
