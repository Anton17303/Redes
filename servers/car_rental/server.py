#!/usr/bin/env python3
"""
server.py

Servidor MCP LOCAL para el caso de uso "Car Rental Agency", implementado
a mano sobre el transporte stdio, SIN usar ningún SDK de MCP
(no FastMCP, no `mcp` package). Solo se usa `sys.stdin` / `sys.stdout`
y el módulo estándar `json`.

Protocolo (JSON-RPC 2.0 sobre stdio, un mensaje por línea):
    Cliente -> Servidor:  initialize
    Servidor -> Cliente:  result con protocolVersion/capabilities/serverInfo
    Cliente -> Servidor:  notifications/initialized   (sin respuesta)
    Cliente -> Servidor:  tools/list
    Servidor -> Cliente:  result con la lista de tools
    Cliente -> Servidor:  tools/call {name, arguments}
    Servidor -> Cliente:  result con {content: [...], isError}

stderr se usa libremente para logging de diagnóstico del servidor
(no es parte del protocolo).
"""

from __future__ import annotations

import json
import sys

from logic import TOOL_DEFINITIONS, call_tool

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "car-rental-mcp-server", "version": "1.0.0"}


def log(msg: str):
    print(f"[car-rental-server] {msg}", file=sys.stderr, flush=True)


def send(message: dict):
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def make_result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def make_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_message(msg: dict):
    method = msg.get("method")
    msg_id = msg.get("id")  # None si es notification

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
        send(make_result(msg_id, result))

    elif method == "notifications/initialized":
        log("Cliente confirmó inicialización.")
        # Es una notification: no se responde.

    elif method == "tools/list":
        send(make_result(msg_id, {"tools": TOOL_DEFINITIONS}))

    elif method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        log(f"tools/call -> {tool_name}({arguments})")
        result = call_tool(tool_name, arguments)
        send(make_result(msg_id, result))

    elif method == "shutdown":
        send(make_result(msg_id, {}))

    else:
        if msg_id is not None:
            send(make_error(msg_id, -32601, f"Method not found: {method}"))
        else:
            log(f"Notification desconocida ignorada: {method}")


def main():
    log("Servidor iniciado, esperando mensajes por stdin...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            log(f"Error de parseo JSON: {exc}")
            continue
        try:
            handle_message(msg)
        except Exception as exc:  # noqa: BLE001
            log(f"Error manejando mensaje: {exc}")
            if isinstance(msg, dict) and msg.get("id") is not None:
                send(make_error(msg["id"], -32603, str(exc)))


if __name__ == "__main__":
    main()
