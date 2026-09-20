"""
session.py

Mantiene el contexto de la conversación (funcionalidad 2 del proyecto):
si el usuario pregunta "¿Quién fue Alan Turing?" y luego "¿En qué fecha
nació?", el historial de mensajes permite que el LLM entienda a qué se
refiere la segunda pregunta.

El historial se guarda en el formato `contents` de la API de Gemini:
una lista de turnos `{"role": "user" | "model", "parts": [...]}`, donde
cada `part` puede ser texto (`{"text": ...}`), una llamada a función que
hizo el modelo (`{"functionCall": {...}}`) o el resultado de una función
que le devolvemos al modelo (`{"functionResponse": {...}}`).
"""

from __future__ import annotations

from typing import Any, List


class Session:
    def __init__(self):
        self.contents: List[dict] = []

    def add_user_text(self, text: str):
        self.contents.append({"role": "user", "parts": [{"text": text}]})

    def add_model_parts(self, parts: List[dict]):
        """Agrega el turno del modelo (texto y/o functionCall) tal como lo
        devolvió la API en `candidates[0].content.parts`."""
        self.contents.append({"role": "model", "parts": parts})

    def add_function_responses(self, responses: List[dict]):
        """`responses` es una lista de parts `{"functionResponse": {...}}`,
        una por cada `functionCall` que el modelo pidió ejecutar en su
        último turno. Se envían de vuelta como un turno "user", que es como
        la API de Gemini espera recibir los resultados de las funciones."""
        self.contents.append({"role": "user", "parts": responses})

    def as_list(self) -> List[Any]:
        return self.contents

    def reset(self):
        self.contents = []
