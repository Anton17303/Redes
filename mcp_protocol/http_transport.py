"""
http_transport.py

Transporte HTTP para servidores MCP remotos, implementado a mano
siguiendo la idea de "Streamable HTTP" de la especificación de MCP,
simplificado a request/response síncrono (sin SDK de MCP):

    - Un único endpoint HTTP (ej. POST https://<host>/mcp).
    - Cada mensaje JSON-RPC (request o notification) se envía como el
      body de un POST, con Content-Type: application/json.
    - El servidor responde con el JSON-RPC Response correspondiente
      (o 202 Accepted sin cuerpo si el mensaje era una notification).
    - El servidor puede asignar un identificador de sesión mediante el
      header "Mcp-Session-Id" en la respuesta al "initialize"; el
      cliente debe reenviar ese header en las siguientes peticiones.

Solo se usa la librería estándar/`requests` para hacer HTTP; NO se usa
ningún SDK de MCP.
"""

from __future__ import annotations

from typing import Optional

import requests


class HTTPTransport:
    """Cliente HTTP manual para hablar JSON-RPC con un servidor MCP remoto."""

    def __init__(self, base_url: str, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session_id: Optional[str] = None

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def send_request(self, message: dict) -> Optional[dict]:
        """Envía un Request/Notification JSON-RPC y retorna la Response (o None si era notification)."""
        resp = requests.post(
            f"{self.base_url}/mcp",
            json=message,
            headers=self._headers(),
            timeout=self.timeout,
        )
        # El servidor puede devolver un id de sesión en el handshake inicial
        if "Mcp-Session-Id" in resp.headers:
            self.session_id = resp.headers["Mcp-Session-Id"]

        if resp.status_code == 202:
            # Notification aceptada, sin cuerpo de respuesta
            return None

        resp.raise_for_status()
        if not resp.content:
            return None
        return resp.json()

    def close(self):
        # No hay conexión persistente que cerrar en este modelo simplificado.
        self.session_id = None
