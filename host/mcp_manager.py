"""
mcp_manager.py

El Anfitrión (host) puede coordinar múltiples Clientes MCP, cada uno
hablando con un Servidor distinto (local o remoto). Este módulo:
    - Crea y conecta un MCPClient por cada servidor configurado.
    - Junta todas las herramientas expuestas por todos los servidores
      en una sola lista para pasársela al LLM.
    - Cuando el LLM pide usar una herramienta, encuentra a qué servidor
      pertenece y delega la llamada al MCPClient correspondiente.

Como dos servidores distintos podrían exponer una tool con el mismo
nombre, cada tool se expone al LLM con el nombre calificado
"<servidor>__<tool>", y se traduce de vuelta antes de invocar al
servidor real.
"""

from __future__ import annotations

from typing import Dict, List

from mcp_protocol.client import MCPClient


class MCPManager:
    def __init__(self, logger):
        self.logger = logger
        self.clients: Dict[str, MCPClient] = {}

    def add_server(self, name: str, transport) -> MCPClient:
        client = MCPClient(name=name, transport=transport, log_fn=self.logger.log)
        self.clients[name] = client
        return client

    def connect_all(self):
        for name, client in self.clients.items():
            print(f"\n>> Conectando con servidor MCP '{name}'...")
            client.connect()
            tool_names = [t["name"] for t in client.tools]
            print(f"   Herramientas disponibles: {tool_names}")

    def get_tools_for_llm(self) -> List[dict]:
        """Retorna todas las tools de todos los servidores, con nombre calificado."""
        all_tools = []
        for server_name, client in self.clients.items():
            for tool in client.tools:
                qualified = dict(tool)
                qualified["name"] = f"{server_name}__{tool['name']}"
                all_tools.append(qualified)
        return all_tools

    def call_tool(self, qualified_name: str, arguments: dict):
        server_name, _, tool_name = qualified_name.partition("__")
        if server_name not in self.clients:
            raise ValueError(f"Servidor MCP desconocido: {server_name}")
        return self.clients[server_name].call_tool(tool_name, arguments)

    def close_all(self):
        for client in self.clients.values():
            client.close()
