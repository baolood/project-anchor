"""
Telegram notify with throttling. Never raises; failures are logged.
TELEGRAM_NOTIFY_ENABLED=1 to enable; otherwise no-op.
"""
import os
import time
from typing import Dict

_telegram_throttle: Dict[str, float] = {}
TELEGRAM_THROTTLE_SECONDS = float(os.getenv("TELEGRAM_THROTTLE_SECONDS", "60"))


def send_telegram(text: str, throttle_key: str = "default") -> None:
    """Send text to Telegram. Throttled by throttle_key. Never raises."""
    if (os.getenv("TELEGRAM_NOTIFY_ENABLED") or "").strip() != "1":
        return
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        return
    now = time.time()
    last = _telegram_throttle.get(throttle_key, 0.0)
    if now - last < TELEGRAM_THROTTLE_SECONDS:
        return
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
        if r.status_code == 200:
            _telegram_throttle[throttle_key] = now
        else:
            print(f"[telegram] send failed status={r.status_code} body={r.text[:200]}", flush=True)
    except Exception as e:
        print(f"[telegram] send error: {e}", flush=True)
