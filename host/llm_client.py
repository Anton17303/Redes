"""
llm_client.py

Conexión con el LLM directamente a nivel de su API HTTP (funcionalidad 1
del proyecto: "Comprender cómo interactuar con un LLM a nivel de la
API"). Se usa la API de Mensajes de Anthropic (POST /v1/messages) con
requests puro, sin usar el SDK oficial `anthropic`, para dejar explícito
el formato de la petición/respuesta.

Documentación: https://docs.claude.com/en/api/messages
"""

from __future__ import annotations

import os
from typing import Any, List, Optional

import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-6"


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "No se encontró ANTHROPIC_API_KEY. Defínela como variable de entorno "
                "o en un archivo .env (ver .env.example)."
            )
        self.model = model

    def send(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 1500,
    ) -> dict:
        """Hace un request crudo a POST /v1/messages y retorna el JSON de respuesta."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = tools

        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=body, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Anthropic API error {resp.status_code}: {resp.text}")
        return resp.json()


def mcp_tools_to_anthropic_format(mcp_tools: List[dict]) -> List[dict]:
    """
    Convierte la lista de herramientas expuestas por un servidor MCP
    (formato tools/list: name, description, inputSchema) al formato que
    espera la API de Anthropic para "tools" (name, description, input_schema).
    """
    converted = []
    for t in mcp_tools:
        converted.append(
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("inputSchema", {"type": "object", "properties": {}}),
            }
        )
    return converted
