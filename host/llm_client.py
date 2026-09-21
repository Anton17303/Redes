"""
llm_client.py

Conexión con el LLM directamente a nivel de su API HTTP (funcionalidad 1
del proyecto: "Comprender cómo interactuar con un LLM a nivel de la
API"). Se usa la API de Groq (https://groq.com), que es gratuita (sin
tarjeta de crédito, ~14,400 requests/día en el tier gratuito) y expone
un endpoint compatible con el formato de "Chat Completions" de OpenAI,
incluyendo function/tool calling. Se usa `requests` puro, sin el SDK
oficial `groq`, para dejar explícito el formato de la petición/respuesta.

Documentación:
    https://console.groq.com/docs/api-reference#chat-create
    https://console.groq.com/docs/tool-use
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, List, Optional

import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
MAX_RATE_LIMIT_RETRIES = 5


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "No se encontró GROQ_API_KEY. Defínela como variable de entorno "
                "o en un archivo .env (ver .env.example). Se obtiene gratis en "
                "https://console.groq.com/keys"
            )
        self.model = model

    def send(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        max_tokens: int = 2048,
    ) -> dict:
        """Hace un request crudo a POST /openai/v1/chat/completions (formato
        Chat Completions de OpenAI, servido por Groq) y retorna el JSON de
        respuesta."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            resp = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=60)
            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429 and attempt < MAX_RATE_LIMIT_RETRIES:
                wait_seconds = self._parse_retry_after(resp)
                print(
                    f"  [rate_limit] Groq pidió esperar ~{wait_seconds:.1f}s "
                    f"(intento {attempt + 1}/{MAX_RATE_LIMIT_RETRIES})..."
                )
                time.sleep(wait_seconds)
                continue

            raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text}")

        raise RuntimeError("Groq API: se agotaron los reintentos por rate limit (429).")

    @staticmethod
    def _parse_retry_after(resp: requests.Response) -> float:
        """Extrae cuántos segundos hay que esperar antes de reintentar. Groq
        manda el header estándar `Retry-After`, y además lo repite en el
        mensaje de error (ej. "Please try again in 3.585s")."""
        header_value = resp.headers.get("Retry-After")
        if header_value:
            try:
                return max(float(header_value), 0.5)
            except ValueError:
                pass

        match = re.search(r"try again in ([\d.]+)s", resp.text)
        if match:
            return max(float(match.group(1)), 0.5) + 0.5  # pequeño margen

        return 5.0  # fallback razonable si no se pudo parsear


def _make_strict_nullable(schema: Any) -> Any:
    """El modelo (openai/gpt-oss-120b vía Groq) usa el modo "strict" de
    tool calling: en vez de omitir parámetros opcionales que decide no
    usar, los manda explícitamente como `null`. Para que eso sea válido,
    el JSON Schema tiene que declarar TODAS las propiedades en
    `required` (convención de OpenAI Structured Outputs en modo strict)
    y, para las que son opcionales de verdad, permitir `null` en su
    `type` (y agregarlo al `enum`, si tiene uno). Sin este ajuste, Groq
    rechaza el tool call con "value must be one of [...]" o "expected
    string, but got null"."""
    if not isinstance(schema, dict):
        return schema

    schema = dict(schema)
    original_required = set(schema.get("required", []))

    if "properties" in schema and isinstance(schema["properties"], dict):
        new_props = {}
        for key, subschema in schema["properties"].items():
            subschema = _make_strict_nullable(subschema)
            if key not in original_required and isinstance(subschema, dict):
                subschema = dict(subschema)
                if "type" in subschema:
                    t = subschema["type"]
                    if isinstance(t, str) and t != "null":
                        subschema["type"] = [t, "null"]
                    elif isinstance(t, list) and "null" not in t:
                        subschema["type"] = [*t, "null"]
                if "enum" in subschema and None not in subschema["enum"]:
                    subschema["enum"] = [*subschema["enum"], None]
            new_props[key] = subschema
        schema["properties"] = new_props
        # Modo strict: TODAS las propiedades van en "required"; lo que
        # antes era "opcional" ahora se expresa solo por aceptar null.
        schema["required"] = list(schema["properties"].keys())

    return schema


def mcp_tools_to_openai_format(mcp_tools: List[dict]) -> List[dict]:
    """
    Convierte la lista de herramientas expuestas por servidores MCP
    (formato tools/list: name, description, inputSchema) al formato
    "tools" de la API de Chat Completions (OpenAI-compatible, usado por
    Groq): una lista de `{"type": "function", "function": {...}}`, donde
    cada una usa `parameters` (no `inputSchema`) para el JSON Schema.
    """
    out = []
    for t in mcp_tools:
        schema = t.get("inputSchema") or {"type": "object", "properties": {}}
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": _make_strict_nullable(schema),
                },
            }
        )
    return out