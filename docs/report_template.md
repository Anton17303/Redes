# Reporte — Proyecto 1: Uso de un protocolo existente (CC3067 Redes)

**Nombre:** Alejandro _______________
**Fecha:** _______________

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

- ¿Qué aprendiste sobre MCP y JSON-RPC al implementarlo manualmente
  (sin SDK) hasta este punto?
- ¿Qué tan práctico resultó usar los servidores oficiales (filesystem,
  git) comparado con implementar el tuyo propio desde cero?
- ¿Qué dificultades tuviste con el handshake, el framing de mensajes
  por stdio, o el manejo de tools/list y tools/call?
- ¿Qué esperas resolver o mejorar en la siguiente entrega (servidor
  remoto + Wireshark)?

---

## Parte 2 — Entrega final (se completa después, con el servidor remoto)

*(No llenar todavía — esta sección se agrega cuando `car_rental_remote`
esté desplegado.)*

### 8. Especificación — ampliación con el servidor remoto
- URL de despliegue: _______________
- Diferencias de transporte (HTTP vs stdio):

### 9. Análisis de la comunicación (Wireshark)
> Ver `docs/wireshark_analysis_template.md` completo, con la captura
> real y el análisis por capa (enlace, red, transporte, aplicación).

### 10. Conclusiones — ampliación
- Diferencias entre depurar/probar un servidor local vs uno remoto.
- Lecciones aprendidas del despliegue a la nube.
- Lecciones aprendidas del análisis con Wireshark.

---

*Este reporte se complementa con la presentación oral, donde se deben
cubrir: características implementadas, dificultades y lecciones
aprendidas, según el enunciado del proyecto.*
