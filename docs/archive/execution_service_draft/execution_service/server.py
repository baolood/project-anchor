import os

from flask import Flask, request, jsonify

from shared.schemas import ExecutionTicket, ExecMode, Status
from execution_service.verifier import verify_ticket
from execution_service.executor import execute_simulate, execute_testnet
from local_box.audit.event_store import save_execution_receipt, get_execution_receipt

app = Flask(__name__)

HOST = os.getenv("EXECUTION_SERVICE_HOST", "127.0.0.1")
PORT = int(os.getenv("EXECUTION_SERVICE_PORT", "9001"))
EXECUTION_SHARED_KEYS = os.getenv("EXECUTION_SHARED_KEYS", "")


def _parse_shared_keys(raw: str) -> dict[str, str]:
    if not raw.strip():
        raise RuntimeError("EXECUTION_SHARED_KEYS is required")

    parsed: dict[str, str] = {}
    for item in raw.split(","):
        pair = item.strip()
        if not pair:
            raise RuntimeError("EXECUTION_SHARED_KEYS contains an empty entry")
        if ":" not in pair:
            raise RuntimeError("EXECUTION_SHARED_KEYS entry must be key_id:key")

        key_id, key = pair.split(":", 1)
        key_id = key_id.strip()
        key = key.strip()

        if not key_id or not key:
            raise RuntimeError("EXECUTION_SHARED_KEYS entry must contain non-empty key_id and key")
        if key_id in parsed:
            raise RuntimeError("EXECUTION_SHARED_KEYS contains duplicate key_id")

        parsed[key_id] = key

    return parsed


SHARED_KEYS = _parse_shared_keys(EXECUTION_SHARED_KEYS)


def _validate_boundary_config() -> None:
    if not SHARED_KEYS:
        raise RuntimeError("EXECUTION_SHARED_KEYS is required")


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "ok": True,
            "service": "execution_service",
            "boundary": {
                "host": HOST,
                "shared_key_required": True,
                "shared_key_ids": sorted(SHARED_KEYS),
            },
        }
    )


@app.route("/execute", methods=["POST"])
def execute():
    request_key_id = str(request.headers.get("X-EXECUTION-KEY-ID") or "").strip()
    request_key = str(request.headers.get("X-EXECUTION-KEY") or "").strip()
    expected_key = SHARED_KEYS.get(request_key_id)
    if expected_key is None or request_key != expected_key:
        return jsonify({"error": "forbidden"}), 403

    data = request.json

    try:
        ticket = ExecutionTicket(**data)
    except Exception as e:
        return jsonify({"error": f"invalid ticket: {str(e)}"}), 400

    # 🔒 核心安全边界：必须验签
    if not verify_ticket(ticket):
        return jsonify({"error": "invalid signature"}), 403

    # 🔒 禁止 live
    if ticket.mode == ExecMode.LIVE:
        return jsonify({"error": "LIVE mode disabled"}), 403

    # 执行
    if ticket.mode == ExecMode.SIMULATE:
        result = execute_simulate(ticket)
    elif ticket.mode == ExecMode.TESTNET:
        result = execute_testnet(ticket)
    else:
        return jsonify({"error": "unsupported mode"}), 400

    save_execution_receipt(
        ticket_id=ticket.ticket_id,
        command_id=ticket.command_id,
        status=result.status.value if hasattr(result.status, "value") else str(result.status),
        payload=result.__dict__,
    )
    return jsonify(result.__dict__)


@app.route("/receipt/<ticket_id>", methods=["GET"])
def receipt(ticket_id: str):
    row = get_execution_receipt(ticket_id)
    if row is None:
        return jsonify({"error": "receipt not found"}), 404
    return jsonify(row)


if __name__ == "__main__":
    _validate_boundary_config()
    app.run(host=HOST, port=PORT)
