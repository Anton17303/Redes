"""
logger.py

Mantiene y muestra un log de todas las solicitudes y respuestas
JSON-RPC intercambiadas con los servidores MCP (funcionalidad 3 del
proyecto). Cada entrada se guarda en memoria y se escribe también a un
archivo .jsonl (una entrada JSON por línea) para poder analizarla
después o compararla contra la captura de Wireshark.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List


class MCPLogger:
    def __init__(self, log_path: str = "mcp_interactions.log.jsonl", verbose: bool = True):
        self.log_path = log_path
        self.verbose = verbose
        self.entries: List[dict] = []
        # Empezar el archivo limpio en cada corrida
        open(self.log_path, "w", encoding="utf-8").close()

    def log(self, entry: dict):
        entry = dict(entry)
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.entries.append(entry)

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        if self.verbose:
            direction_arrow = "-->" if entry["direction"] == "send" else "<--"
            method = entry["message"].get("method", entry["message"].get("id", ""))
            print(f"  [MCP-LOG] [{entry['server']}] {direction_arrow} {method}")

    def show(self, n: int = 20):
        """Imprime las últimas n entradas del log de forma legible."""
        print(f"\n===== Últimas {n} interacciones MCP =====")
        for entry in self.entries[-n:]:
            print(f"[{entry['timestamp']}] server={entry['server']} dir={entry['direction']}")
            print(json.dumps(entry["message"], ensure_ascii=False, indent=2))
            print("-" * 60)
