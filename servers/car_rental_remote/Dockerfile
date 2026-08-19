# Dockerfile para desplegar el servidor MCP remoto (car_rental) en
# Google Cloud Run, Fly.io, Render, o cualquier plataforma que corra
# contenedores HTTP.
#
# Build local:
#   docker build -t car-rental-mcp-server .
#   docker run -p 8080:8080 car-rental-mcp-server
#
# Deploy a Google Cloud Run (desde este directorio):
#   gcloud run deploy car-rental-mcp-server \
#       --source . \
#       --region us-central1 \
#       --allow-unauthenticated

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:app"]
