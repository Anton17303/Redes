"""
chatbot.py

El Anfitrión (host). Orquesta:
    1) La conexión con el LLM a nivel de API (host/llm_client.py)
    2) El contexto de la conversación (host/session.py)
    3) El log de interacciones con servidores MCP (host/logger.py)
    4) Los múltiples Clientes MCP conectados a distintos Servidores
       (host/mcp_manager.py)

Ciclo por cada turno del usuario:
    - Se agrega el mensaje del usuario a la sesión.
    - Se llama al LLM con el historial completo + la lista de tools
      disponibles (agregadas de todos los servidores MCP).
    - Si el LLM responde con bloques `tool_use`, el host ejecuta esas
      herramientas contra el servidor MCP correspondiente y le
      devuelve el resultado al LLM (protocolo de "tool calling" de la
      API de Anthropic), repitiendo hasta que el LLM entregue una
      respuesta final en texto.
"""

from __future__ import annotations

from host.llm_client import LLMClient, mcp_tools_to_anthropic_format
from host.mcp_manager import MCPManager
from host.session import Session

SYSTEM_PROMPT = (
    "Eres un asistente que puede usar herramientas expuestas por servidores MCP "
    "(sistema de archivos, git, y un servicio de renta de autos). Usa las "
    "herramientas cuando el usuario lo requiera explícita o implícitamente. "
    "Responde de forma clara y concisa."
)


class Chatbot:
    def __init__(self, llm_client: LLMClient, mcp_manager: MCPManager, session: Session):
        self.llm = llm_client
        self.mcp = mcp_manager
        self.session = session

    def ask(self, user_text: str) -> str:
        self.session.add_user_message(user_text)
        tools = mcp_tools_to_anthropic_format(self.mcp.get_tools_for_llm())

        while True:
            response = self.llm.send(
                messages=self.session.as_list(),
                tools=tools,
                system=SYSTEM_PROMPT,
            )

            content_blocks = response.get("content", [])
            self.session.add_assistant_message(content_blocks)

            tool_use_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]

            if not tool_use_blocks:
                # Respuesta final: concatenar los bloques de texto
                text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
                return "\n".join(text_parts).strip()

            # Ejecutar cada tool_use contra el servidor MCP correspondiente
            tool_results = []
            for block in tool_use_blocks:
                tool_name = block["name"]
                tool_input = block.get("input", {})
                tool_use_id = block["id"]

                print(f"  [tool_use] {tool_name}({tool_input})")
                try:
                    result = self.mcp.call_tool(tool_name, tool_input)
                    result_text = self._stringify_result(result)
                    is_error = False
                except Exception as exc:  # noqa: BLE001
                    result_text = f"Error ejecutando la herramienta: {exc}"
                    is_error = True

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_text,
                        "is_error": is_error,
                    }
                )

            # El resultado de las herramientas se envía de vuelta como mensaje "user"
            self.session.add_user_message(tool_results)
            # y el ciclo continúa: se vuelve a llamar al LLM con el nuevo contexto

    @staticmethod
    def _stringify_result(result) -> str:
        if result is None:
            return ""
        if isinstance(result, dict) and "content" in result:
            # Formato MCP: content es una lista de bloques {type: "text", text: ...}
            parts = []
            for block in result["content"]:
                if block.get("type") == "text":
                    parts.append(block["text"])
            return "\n".join(parts) if parts else str(result)
        return str(result)
