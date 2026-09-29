"""Stateless Streamable HTTP MCP endpoint for ANCHOR_CONTROL_MCP_V1."""

from __future__ import annotations

import hmac
import json
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

from app.mcp import SERVER_NAME, SERVER_VERSION, TOKEN_ENV
from app.mcp.sanitize import redact_obj
from app.mcp.tools import TOOL_NAMES, ToolContext, call_tool, default_context, tool_definitions


SUPPORTED_PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18"}
DEFAULT_PROTOCOL_VERSION = "2025-03-26"
MAX_BODY_BYTES = 65536
ALLOWED_ORIGINS_ENV = "ANCHOR_CONTROL_MCP_ALLOWED_ORIGINS"
_QUERY_SECRET_RE_KEYS = ("token", "access_token", "api_key", "authorization", "password", "secret")


@dataclass
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes | None


def _secure_equals(presented: str, expected: str) -> bool:
    presented_b = presented.encode("utf-8")
    expected_b = expected.encode("utf-8")
    if len(presented_b) != len(expected_b):
        hmac.compare_digest(expected_b, expected_b)
        return False
    return hmac.compare_digest(presented_b, expected_b)


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def _query_has_secret(query_string: str) -> bool:
    if not query_string:
        return False
    for part in query_string.split("&"):
        key = part.split("=", 1)[0].strip().lower()
        if key in _QUERY_SECRET_RE_KEYS:
            return True
    return False


def _origin_allowed(origin: str, host_header: str | None, env: Mapping[str, str]) -> bool:
    allow = [item.strip() for item in env.get(ALLOWED_ORIGINS_ENV, "").split(",") if item.strip()]
    if allow:
        return origin in allow
    parsed = urlsplit(origin)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        return False
    host = (host_header or "").split(",")[0].strip().lower()
    host_name = host.split(":")[0]
    if host_name.startswith("[") and "]" in host_name:
        host_name = host_name[1:host_name.index("]")]
    return bool(host_name) and parsed.hostname.lower() == host_name


def _base_headers(content_type: str | None = "application/json") -> dict[str, str]:
    headers = {"cache-control": "no-store", "x-content-type-options": "nosniff"}
    if content_type:
        headers["content-type"] = content_type
    return headers


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _wants_sse_only(accept: str) -> bool:
    lowered = accept.lower()
    if "text/event-stream" not in lowered:
        return False
    return "application/json" not in lowered and "*/*" not in lowered


def _encode(payload: dict[str, Any], accept: str) -> tuple[str, bytes]:
    encoded = _json_bytes(payload)
    if _wants_sse_only(accept):
        body = b"event: message\ndata: " + encoded + b"\n\n"
        return "text/event-stream", body
    return "application/json", encoded


def _initialize_result(params: dict[str, Any]) -> dict[str, Any]:
    requested = params.get("protocolVersion")
    version = requested if isinstance(requested, str) and requested in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
    return {
        "protocolVersion": version,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        "instructions": (
            "ANCHOR_CONTROL_MCP_V1 is read-only. "
            "Exactly seven tools are available: "
            + ", ".join(TOOL_NAMES)
            + ". No secrets, trading, orders, withdrawals, database writes, "
            "service control, SSH, or arbitrary shell."
        ),
    }


def _tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": False,
    }


def handle_message(message: Any, ctx: ToolContext) -> dict[str, Any] | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        request_id = message.get("id") if isinstance(message, dict) else None
        return _rpc_error(request_id, -32600, "Invalid Request")
    method = message["method"]
    request_id = message.get("id", None)
    is_notification = "id" not in message
    params = message.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        if is_notification:
            return None
        return _rpc_error(request_id, -32602, "Invalid params")
    if is_notification:
        return None
    if method == "initialize":
        return _rpc_result(request_id, _initialize_result(params))
    if method == "ping":
        return _rpc_result(request_id, {})
    if method == "tools/list":
        return _rpc_result(request_id, {"tools": tool_definitions()})
    if method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or name not in TOOL_NAMES:
            return _rpc_error(request_id, -32602, "Unknown tool")
        try:
            payload = call_tool(name, params.get("arguments"), ctx)
        except ValueError as exc:
            return _rpc_error(request_id, -32602, str(exc))
        except KeyError:
            return _rpc_error(request_id, -32602, "Unknown tool")
        except Exception:
            return _rpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": "read_failed"}],
                    "isError": True,
                },
            )
        return _rpc_result(request_id, _tool_result(payload))
    return _rpc_error(request_id, -32601, "Method not found")


