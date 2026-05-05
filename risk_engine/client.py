"""Thin HTTP client for the archived execution_service draft (port 9001).

Not a risk model — see ``docs/RISK_ENGINE_PENDING_DECISION_RECORD_V1.md``.
"""

import os

import requests

from shared.schemas import ExecutionTicket


EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://127.0.0.1:9001")
EXECUTION_SHARED_KEY_ID = os.getenv("EXECUTION_SHARED_KEY_ID", "")
EXECUTION_SHARED_KEY = os.getenv("EXECUTION_SHARED_KEY", "")


def _headers() -> dict:
    return {
        "X-EXECUTION-KEY-ID": EXECUTION_SHARED_KEY_ID,
        "X-EXECUTION-KEY": EXECUTION_SHARED_KEY,
    }


def send_ticket(ticket: ExecutionTicket):
    return requests.post(f"{EXECUTION_SERVICE_URL}/execute", json=ticket.__dict__, headers=_headers())


def get_receipt(ticket_id: str):
    return requests.get(f"{EXECUTION_SERVICE_URL}/receipt/{ticket_id}", headers=_headers())
