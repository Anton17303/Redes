#!/usr/bin/env python3
"""
app.py

Servidor MCP REMOTO para el caso de uso "Car Rental Agency", expuesto
sobre HTTP en vez de stdio, implementado a mano (sin SDK de MCP).

Sigue la misma idea de "Streamable HTTP" de la especificación de MCP,
simplificada:
    - Un único endpoint: POST /mcp
    - El body es un mensaje JSON-RPC 2.0 (request o notification).
    - Si es una Request, se responde 200 con el JSON-RPC Response.
    - Si es una Notification, se responde 202 sin cuerpo.
    - En la respuesta de "initialize" se asigna un Mcp-Session-Id (uuid)
      que el cliente debe reenviar en las siguientes peticiones vía
      header. Esto es solo para fines demostrativos del curso; esta
      implementación no valida estrictamente la sesión.

Pensado para desplegarse en Google Cloud Run / Cloudflare Workers /
cualquier servicio que corra un contenedor HTTP (ver Dockerfile).
"""

from __future__ import annotations

import os
import uuid

from flask import Flask, jsonify, request

from logic import TOOL_DEFINITIONS, call_tool

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "car-rental-mcp-server-remote", "version": "1.0.0"}

app = Flask(__name__)


def make_result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def make_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "server": SERVER_INFO})


@app.route("/mcp", methods=["POST"])
def mcp_endpoint():
    msg = request.get_json(force=True, silent=False)
    method = msg.get("method")
    msg_id = msg.get("id")

    app.logger.info("MCP <- %s (id=%s)", method, msg_id)

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
        resp = jsonify(make_result(msg_id, result))
        resp.headers["Mcp-Session-Id"] = str(uuid.uuid4())
        return resp, 200

    if method == "notifications/initialized":
        return "", 202

    if method == "tools/list":
        return jsonify(make_result(msg_id, {"tools": TOOL_DEFINITIONS})), 200

    if method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = call_tool(tool_name, arguments)
        return jsonify(make_result(msg_id, result)), 200

    if msg_id is not None:
        return jsonify(make_error(msg_id, -32601, f"Method not found: {method}")), 200
    return "", 202


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