def dispatch_http(
    method: str,
    headers: Mapping[str, str],
    body: bytes,
    query_string: str = "",
    env: Mapping[str, str] | None = None,
    context: ToolContext | None = None,
) -> HttpResult:
    selected_env = env if env is not None else os.environ
    normalized = {str(key).lower(): value for key, value in headers.items()}
    if _query_has_secret(query_string):
        payload = {"error": "query_credentials_rejected"}
        return HttpResult(400, _base_headers(), _json_bytes(payload))
    origin = normalized.get("origin")
    if origin and not _origin_allowed(origin, normalized.get("host"), selected_env):
        return HttpResult(403, _base_headers(), _json_bytes({"error": "origin_rejected"}))
    expected = (selected_env.get(TOKEN_ENV) or "").strip()
    if not expected:
        return HttpResult(
            503,
            _base_headers(),
            _json_bytes({"error": "anchor_control_mcp_disabled", "detail": f"{TOKEN_ENV} is not set"}),
        )
    presented = _bearer(normalized.get("authorization"))
    if presented is None or not _secure_equals(presented, expected):
        headers_out = _base_headers()
        headers_out["www-authenticate"] = 'Bearer realm="anchor-control-mcp"'
        return HttpResult(401, headers_out, _json_bytes({"error": "unauthorized"}))
    upper = method.upper()
    if upper == "GET":
        headers_out = _base_headers()
        headers_out["allow"] = "POST, DELETE"
        return HttpResult(405, headers_out, _json_bytes({"error": "use_post_jsonrpc"}))
    if upper == "DELETE":
        return HttpResult(204, {"cache-control": "no-store"}, None)
    if upper != "POST":
        headers_out = _base_headers()
        headers_out["allow"] = "POST, DELETE"
        return HttpResult(405, headers_out, _json_bytes({"error": "method_not_allowed"}))
    content_length = normalized.get("content-length", "")
    if content_length.isdigit() and int(content_length) > MAX_BODY_BYTES:
        return HttpResult(413, _base_headers(), _json_bytes({"error": "body_too_large"}))
    if len(body) > MAX_BODY_BYTES:
        return HttpResult(413, _base_headers(), _json_bytes({"error": "body_too_large"}))
    ctx = context or default_context(selected_env)
    ctx.extra_secrets = tuple(dict.fromkeys([expected, *ctx.extra_secrets]))
    accept = normalized.get("accept", "")
    if not body.strip():
        content_type, encoded = _encode(_rpc_error(None, -32700, "Parse error"), accept)
        return HttpResult(200, _base_headers(content_type), encoded)
    try:
        message = json.loads(body)
    except json.JSONDecodeError:
        content_type, encoded = _encode(_rpc_error(None, -32700, "Parse error"), accept)
        return HttpResult(200, _base_headers(content_type), encoded)
    if isinstance(message, list):
        content_type, encoded = _encode(_rpc_error(None, -32600, "Batch requests are not supported"), accept)
        return HttpResult(200, _base_headers(content_type), encoded)
    response = handle_message(message, ctx)
    if response is None:
        return HttpResult(202, {"cache-control": "no-store"}, None)
    safe = redact_obj(response, ctx.extra_secrets)
    if not isinstance(safe, dict):
        safe = _rpc_error(message.get("id") if isinstance(message, dict) else None, -32603, "Internal error")
    content_type, encoded = _encode(safe, accept)
    return HttpResult(200, _base_headers(content_type), encoded)
