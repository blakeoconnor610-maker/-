"""Works out which addresses the control panel is reachable on."""

from __future__ import annotations

import os
import socket


def local_ips() -> list[str]:
    """Every ipv4 address this machine answers on, best guess first.

    Nothing is sent anywhere - the udp socket is only used to ask the routing
    table which interface would be used to reach the outside world.
    """
    found: list[str] = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 53))  # reserved test address, no traffic leaves
        found.append(sock.getsockname()[0])
    except OSError:
        pass
    finally:
        sock.close()

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if address not in found:
                found.append(address)
    except OSError:
        pass

    return [ip for ip in found if not ip.startswith("127.")]


def panel_state() -> dict:
    """What the panel is configured to do, straight from the environment."""
    enabled = os.getenv("PANEL_ENABLED", "false").lower() in ("1", "true", "yes")
    host = os.getenv("PANEL_HOST", "0.0.0.0")
    port = os.getenv("PANEL_PORT", "8080")
    password = (os.getenv("PANEL_PASSWORD") or "").strip()

    if not enabled:
        problem = "PANEL_ENABLED is not set to true in your .env"
    elif len(password) < 12:
        problem = "PANEL_PASSWORD is missing or shorter than 12 characters"
    else:
        problem = None

    if host in ("127.0.0.1", "localhost"):
        addresses = [f"http://127.0.0.1:{port}"]
        reach = "loopback only - nothing else on the network can reach it"
    else:
        addresses = [f"http://{ip}:{port}" for ip in local_ips()]
        reach = "anything that can reach this machine on that port"

    return {
        "enabled": enabled,
        "host": host,
        "port": port,
        "problem": problem,
        "addresses": addresses,
        "reach": reach,
    }
