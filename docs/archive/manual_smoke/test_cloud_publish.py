import requests


CLOUD_URL = "http://127.0.0.1:9003/publish"


def test_allowed():
    body = {
        "strategy_id": "cloud_demo",
        "version": "v1",
        "payload": {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "qty": 0.01,
            "price": 100.0,
            "stop_loss": 95.0,
            "leverage": 1,
            "mode": "simulate",
        },
    }
    r = requests.post(CLOUD_URL, json=body, timeout=10)
    print("ALLOWED:", r.status_code, r.json())


def test_blocked_version():
    body = {
        "strategy_id": "cloud_demo",
        "version": "v999",
        "payload": {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "qty": 0.01,
            "price": 100.0,
            "stop_loss": 95.0,
            "leverage": 1,
            "mode": "simulate",
        },
    }
    r = requests.post(CLOUD_URL, json=body, timeout=10)
    print("BLOCKED_VERSION:", r.status_code, r.json())


if __name__ == "__main__":
    test_allowed()
    test_blocked_version()
