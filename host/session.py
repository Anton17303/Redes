"""
session.py

Mantiene el contexto de la conversación (funcionalidad 2 del proyecto):
si el usuario pregunta "¿Quién fue Alan Turing?" y luego "¿En qué fecha
nació?", el historial de mensajes permite que el LLM entienda a qué se
refiere la segunda pregunta.
"""

from __future__ import annotations

from typing import Any, List


class Session:
    def __init__(self):
        self.messages: List[dict] = []

    def add_user_message(self, content: Any):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: Any):
        self.messages.append({"role": "assistant", "content": content})

    def as_list(self) -> List[dict]:
        return self.messages

    def reset(self):
        self.messages = []
