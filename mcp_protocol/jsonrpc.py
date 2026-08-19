"""
jsonrpc.py

Implementación manual del formato de mensajes JSON-RPC 2.0.

Este módulo NO usa ninguna librería o SDK de MCP. Solo construye y
valida diccionarios Python que luego se serializan a JSON, siguiendo
estrictamente la especificación de JSON-RPC 2.0 (https://www.jsonrpc.org/).

MCP usa JSON-RPC 2.0 como formato de mensajes en la capa de aplicación.
Existen 3 tipos de mensajes:
    - Request:      tiene "id", espera una Response.
    - Notification:  NO tiene "id", no espera respuesta.
    - Response:      tiene "id" (igual al de la Request) y "result" o "error".
"""

from __future__ import annotations

import itertools
import json
from typing import Any, Optional


class JSONRPCError(Exception):
    """Representa un error JSON-RPC recibido de la contraparte."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.data = data

    @classmethod
    def from_dict(cls, error_obj: dict) -> "JSONRPCError":
        return cls(
            code=error_obj.get("code", -32603),
            message=error_obj.get("message", "Unknown error"),
            data=error_obj.get("data"),
        )


class IDGenerator:
    """Genera ids incrementales únicos para las requests salientes."""

    def __init__(self):
        self._counter = itertools.count(1)

    def next(self) -> int:
        return next(self._counter)


def make_request(request_id: int, method: str, params: Optional[dict] = None) -> dict:
    """Construye un mensaje Request de JSON-RPC 2.0."""
    msg = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params is not None:
        msg["params"] = params
    return msg


def make_notification(method: str, params: Optional[dict] = None) -> dict:
    """Construye un mensaje Notification de JSON-RPC 2.0 (sin id)."""
    msg = {
        "jsonrpc": "2.0",
        "method": method,
    }
    if params is not None:
        msg["params"] = params
    return msg


def make_result_response(request_id, result: Any) -> dict:
    """Construye una Response exitosa."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def make_error_response(request_id, code: int, message: str, data: Any = None) -> dict:
    """Construye una Response de error."""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def parse_message(raw: str) -> dict:
    """Parsea una línea de texto a un diccionario JSON-RPC, validando forma básica."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise JSONRPCError(-32700, f"Parse error: {exc}") from exc

    if msg.get("jsonrpc") != "2.0":
        raise JSONRPCError(-32600, "Invalid Request: missing/invalid 'jsonrpc' field")
    return msg


def is_response(msg: dict) -> bool:
    return "result" in msg or "error" in msg


def is_request(msg: dict) -> bool:
    return "method" in msg and "id" in msg


def is_notification(msg: dict) -> bool:
    return "method" in msg and "id" not in msg


# Códigos de error estándar de JSON-RPC 2.0
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
