# MCP Chatbot — CC3067 Redes, Proyecto 1

Console chatbot (Host) that talks to an LLM through the Anthropic API
and coordinates several **Model Context Protocol (MCP)** servers
(local and remote). The MCP protocol — JSON-RPC 2.0 messages, the
`initialize` handshake, `tools/list`, `tools/call` — is implemented
**by hand**, without using any MCP SDK (no `mcp` package, no
FastMCP), as required by the assignment.

## Features implemented

**General chatbot**
- [x] Connects to an LLM at the API level (raw HTTP requests to
      Anthropic's `POST /v1/messages`, see `host/llm_client.py`).
- [x] Keeps conversation context across turns (`host/session.py`).
- [x] Logs every JSON-RPC request/response exchanged with every MCP
      server, both to stdout and to `mcp_interactions.log.jsonl`
      (`host/logger.py`). Type `log` in the chat to print the log.

**MCP servers — official (local)**
- [x] [Filesystem MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)
      (`@modelcontextprotocol/server-filesystem`), scoped to `./workspace`.
- [x] [Git MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/git)
      (`mcp-server-git`).

**MCP servers — custom (own implementation)**
- [x] `servers/car_rental` — **local**, stdio transport, hand-rolled
      JSON-RPC server/client.
- [x] `servers/car_rental_remote` — **remote**, HTTP transport
      (Flask), deployable to Google Cloud Run. Same business logic,
      same tool set, only the transport differs.

**Protocol implementation**
- All JSON-RPC framing (`mcp_protocol/jsonrpc.py`), the stdio
  transport (`mcp_protocol/stdio_transport.py`), the HTTP transport
  (`mcp_protocol/http_transport.py`) and the MCP handshake/tool-calling
  client (`mcp_protocol/client.py`) are implemented from scratch on
  top of the standard library / `requests`, following the public MCP
  specification (https://modelcontextprotocol.io/specification/2025-06-18).

## Project structure

```
mcp-chatbot-project/
├── main.py                     # Entry point (console host)
├── host/
│   ├── chatbot.py              # LLM <-> tools orchestration loop
│   ├── llm_client.py           # Raw Anthropic Messages API client
│   ├── mcp_manager.py          # Manages multiple MCP clients/servers
│   ├── session.py              # Conversation context
│   └── logger.py               # MCP interaction logger
├── mcp_protocol/
│   ├── jsonrpc.py              # JSON-RPC 2.0 message helpers
│   ├── stdio_transport.py      # Manual stdio transport (local servers)
│   ├── http_transport.py       # Manual HTTP transport (remote servers)
│   └── client.py                # MCP client: handshake, tools/list, tools/call
├── servers/
│   ├── car_rental/              # Custom LOCAL MCP server (stdio)
│   │   ├── server.py
│   │   ├── logic.py             # Business logic (shared with remote)
│   │   └── catalog.json
│   └── car_rental_remote/       # Custom REMOTE MCP server (HTTP)
│       ├── app.py
│       ├── logic.py
│       ├── catalog.json
│       ├── Dockerfile
│       └── requirements.txt
└── docs/
    ├── architecture.md
    ├── report_template.md
    └── wireshark_analysis_template.md
```

## Requirements

- Python 3.10+
- Node.js 18+ and `npx` (to run the official Filesystem MCP server)
- `uv`/`uvx` (to run the official Git MCP server) — install with
  `pip install uv` or see https://docs.astral.sh/uv/getting-started/installation/
- An Anthropic API key (the free $5 credit is enough for this project)

## Installation

```bash
git clone <your-private-repo-url>
cd mcp-chatbot-project
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY
```

## Usage

```bash
python main.py
```

Example session:

```
Tú: crea un repositorio git en la carpeta actual, agrega un README que
    diga "Proyecto 1 Redes" y haz commit
Bot: (usa filesystem + git MCP servers para crear el archivo y el commit)

Tú: busca autos suv disponibles con precio menor a $60 por día
Bot: (usa car_rental MCP server) Autos disponibles: ...

Tú: resérvame el Hyundai Tucson del 1 al 5 de septiembre a nombre de Alejandro
Bot: (usa car_rental MCP server) Reservación creada con éxito...

Tú: log
(imprime el log de mensajes JSON-RPC intercambiados con los servidores)
```

## Using the remote car_rental server instead of the local one

See `servers/car_rental_remote/README.md` for deployment instructions
(Google Cloud Run). Once deployed:

```bash
export CAR_RENTAL_REMOTE_URL="https://<your-cloud-run-url>"
python main.py
```

## Custom MCP server specification (car_rental)

See `docs/architecture.md` for the full specification (tools,
parameters, JSON-RPC examples) of the custom `car_rental` MCP server,
covering deliverable #8 of the assignment.

## Notes on the manual protocol implementation

No MCP SDK is used anywhere in this project (client or server side).
`mcp_protocol/` implements JSON-RPC 2.0 framing, the `initialize` /
`notifications/initialized` handshake, `tools/list` and `tools/call`
directly on top of:
- `subprocess` pipes (stdin/stdout) for the stdio transport, and
- plain HTTP POST requests (`requests` library) for the HTTP transport.

The official Filesystem and Git MCP servers are used as-is (they are
pre-built binaries/servers, not SDKs the chatbot itself imports); the
chatbot's *client* side that talks to them is still the manual
implementation in `mcp_protocol/`.
