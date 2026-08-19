"""
client.py

Cliente MCP implementado a mano sobre JSON-RPC 2.0 (sin SDKs de MCP).

Responsabilidades de un "Cliente" según el proyecto:
    - Mantener la conexión con UN servidor.
    - Realizar el handshake ("initialize" + notification "initialized").
    - Obtener la lista de herramientas ("tools/list").
    - Invocar herramientas ("tools/call").

Funciona sobre cualquier transporte que implemente:
    - send(message: dict) -> None                (stdio)
    - receive(timeout: float) -> dict             (stdio)
    - send_request(message: dict) -> dict | None  (http)

Para unificar ambos transportes, este cliente detecta el tipo de
transporte y adapta la forma en la que espera la respuesta.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from mcp_protocol import jsonrpc
from mcp_protocol.http_transport import HTTPTransport
from mcp_protocol.stdio_transport import StdioTransport

MCP_PROTOCOL_VERSION = "2025-06-18"

ClientInfo = {"name": "uvg-redes-mcp-chatbot", "version": "1.0.0"}


class MCPClient:
    def __init__(self, name: str, transport, log_fn: Optional[Callable[[dict], None]] = None):
        """
        name: identificador legible del servidor (ej. "filesystem", "git", "car_rental")
        transport: instancia de StdioTransport o HTTPTransport ya creada (no iniciada)
        log_fn: callback opcional para loggear cada mensaje JSON-RPC intercambiado
        """
        self.name = name
        self.transport = transport
        self.log_fn = log_fn or (lambda entry: None)
        self._ids = jsonrpc.IDGenerator()
        self.tools: List[dict] = []
        self._initialized = False

    # ------------------------------------------------------------------ #
    # Transporte
    # ------------------------------------------------------------------ #

    def _is_stdio(self) -> bool:
        return isinstance(self.transport, StdioTransport)

    def _log(self, direction: str, message: dict):
        self.log_fn({"server": self.name, "direction": direction, "message": message})

    def _call(self, method: str, params: Optional[dict] = None, is_notification: bool = False):
        """Envía un mensaje JSON-RPC y, si aplica, espera su respuesta."""
        if is_notification:
            msg = jsonrpc.make_notification(method, params)
        else:
            req_id = self._ids.next()
            msg = jsonrpc.make_request(req_id, method, params)

        self._log("send", msg)

        if self._is_stdio():
            self.transport.send(msg)
            if is_notification:
                return None
            response = self.transport.receive()
            self._log("recv", response)
            if "error" in response:
                raise jsonrpc.JSONRPCError.from_dict(response["error"])
            return response.get("result")
        else:
            response = self.transport.send_request(msg)
            if response is None:
                return None
            self._log("recv", response)
            if "error" in response:
                raise jsonrpc.JSONRPCError.from_dict(response["error"])
            return response.get("result")

    # ------------------------------------------------------------------ #
    # Ciclo de vida MCP
    # ------------------------------------------------------------------ #

    def connect(self):
        """Inicia el transporte (si aplica) y ejecuta el handshake MCP."""
        if self._is_stdio():
            self.transport.start()

        init_result = self._call(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": ClientInfo,
            },
        )

        # Notification obligatoria tras recibir la respuesta de initialize
        self._call("notifications/initialized", is_notification=True)
        self._initialized = True

        server_info = (init_result or {}).get("serverInfo", {})
        print(f"[MCPClient:{self.name}] Conectado a "
              f"{server_info.get('name', '?')} v{server_info.get('version', '?')}")

        self.refresh_tools()
        return init_result

    def refresh_tools(self) -> List[dict]:
        result = self._call("tools/list", {})
        self.tools = (result or {}).get("tools", [])
        return self.tools

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        result = self._call("tools/call", {"name": tool_name, "arguments": arguments})
        return result

    def close(self):
        try:
            self.transport.close()
        except Exception:
            pass
