"""Host-side ANCHOR_CONTROL_MCP listener. Loopback port 8001 only, never root.

This process is separate from the Docker backend on 127.0.0.1:8000. It mounts
only the read-only MCP router.
"""

from __future__ import annotations

import os
import socket
import sys
from typing import Mapping


BIND_HOST = "127.0.0.1"
BIND_PORT = 8001
BIND_VALUE = "127.0.0.1:8001"
BIND_ENV = "ANCHOR_CONTROL_MCP_BIND"
SERVICE_USER = "anchor-mcp"
PROJECT_ROOT = "/path/to/project-anchor"

FORBIDDEN_UNIT_SNIPPETS = (
    "docker.sock",
    "/var/run/docker",
    "ssh",
    "systemctl start",
    "systemctl stop",
    "systemctl restart",
    "systemctl reload",
    "User=root",
    "Group=root",
    "DATABASE_URL",
    "AmbientCapabilities",
    "CAP_SYS_ADMIN",
    "0.0.0.0",
    ":8000",
)


class BindRejected(Exception):
    """The process was asked to listen somewhere other than 127.0.0.1:8001."""


def require_loopback_bind(env: Mapping[str, str]) -> tuple[str, int]:
    """Accept only the unset default or the exact loopback sidecar address."""
    raw = env.get(BIND_ENV)
    if raw is None or raw.strip() == "" or raw.strip() == BIND_VALUE:
        return BIND_HOST, BIND_PORT
    raise BindRejected(f"refusing bind {raw.strip()!r}; only {BIND_VALUE} is allowed")


def root_rejected(euid: int) -> bool:
    return euid == 0


def render_service_unit() -> str:
    """Example systemd unit. Review only; this function does not install it."""
    backend = f"{PROJECT_ROOT}/anchor-backend"
    return f"""[Unit]
Description=Project Anchor read-only control MCP host sidecar
Documentation=file:{backend}/docs/ANCHOR_CONTROL_MCP_HOST_SIDECAR_V1.md
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={SERVICE_USER}
Group={SERVICE_USER}
SupplementaryGroups=systemd-journal
WorkingDirectory={backend}
Environment=PYTHONPATH={backend}
Environment=ANCHOR_CONTROL_MCP_HOST_SIDECAR=1
Environment=ANCHOR_CONTROL_MCP_BIND={BIND_VALUE}
Environment=ANCHOR_CONTROL_MCP_SERVICE_UNITS=docker.service
Environment=ANCHOR_CONTROL_MCP_TIMER_UNITS=
Environment=ANCHOR_CONTROL_MCP_REPORTS_DIR={PROJECT_ROOT}/reports
Environment=ANCHOR_CONTROL_MCP_BACKEND_PROBE=1
EnvironmentFile=-/etc/project-anchor/anchor-control-mcp.env
ExecStart=/usr/bin/python3 -m app.mcp.host_sidecar
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
UMask=0077
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
IPAddressDeny=any
IPAddressAllow=localhost
LockPersonality=true
RestrictSUIDSGID=true

[Install]
WantedBy=multi-user.target
"""


def unit_problems(text: str) -> list[str]:
    problems: list[str] = []
    for snippet in FORBIDDEN_UNIT_SNIPPETS:
        if snippet in text:
            problems.append(f"forbidden snippet: {snippet}")
    required = (
        f"User={SERVICE_USER}",
        f"Group={SERVICE_USER}",
        "SupplementaryGroups=systemd-journal",
        f"Environment=ANCHOR_CONTROL_MCP_BIND={BIND_VALUE}",
        "Environment=ANCHOR_CONTROL_MCP_HOST_SIDECAR=1",
        "Environment=ANCHOR_CONTROL_MCP_SERVICE_UNITS=docker.service",
        "Environment=ANCHOR_CONTROL_MCP_BACKEND_PROBE=1",
        "ExecStart=/usr/bin/python3 -m app.mcp.host_sidecar",
        "EnvironmentFile=-/etc/project-anchor/anchor-control-mcp.env",
        "IPAddressAllow=localhost",
        "NoNewPrivileges=true",
    )
    for snippet in required:
        if snippet not in text:
            problems.append(f"missing snippet: {snippet}")
    return problems


def open_loopback_listener(env: Mapping[str, str] | None = None) -> socket.socket:
    """Bind the only legal sidecar address. Caller closes the socket."""
    host, port = require_loopback_bind(os.environ if env is None else env)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(1)
    except Exception:
        sock.close()
        raise
    return sock


def create_app():
    """ASGI app that exposes POST /mcp and no trading routes."""
    from fastapi import FastAPI

    from app.mcp.router import router

    app = FastAPI(
        title="anchor-control-mcp-host",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(router)
    return app


def main() -> int:
    try:
        host, port = require_loopback_bind(os.environ)
    except BindRejected as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if root_rejected(os.geteuid()):
        print("anchor-control-mcp host sidecar refuses to run as root", file=sys.stderr)
        return 2
    import uvicorn

    uvicorn.run(
        create_app(),
        host=host,
        port=port,
        access_log=False,
        log_level="info",
        proxy_headers=False,
        forwarded_allow_ips="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
