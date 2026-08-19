#!/usr/bin/env python3
"""
main.py

Punto de entrada del chatbot en consola (Anfitrión MCP).

Uso:
    python main.py

Configuración (ver .env.example):
    ANTHROPIC_API_KEY       Requerida.
    ANTHROPIC_MODEL         Opcional (default: claude-sonnet-4-6)
    WORKSPACE_DIR           Carpeta que expone el Filesystem MCP server (default: ./workspace)
    CAR_RENTAL_REMOTE_URL   Si se define, usa el servidor de renta de autos REMOTO
                            (https://...) en vez del local (stdio).
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from host.chatbot import Chatbot
from host.llm_client import LLMClient
from host.logger import MCPLogger
from host.mcp_manager import MCPManager
from host.session import Session
from mcp_protocol.http_transport import HTTPTransport
from mcp_protocol.stdio_transport import StdioTransport

load_dotenv()

WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", os.path.join(os.getcwd(), "workspace"))
CAR_RENTAL_REMOTE_URL = os.environ.get("CAR_RENTAL_REMOTE_URL")


def build_mcp_manager(logger: MCPLogger) -> MCPManager:
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    manager = MCPManager(logger)

    # --- Servidor oficial: Filesystem MCP server -------------------------
    # Requiere Node.js. Se lanza vía npx, sin necesidad de instalación previa.
    manager.add_server(
        "filesystem",
        StdioTransport(["npx", "-y", "@modelcontextprotocol/server-filesystem", WORKSPACE_DIR]),
    )

    # --- Servidor oficial: Git MCP server ---------------------------------
    # Requiere Python + `uv`/`uvx` (o pip install mcp-server-git).
    manager.add_server(
        "git",
        StdioTransport(["uvx", "mcp-server-git"]),
    )

    # --- Servidor propio: Car Rental (renta de autos) ---------------------
    if CAR_RENTAL_REMOTE_URL:
        print(f">> Usando servidor 'car_rental' REMOTO en {CAR_RENTAL_REMOTE_URL}")
        manager.add_server("car_rental", HTTPTransport(CAR_RENTAL_REMOTE_URL))
    else:
        print(">> Usando servidor 'car_rental' LOCAL (stdio)")
        manager.add_server(
            "car_rental",
            StdioTransport([sys.executable, os.path.join("servers", "car_rental", "server.py")]),
        )

    return manager


def main():
    logger = MCPLogger(log_path="mcp_interactions.log.jsonl", verbose=True)
    mcp_manager = build_mcp_manager(logger)
    mcp_manager.connect_all()

    llm_client = LLMClient(model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"))
    session = Session()
    chatbot = Chatbot(llm_client, mcp_manager, session)

    print("\n=========================================")
    print(" Chatbot MCP (Proyecto 1 - CC3067 Redes)")
    print(" Escribe 'salir' para terminar, 'log' para ver el log MCP")
    print("=========================================\n")

    try:
        while True:
            user_text = input("Tú: ").strip()
            if not user_text:
                continue
            if user_text.lower() in ("salir", "exit", "quit"):
                break
            if user_text.lower() == "log":
                logger.show()
                continue

            answer = chatbot.ask(user_text)
            print(f"\nBot: {answer}\n")
    except KeyboardInterrupt:
        pass
    finally:
        mcp_manager.close_all()
        print("\nSesión finalizada. Log guardado en mcp_interactions.log.jsonl")


if __name__ == "__main__":
    main()
