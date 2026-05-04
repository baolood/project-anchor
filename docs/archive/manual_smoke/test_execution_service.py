import requests
import time

from shared.schemas import ExecutionTicket, ExecMode, new_ticket_id
from execution_service.verifier import sign_ticket

URL = "http://localhost:9001/execute"


def build_ticket():
    ticket = ExecutionTicket(
        ticket_id=new_ticket_id(),
        command_id="cmd_test_001",
        symbol="BTCUSDT",
        side="BUY",
        qty=0.01,
        price=100.0,
        mode=ExecMode.SIMULATE,
        issued_at=time.time(),
        signature=""
    )

    ticket.signature = sign_ticket(ticket)
    return ticket


def test_success():
    ticket = build_ticket()

    r = requests.post(URL, json=ticket.__dict__)
    print("SUCCESS:", r.json())


def test_invalid_signature():
    ticket = build_ticket()
    ticket.signature = "fake_signature"

    r = requests.post(URL, json=ticket.__dict__)
    print("INVALID SIGN:", r.json())


def test_live_blocked():
    ticket = build_ticket()
    ticket.mode = ExecMode.LIVE
    ticket.signature = sign_ticket(ticket)

    r = requests.post(URL, json=ticket.__dict__)
    print("LIVE BLOCK:", r.json())


def test_testnet_mock():
    ticket = build_ticket()
    ticket.mode = ExecMode.TESTNET
    ticket.signature = sign_ticket(ticket)

    r = requests.post(URL, json=ticket.__dict__)
    print("TESTNET:", r.json())


if __name__ == "__main__":
    print("\n=== TEST 1: SUCCESS ===")
    test_success()

    print("\n=== TEST 2: INVALID SIGNATURE ===")
    test_invalid_signature()

    print("\n=== TEST 3: LIVE BLOCKED ===")
    test_live_blocked()

    print("\n=== TEST 4: TESTNET MOCK ===")
    test_testnet_mock()
