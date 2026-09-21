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
    - Se llama al LLM (Groq, API compatible con OpenAI Chat Completions)
      con el historial completo + la lista de tools disponibles
      (agregadas de todos los servidores MCP), en el formato
      `{"type": "function", "function": {...}}` que espera la API.
    - Si el LLM responde con uno o más `tool_calls` dentro de
      `choices[0].message`, el host ejecuta esas herramientas contra el
      servidor MCP correspondiente y le devuelve el resultado al LLM
      como mensajes `role: "tool"` (uno por cada `tool_call_id`),
      repitiendo hasta que el LLM entregue una respuesta final en texto.
"""

from __future__ import annotations

import json

from host.llm_client import LLMClient, mcp_tools_to_openai_format
from host.mcp_manager import MCPManager
from host.session import Session

SYSTEM_PROMPT = (
    "Eres un asistente que puede usar herramientas expuestas por servidores MCP "
    "(sistema de archivos, git, y un servicio de renta de autos). Usa las "
    "herramientas cuando el usuario lo requiera explícita o implícitamente. "
    "Responde de forma clara y concisa."
)

# Límite de vueltas del ciclo LLM -> tools -> LLM por cada pregunta del
# usuario, para evitar un loop infinito si el modelo insiste en llamar
# herramientas indefinidamente.
MAX_TOOL_ITERATIONS = 10


class Chatbot:
    def __init__(self, llm_client: LLMClient, mcp_manager: MCPManager, session: Session):
        self.llm = llm_client
        self.mcp = mcp_manager
        self.session = session

    def ask(self, user_text: str) -> str:
        self.session.add_user_message(user_text)
        tools = mcp_tools_to_openai_format(self.mcp.get_tools_for_llm())

        for _ in range(MAX_TOOL_ITERATIONS):
            response = self.llm.send(messages=self.session.as_list(), tools=tools)

            choices = response.get("choices", [])
            if not choices:
                return "[El modelo no devolvió ninguna respuesta]"

            message = choices[0].get("message", {})
            self.session.add_assistant_message(message)

            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                return (message.get("content") or "").strip()

            # Ejecutar cada tool_call contra el servidor MCP correspondiente
            for call in tool_calls:
                fn = call.get("function", {})
                tool_name = fn.get("name")
                try:
                    tool_args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    tool_args = {}
                # El modelo a veces manda `null` explícito para parámetros
                # opcionales que decidió no usar; los quitamos para que la
                # herramienta reciba solo los argumentos que sí especificó.
                tool_args = {k: v for k, v in tool_args.items() if v is not None}

                print(f"  [tool_use] {tool_name}({tool_args})")
                try:
                    result = self.mcp.call_tool(tool_name, tool_args)
                    result_text = self._stringify_result(result)
                except Exception as exc:  # noqa: BLE001
                    result_text = f"Error ejecutando la herramienta: {exc}"

                # Cada resultado se envía de vuelta como un mensaje
                # role="tool", referenciando el tool_call_id que le
                # corresponde (así lo espera la API de Chat Completions).
                self.session.add_tool_result(call["id"], result_text)

            # El ciclo continúa: se vuelve a llamar al LLM con el nuevo
            # contexto (incluyendo los resultados de las herramientas).

        return "[Se alcanzó el número máximo de llamadas a herramientas para esta pregunta]"

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