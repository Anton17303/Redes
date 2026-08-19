"""
stdio_transport.py

Transporte STDIO para servidores MCP locales, implementado a mano.

Según la especificación de MCP, el transporte stdio funciona así:
    - El cliente lanza al servidor como subproceso.
    - Cada mensaje JSON-RPC se envía como una línea de texto (UTF-8)
      terminada en '\n' por stdin/stdout.
    - Los mensajes NUNCA deben contener saltos de línea embebidos
      (se serializa el JSON en una sola línea).
    - stderr del servidor puede usarse libremente para logging, y no
      forma parte del protocolo.

No se usa ningún SDK de MCP: la lectura/escritura se hace directamente
sobre los pipes del subproceso con el módulo estándar `subprocess`.
"""

from __future__ import annotations

import json
import subprocess
import threading
from queue import Queue, Empty
from typing import List, Optional


class StdioTransport:
    """Administra un subproceso servidor MCP y el intercambio de mensajes."""

    def __init__(self, command: List[str], cwd: Optional[str] = None, env: Optional[dict] = None):
        self.command = command
        self._proc: Optional[subprocess.Popen] = None
        self._cwd = cwd
        self._env = env
        self._incoming: "Queue[dict]" = Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None

    def start(self):
        self._proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
            cwd=self._cwd,
            env=self._env,
        )
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        self._stderr_thread = threading.Thread(target=self._stderr_loop, daemon=True)
        self._stderr_thread.start()

    def _read_loop(self):
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._incoming.put(msg)

    def _stderr_loop(self):
        assert self._proc is not None and self._proc.stderr is not None
        for line in self._proc.stderr:
            # stderr del servidor no es parte del protocolo; solo se
            # muestra como diagnóstico.
            print(f"[server-stderr] {line.rstrip()}")

    def send(self, message: dict):
        assert self._proc is not None and self._proc.stdin is not None
        line = json.dumps(message, ensure_ascii=False)
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()

    def receive(self, timeout: float = 15.0) -> dict:
        try:
            return self._incoming.get(timeout=timeout)
        except Empty as exc:
            raise TimeoutError("Timeout esperando respuesta del servidor MCP (stdio)") from exc

    def close(self):
        if self._proc is None:
            return
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
        except Exception:
            pass
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
