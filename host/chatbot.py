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
    - Se llama al LLM (Gemini) con el historial completo + la lista de
      tools disponibles (agregadas de todos los servidores MCP), en el
      formato `functionDeclarations` que espera la API de Gemini.
    - Si el LLM responde con una o más `functionCall` dentro de
      `candidates[0].content.parts`, el host ejecuta esas herramientas
      contra el servidor MCP correspondiente y le devuelve el resultado
      al LLM como partes `functionResponse` en un nuevo turno "user"
      (protocolo de "function calling" de la API de Gemini), repitiendo
      hasta que el LLM entregue una respuesta final en texto.
"""

from __future__ import annotations

from host.llm_client import LLMClient, mcp_tools_to_gemini_format
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
        self.session.add_user_text(user_text)
        tools = mcp_tools_to_gemini_format(self.mcp.get_tools_for_llm())

        for _ in range(MAX_TOOL_ITERATIONS):
            response = self.llm.send(
                contents=self.session.as_list(),
                tools=tools,
                system=SYSTEM_PROMPT,
            )

            block_reason = response.get("promptFeedback", {}).get("blockReason")
            if block_reason:
                return f"[La solicitud fue bloqueada por seguridad: {block_reason}]"

            candidates = response.get("candidates", [])
            if not candidates:
                return "[El modelo no devolvió ninguna respuesta]"

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            self.session.add_model_parts(parts)

            function_calls = [p["functionCall"] for p in parts if "functionCall" in p]

            if not function_calls:
                text_parts = [p["text"] for p in parts if "text" in p]
                return "\n".join(text_parts).strip()

            # Ejecutar cada functionCall contra el servidor MCP correspondiente
            function_responses = []
            for call in function_calls:
                tool_name = call["name"]
                tool_args = call.get("args", {}) or {}

                print(f"  [tool_use] {tool_name}({tool_args})")
                try:
                    result = self.mcp.call_tool(tool_name, tool_args)
                    result_text = self._stringify_result(result)
                    response_payload = {"content": result_text}
                except Exception as exc:  # noqa: BLE001
                    response_payload = {"error": f"Error ejecutando la herramienta: {exc}"}

                function_responses.append(
                    {
                        "functionResponse": {
                            "name": tool_name,
                            "response": response_payload,
                        }
                    }
                )

            # Los resultados de las herramientas se envían de vuelta como un
            # turno "user" (ver Session.add_function_responses), y el ciclo
            # continúa: se vuelve a llamar al LLM con el nuevo contexto.
            self.session.add_function_responses(function_responses)

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
