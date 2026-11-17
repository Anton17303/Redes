#!/usr/bin/env python3
"""Validate the real Nginx config locally and render an isolated test browser.

This proves local behavior only, never public Azure availability. The temporary
server binds loopback and substitutes only the root path and the HTTP port.
"""
import argparse
import hashlib
import http.client
import json
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nginx-directory", type=Path, help="Distribución oficial Windows de nginx con conf/mime.types")
    parser.add_argument("--browser-executable", type=Path, help="Chromium de prueba; no usar perfil de Chrome del usuario")
    parser.add_argument("--output", type=Path, default=ROOT / "evidencias/local-render")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.nginx_directory:
        executable = args.nginx_directory / "nginx.exe"
        mime_types = args.nginx_directory / "conf/mime.types"
    else:
        executable = shutil.which("nginx")
        mime_types = Path("/etc/nginx/mime.types")
    if not executable or not Path(executable).is_file() or not mime_types.is_file():
        raise SystemExit("Nginx no disponible: indicar --nginx-directory o instalar nginx para la validación local")
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    report = {"scope": "LOCAL ONLY: loopback, not Azure", "port": port, "checks": []}
    with tempfile.TemporaryDirectory(prefix="cafenube-nginx-") as temporary:
        folder = Path(temporary)
        (folder / "logs").mkdir()
        (folder / "temp").mkdir()
        server = (ROOT / "config/nginx_cafenube.conf").read_text("utf-8")
        server = server.replace("listen 80 default_server;", f"listen 127.0.0.1:{port} default_server;")
        server = server.replace("root /var/www/cafenube;", f'root "{(ROOT / "web").as_posix()}";')
        config = (f'pid "{(folder / "nginx.pid").as_posix()}";\n'
                  f'error_log "{(folder / "error.log").as_posix()}";\nevents {{}}\n'
                  f'http {{ include "{mime_types.as_posix()}"; access_log off;\n'
                  + "".join(f'{directive}_temp_path "{(folder / directive).as_posix()}";\n'
                            for directive in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi"))
                  + server + "\n}\n")
        (folder / "nginx.conf").write_text(config, encoding="utf-8", newline="\n")
        command = [str(executable), "-p", folder.as_posix() + "/", "-c", "nginx.conf"]
        syntax = subprocess.run(command + ["-t"], capture_output=True, text=True)
        report["nginx_syntax"] = {"exit_code": syntax.returncode, "stderr": syntax.stderr}
        if syntax.returncode:
            raise RuntimeError(syntax.stderr)
        process = subprocess.Popen(command + ["-g", "daemon off;"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
        try:
            for attempt in range(30):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                        break
                except OSError:
                    time.sleep(0.1)
            for route, expected_status, source in (("/", 200, "web/index.html"), ("/styles.css", 200, "web/styles.css"),
                                                    ("/healthz", 200, None), ("/no-existe", 404, None), ("/.git/config", 403, None)):
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                connection.request("GET", route)
                response = connection.getresponse()
                body = response.read()
                assert response.status == expected_status, (route, response.status)
                if source:
                    assert body == (ROOT / source).read_bytes(), route
                elif route == "/healthz":
                    assert body == b"cafenube-ok\n"
                assert response.getheader("Server") == "nginx"
                assert response.getheader("X-Content-Type-Options") == "nosniff"
                assert response.getheader("X-Frame-Options") == "DENY"
                assert response.getheader("Content-Security-Policy")
                if route == "/styles.css":
                    assert "text/css" in response.getheader("Content-Type")
                report["checks"].append({"route": route, "status": response.status, "sha256": hashlib.sha256(body).hexdigest(), "result": "PASS"})
                connection.close()
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                options = {"headless": True}
                if args.browser_executable:
                    options["executable_path"] = str(args.browser_executable)
                browser = playwright.chromium.launch(**options)
                try:
                    for name, width, height in (("desktop", 1440, 1000), ("mobile", 390, 844), ("small-mobile", 320, 740)):
                        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                        requests = []
                        page.on("request", lambda request: requests.append(request.url))
                        page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
                        assert page.title() == "CaféNube | Café guatemalteco de especialidad"
                        assert page.locator("h1").count() == 1
                        assert page.locator("html").get_attribute("lang") == "es"
                        assert "Buen café. Buen origen." in page.inner_text("#nosotros")
                        assert "?" not in page.inner_text("body")
                        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), name
                        assert page.evaluate("[...document.querySelectorAll('a[href^=\"#\"]')].every(a => document.getElementById(a.hash.slice(1)))")
                        assert all(url.startswith(f"http://127.0.0.1:{port}/") for url in requests)
                        page.screenshot(path=str(args.output / f"preview-{name}.png"), full_page=True)
                        report["checks"].append({"viewport": name, "width": width, "height": height, "overflow": False, "result": "PASS"})
                        page.close()
                finally:
                    browser.close()
        finally:
            subprocess.run(command + ["-s", "quit"], capture_output=True, timeout=10)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
    (args.output / "local-web-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
