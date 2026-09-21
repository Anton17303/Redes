"""
session.py

Mantiene el contexto de la conversación (funcionalidad 2 del proyecto):
si el usuario pregunta "¿Quién fue Alan Turing?" y luego "¿En qué fecha
nació?", el historial de mensajes permite que el LLM entienda a qué se
refiere la segunda pregunta.

El historial se guarda en el formato "Chat Completions" (OpenAI-
compatible, usado por Groq): una lista de mensajes
`{"role": "system"|"user"|"assistant"|"tool", ...}`, donde un mensaje
`assistant` puede incluir `tool_calls` (cuando el modelo pide ejecutar
una o más herramientas) y un mensaje `tool` es la respuesta a una de
esas llamadas, referenciada por `tool_call_id`.
"""

from __future__ import annotations

from typing import Any, List


class Session:
    def __init__(self, system_prompt: str | None = None):
        self.messages: List[dict] = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_user_message(self, text: str):
        self.messages.append({"role": "user", "content": text})

    def add_assistant_message(self, message: dict):
        """Agrega el mensaje del asistente tal como lo devolvió la API en
        `choices[0].message` (incluye `content` y, si aplica, `tool_calls`)."""
        self.messages.append(message)

    def add_tool_result(self, tool_call_id: str, content: str):
        self.messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "content": content}
        )

    def as_list(self) -> List[Any]:
        return self.messages

    def reset(self):
        system_messages = [m for m in self.messages if m.get("role") == "system"]
        self.messages = system_messages