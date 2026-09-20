"""
llm_client.py

Conexión con el LLM directamente a nivel de su API HTTP (funcionalidad 1
del proyecto: "Comprender cómo interactuar con un LLM a nivel de la
API"). Se usa la API de Gemini (Google AI Studio), endpoint
`POST /v1beta/models/{model}:generateContent`, con `requests` puro y
sin usar el SDK oficial `google-genai`, para dejar explícito el
formato de la petición/respuesta.

Documentación:
    https://ai.google.dev/gemini-api/docs/text-generation
    https://ai.google.dev/gemini-api/docs/function-calling
"""

from __future__ import annotations

import os
from typing import Any, List, Optional

import requests

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"

# Claves del JSON Schema (como las expone `inputSchema` de un servidor MCP)
# que la API de Gemini no acepta en `functionDeclarations.parameters` y que
# por lo tanto hay que remover antes de enviarlas.
_UNSUPPORTED_SCHEMA_KEYS = {
    "$schema",
    "additionalProperties",
    "examples",
    "title",
    "$id",
    "$ref",
    "$defs",
}


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "No se encontró GEMINI_API_KEY. Defínela como variable de entorno "
                "o en un archivo .env (ver .env.example)."
            )
        self.model = model

    def send(
        self,
        contents: List[dict],
        tools: Optional[List[dict]] = None,
        system: Optional[str] = None,
        max_output_tokens: int = 2048,
    ) -> dict:
        """Hace un request crudo a POST /v1beta/models/{model}:generateContent
        y retorna el JSON de respuesta."""
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "content-type": "application/json",
        }
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_output_tokens},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            body["tools"] = tools

        resp = requests.post(url, headers=headers, json=body, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")
        return resp.json()


def _sanitize_schema(schema: Any) -> Any:
    """Limpia un JSON Schema (tal como lo expone `tools/list` de un servidor
    MCP) para que sea aceptado como `parameters` de una `functionDeclaration`
    de Gemini: remueve palabras clave no soportadas y sanea recursivamente
    `properties` / `items`."""
    if not isinstance(schema, dict):
        return schema

    cleaned = {k: v for k, v in schema.items() if k not in _UNSUPPORTED_SCHEMA_KEYS}

    if "properties" in cleaned and isinstance(cleaned["properties"], dict):
        cleaned["properties"] = {
            key: _sanitize_schema(value) for key, value in cleaned["properties"].items()
        }
    if "items" in cleaned:
        cleaned["items"] = _sanitize_schema(cleaned["items"])

    # Gemini requiere que todo objeto tenga "type"; si el schema MCP lo omite
    # (algunos servidores lo hacen para objetos vacíos), se asume "object".
    cleaned.setdefault("type", "object")
    return cleaned


def mcp_tools_to_gemini_format(mcp_tools: List[dict]) -> List[dict]:
    """
    Convierte la lista de herramientas expuestas por servidores MCP
    (formato tools/list: name, description, inputSchema) al formato que
    espera la API de Gemini para "tools": una lista con un único elemento
    `{"functionDeclarations": [...]}`, donde cada declaración usa
    `parameters` (no `inputSchema`/`input_schema`) para el JSON Schema.
    """
    declarations = []
    for t in mcp_tools:
        schema = t.get("inputSchema") or {"type": "object", "properties": {}}
        declarations.append(
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": _sanitize_schema(schema),
            }
        )
    return [{"functionDeclarations": declarations}]
