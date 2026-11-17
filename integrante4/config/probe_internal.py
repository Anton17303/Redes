#!/usr/bin/env python3
"""Identical service probes from DMZ and TI: distinguish responses from silence."""
import http.client
import json
import os
import socket
import struct


def dns_query(protocol):
    transaction = os.urandom(2)
    labels = "rrhh.cafenube.internal".split(".")
    packet = transaction + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    packet += b"".join(bytes([len(label)]) + label.encode("ascii") for label in labels) + b"\x00\x00\x01\x00\x01"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if protocol == "UDP" else socket.SOCK_STREAM)
    sock.settimeout(4)
    try:
        sock.connect(("10.0.0.132", 53))
        if protocol == "UDP":
            sock.send(packet)
            reply = sock.recv(4096)
        else:
            sock.sendall(struct.pack("!H", len(packet)) + packet)
            length_bytes = receive(sock, 2)
            reply = receive(sock, struct.unpack("!H", length_bytes)[0])
        if len(reply) < 12 or reply[:2] != transaction:
            return {"response": True, "healthy": False, "detail": "Respuesta DNS inválida"}
        rcode = reply[3] & 15
        answers = struct.unpack("!H", reply[6:8])[0]
        return {"response": True, "healthy": rcode == 0 and answers > 0 and socket.inet_aton("10.0.0.133") in reply,
                "rcode": rcode, "answers": answers}
    finally:
        sock.close()


def receive(sock, length):
    result = b""
    while len(result) < length:
        chunk = sock.recv(length - len(result))
        if not chunk:
            raise ConnectionError("Respuesta TCP incompleta")
        result += chunk
    return result


def http_query():
    connection = http.client.HTTPConnection("10.0.0.133", 80, timeout=4)
    try:
        connection.request("GET", "/", headers={"Host": "rrhh.cafenube.internal"})
        response = connection.getresponse()
        response.read(1024)
        return {"response": True, "healthy": response.status == 200, "status": response.status}
    finally:
        connection.close()


def ssh_query():
    with socket.create_connection(("10.0.0.148", 22), timeout=4) as sock:
        banner = sock.recv(256)
        return {"response": True, "healthy": banner.startswith(b"SSH-"), "banner": banner.decode("ascii", "replace").strip()}


def probe(function):
    try:
        return function()
    except PermissionError as error:
        return {"response": False, "healthy": False, "classification": "HOST_POLICY_DENY", "detail": str(error)}
    except (socket.timeout, TimeoutError) as error:
        return {"response": False, "healthy": False, "classification": "TIMEOUT_INCONCLUSIVE", "detail": str(error)}
    except (OSError, ConnectionError, http.client.HTTPException, struct.error) as error:
        return {"response": False, "healthy": False, "classification": "SERVICE_OR_NETWORK_ERROR", "detail": str(error)}


def main():
    # ROLE se antepone desde el runner; no se interpreta como shell ni se ejecuta contenido externo.
    results = {"dns_udp": probe(lambda: dns_query("UDP")),
               "dns_tcp": probe(lambda: dns_query("TCP")), "intranet_http": probe(http_query)}
    if globals().get("ROLE") == "TI":
        results["admin_ssh"] = probe(ssh_query)
    print("I4_PROBE_JSON=" + json.dumps(results, ensure_ascii=True))


if __name__ == "__main__":
    main()
