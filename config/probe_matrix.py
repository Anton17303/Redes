"""Injected TARGETS are numeric project endpoints, never shell commands."""
import json
import socket

results = {}
for host, port in TARGETS:
    try:
        with socket.create_connection((host, port), timeout=4):
            state = "OPEN"
    except ConnectionRefusedError:
        state = "REFUSED"
    except (TimeoutError, socket.timeout):
        state = "TIMEOUT"
    except OSError:
        state = "ERROR"
    results[f"{host}:{port}"] = state
print("CAFENUBE_MATRIX_JSON=" + json.dumps(results))
