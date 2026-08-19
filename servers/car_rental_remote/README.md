# Car Rental MCP Server — Remote (HTTP)

Same business logic as `servers/car_rental` (local, stdio), exposed
over HTTP instead, so it can be deployed to a cloud provider (Google
Cloud Run, Fly.io, Render, Cloudflare, etc.) and used by the chatbot
as a **remote** MCP server (functionality 6 of the project).

The MCP JSON-RPC protocol is implemented by hand on top of Flask
(`app.py`) — no MCP SDK is used. Only one endpoint is exposed:

```
POST /mcp
```

Every request/notification is sent as a JSON-RPC 2.0 message in the
body. The server replies:
- `200 OK` + JSON-RPC response, for requests (`initialize`, `tools/list`, `tools/call`).
- `202 Accepted` (empty body), for notifications (`notifications/initialized`).

On `initialize`, the server returns an `Mcp-Session-Id` header that a
well-behaved client should resend on subsequent calls.

## Run locally

```bash
pip install -r requirements.txt
python app.py
# Server listening on http://localhost:8080
```

## Deploy to Google Cloud Run

```bash
gcloud auth login
gcloud config set project <YOUR_PROJECT_ID>
gcloud run deploy car-rental-mcp-server \
    --source . \
    --region us-central1 \
    --allow-unauthenticated
```

Cloud Run will build the `Dockerfile` and give you a public HTTPS URL,
e.g. `https://car-rental-mcp-server-xxxxx-uc.a.run.app`.

## Use it from the chatbot

Set the environment variable before running the host:

```bash
export CAR_RENTAL_REMOTE_URL="https://car-rental-mcp-server-xxxxx-uc.a.run.app"
python main.py
```

The host (`host/mcp_manager.py`) will then talk to this server via
`mcp_protocol/http_transport.py` instead of spawning the local stdio
process.
