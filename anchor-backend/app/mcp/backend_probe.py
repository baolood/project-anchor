"""Optional loopback HTTP probe of the Docker backend. No Docker socket."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping

from app.mcp.inventory import host_sidecar_enabled


PROBE_ENV = "ANCHOR_CONTROL_MCP_BACKEND_PROBE"
HEALTH_URL = "http://127.0.0.1:8000/health"
OPS_URL = "http://127.0.0.1:8000/ops/state"
ALLOWED_URLS = frozenset({HEALTH_URL, OPS_URL})
_PROBE_TIMEOUT_SEC = 1.0
_MAX_BODY = 65536


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise urllib.error.HTTPError(req.full_url, code, "redirect_rejected", headers, fp)


def probe_enabled(env: Mapping[str, str]) -> bool:
    if not host_sidecar_enabled(env):
        return False
    raw = (env.get(PROBE_ENV) or "1").strip().lower()
    return raw not in {"0", "off", "false", "no"}


def _fetch_allowlisted(url: str, timeout: float = _PROBE_TIMEOUT_SEC) -> dict[str, Any]:
    """GET one hardcoded loopback URL. Any other URL is rejected before the network."""
    if url not in ALLOWED_URLS:
        return {"ok": False, "status": None, "reason": "url_rejected", "json": None}
    opener = urllib.request.build_opener(_RefuseRedirect)
    request = urllib.request.Request(url, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            raw = response.read(_MAX_BODY)
    except urllib.error.HTTPError as exc:
        status = getattr(exc, "code", None)
        return {"ok": False, "status": status if isinstance(status, int) else None, "reason": "http_error", "json": None}
    except Exception:
        return {"ok": False, "status": None, "reason": "unreachable", "json": None}
    if status != 200:
        return {"ok": False, "status": status if isinstance(status, int) else None, "reason": "http_status", "json": None}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return {"ok": False, "status": status, "reason": "not_json", "json": None}
    if not isinstance(payload, dict):
        return {"ok": False, "status": status, "reason": "not_object", "json": None}
    return {"ok": True, "status": status, "reason": "ok", "json": payload}


def _health_ok(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("ok") is True:
        return True
    return payload.get("status") == "ok"


def _has_key(fetch_result: Mapping[str, Any], key: str) -> bool:
    payload = fetch_result.get("json")
    return isinstance(payload, dict) and key in payload


def probe_backend(
    env: Mapping[str, str],
    fetch: Callable[[str], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Probe the Docker backend over loopback HTTP.

    /health gates the host health check. /ops/state is projected to booleans
    only and does not gate PASS. The response body is not returned.
    """
    if not host_sidecar_enabled(env):
        return {"enabled": False, "ok": None, "reason": "not_host_sidecar", "upstream": "127.0.0.1:8000"}
    if not probe_enabled(env):
        return {"enabled": False, "ok": None, "reason": "probe_disabled", "upstream": "127.0.0.1:8000"}
    fetch_one = fetch or _fetch_allowlisted
    health = fetch_one(HEALTH_URL)
    ops = fetch_one(OPS_URL)
    health_ok = health.get("ok") is True and _health_ok(health.get("json"))
    reason = "health_ok" if health_ok else str(health.get("reason") or "health_not_ok")
    status = health.get("status")
    return {
        "enabled": True,
        "ok": health_ok,
        "reason": reason,
        "health_status": status if isinstance(status, int) else None,
        "ops_reachable": ops.get("ok") is True,
        "ops_has_kill_switch": _has_key(ops, "kill_switch"),
        "ops_has_worker_heartbeat": _has_key(ops, "worker_heartbeat"),
        "ops_has_worker_panic": _has_key(ops, "worker_panic"),
        "transport": "http",
        "upstream": "127.0.0.1:8000",
    }
