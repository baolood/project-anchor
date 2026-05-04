from flask import Flask, jsonify, request
import requests

from shared.schemas import StrategyIntent
from cloud.strategy_store.versions import is_allowed_version


LOCAL_BOX_URL = "http://127.0.0.1:9002/run-intent"

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "cloud_strategy_api"})


@app.route("/publish", methods=["POST"])
def publish():
    body = request.json or {}
    try:
        intent = StrategyIntent(**body)
    except Exception as e:
        return jsonify({"error": f"invalid intent: {str(e)}"}), 400

    if not is_allowed_version(intent.version):
        return jsonify({"error": "strategy version not allowed"}), 403

    resp = requests.post(LOCAL_BOX_URL, json=intent.__dict__, timeout=10)
    try:
        payload = resp.json()
    except Exception:
        payload = {"error": resp.text}
    return jsonify(payload), resp.status_code


if __name__ == "__main__":
    app.run(port=9003)
