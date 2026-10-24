"""Host webhook hook for MF4 signals. DEPLOY=NO. Default off.

Posts only when ``MF4_WEBHOOK_ENABLED=1`` (or when the operator passes
``--send-test``). The key is read from systemd ``LoadCredential``
(``$CREDENTIALS_DIRECTORY/webhook``) or from ``MF4_WEBHOOK_ENV_FILE``.
The URL and the key are never written to logs, status, or the outbox.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo


STRATEGY = "MF4_BRK4H_4R"
SOURCE = "anchor-host"
RETRY_DELAYS_S = (2, 5, 15)
TIMEOUT_S = 15
STATE_NAME = "webhook_state.json"
OUTBOX_NAME = "webhook_outbox.jsonl"
_SHANGHAI = ZoneInfo("Asia/Shanghai")
_LOG = logging.getLogger("ops.mf4.webhook")

Poster = Callable[..., Any]
Sleeper = Callable[[float], None]


@dataclass(frozen=True)
class WebhookConfig:
    url: str
    key: str
    header_name: str
    key_format: str

    @property
    def secrets(self) -> tuple[str, ...]:
        header_value = _header_value(self)
        values = [self.url, self.key]
        if header_value and header_value not in values:
            values.append(header_value)
        return tuple(item for item in values if item)


def webhook_enabled(env: Mapping[str, str] | None = None) -> bool:
    selected = os.environ if env is None else env
    return str(selected.get("MF4_WEBHOOK_ENABLED", "0")).strip() == "1"


def load_config(env: Mapping[str, str] | None = None) -> WebhookConfig | None:
    """Load URL and key. Returns None when the credential file is absent."""
    selected = dict(os.environ if env is None else env)
    path = _credential_path(selected)
    if path is None or not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    parsed = _parse_env(text)
    url = (parsed.get("EVAL_WEBHOOK_URL") or "").strip()
    key = (parsed.get("EVAL_WEBHOOK_KEY") or "").strip()
    if not url or not key:
        return None
    header = (parsed.get("EVAL_WEBHOOK_KEY_HEADER") or "Authorization").strip() or "Authorization"
    key_format = parsed.get("EVAL_WEBHOOK_KEY_FORMAT") or "Bearer {key}"
    return WebhookConfig(url=url, key=key, header_name=header, key_format=key_format)


def build_payload(
    *,
    signal: str,
    price: float | int | str,
    when: datetime,
    reason: str,
    event_id: str,
    guard: Mapping[str, Any] | None,
    test: bool = False,
) -> dict[str, Any]:
    return {
        "signal": signal,
        "strategy": STRATEGY,
        "price": price,
        "time_shanghai": shanghai_stamp(when),
        "reason": reason,
        "test": bool(test),
        "source": SOURCE,
        "event_id": event_id,
        "guard": dict(guard) if isinstance(guard, Mapping) else None,
    }


def event_id_for(signal: str, side: str, candle_time: str) -> str:
    import hashlib

    raw = f"{signal}|{side}|{candle_time}".encode("utf-8")
    return "mf4-" + hashlib.sha256(raw).hexdigest()[:20]


def shanghai_stamp(when: datetime) -> str:
    if when.tzinfo is None:
        when = when.replace(tzinfo=ZoneInfo("UTC"))
    return when.astimezone(_SHANGHAI).isoformat(timespec="seconds")


def redact(text: str, secrets: tuple[str, ...] = ()) -> str:
    redacted = text
    for secret in secrets:
        if secret and secret in redacted:
            redacted = redacted.replace(secret, "[REDACTED]")
    lowered = redacted.lower()
    if "bearer " in lowered or "http://" in lowered or "https://" in lowered:
        redacted = _scrub_urls_and_bearers(redacted)
    return redacted


def deliver(
    payload: Mapping[str, Any],
    config: WebhookConfig,
    *,
    poster: Poster | None = None,
    sleeper: Sleeper | None = None,
) -> tuple[bool, str]:
    """POST with 3 retries (2s, 5s, 15s). Never raises. Never logs the key."""
    send = poster or urllib_poster
    pause = sleeper or _sleep
    body = json.dumps(dict(payload), separators=(",", ":"), sort_keys=True).encode("utf-8")
    headers = _headers(config)
    last = "delivery_failed"
    attempts = len(RETRY_DELAYS_S) + 1
    for attempt in range(attempts):
        try:
            status = send(config.url, headers, body, timeout=TIMEOUT_S)
            code = int(status)
            if 200 <= code < 300:
                return True, "ok"
            last = f"http_{code}"
        except Exception as exc:
            last = redact(f"network_error:{type(exc).__name__}", config.secrets)
            _log_safe("webhook delivery failed", config.secrets)
            if _secret_in_text(str(exc), config.secrets):
                last = "network_error"
        if attempt < len(RETRY_DELAYS_S):
            try:
                pause(RETRY_DELAYS_S[attempt])
            except Exception:
                return False, last
    return False, last


def dispatch(
    out_dir: Path,
    payload: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
    poster: Poster | None = None,
    sleeper: Sleeper | None = None,
    asynchronous: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Send one payload unless its event_id was already accepted.

    ``force`` is only for the explicit ``--send-test`` command. The watcher
    loop leaves it false, so ``MF4_WEBHOOK_ENABLED=0`` sends nothing.
    Network work runs on a daemon thread when ``asynchronous`` is set.
    """
    if not force and not webhook_enabled(env):
        return {"sent": False, "skipped": "disabled"}
    event_id = str(payload.get("event_id") or "")
    if not event_id:
        return {"sent": False, "skipped": "missing_event_id"}
    config = load_config(env)
    if config is None:
        return {"sent": False, "skipped": "credentials_missing"}
    if not _claim(out_dir, event_id):
        return {"sent": False, "skipped": "duplicate"}

    def _run() -> dict[str, Any]:
        try:
            ok, detail = deliver(payload, config, poster=poster, sleeper=sleeper)
            if ok:
                _mark_sent(out_dir, event_id, shanghai_stamp(_now()))
                _drop_outbox(out_dir, event_id)
                return {"sent": True, "event_id": event_id}
            _remember_failure(out_dir, payload, detail)
            return {"sent": False, "queued": True, "event_id": event_id}
        except Exception:
            _log_safe("webhook hook failed", config.secrets)
            return {"sent": False, "queued": False, "event_id": event_id}

    if asynchronous:
        thread = threading.Thread(target=_run, name="mf4-webhook", daemon=True)
        thread.start()
        return {"sent": False, "scheduled": True, "event_id": event_id, "thread": thread}
    return _run()


def flush_outbox(
    out_dir: Path,
    *,
    env: Mapping[str, str] | None = None,
    poster: Poster | None = None,
    sleeper: Sleeper | None = None,
) -> int:
    """Retry queued payloads. Returns how many were delivered. Never raises."""
    if not webhook_enabled(env):
        return 0
    config = load_config(env)
    if config is None:
        return 0
    path = out_dir / OUTBOX_NAME
    rows = _read_outbox(path)
    if not rows:
        return 0
    kept: list[dict[str, Any]] = []
    delivered = 0
    for row in rows:
        payload = row.get("payload")
        event_id = str(row.get("event_id") or "")
        if not isinstance(payload, dict) or not event_id:
            continue
        if event_id in _load_state(out_dir).get("sent", []):
            continue
        ok, detail = deliver(payload, config, poster=poster, sleeper=sleeper)
        if ok:
            _mark_sent(out_dir, event_id, shanghai_stamp(_now()))
            delivered += 1
        else:
            row["attempts"] = int(row.get("attempts") or 1) + 1
            row["last_error"] = detail
            kept.append(row)
    _write_outbox(path, kept)
    return delivered


def send_test(
    out_dir: Path,
    *,
    env: Mapping[str, str] | None = None,
    poster: Poster | None = None,
    sleeper: Sleeper | None = None,
    when: datetime | None = None,
) -> int:
    """Post one ``test: true`` payload. Does not turn the standing flag on."""
    moment = when or _now()
    payload = build_payload(
        signal="TEST",
        price=0,
        when=moment,
        reason="operator_send_test",
        event_id=event_id_for("TEST", "none", shanghai_stamp(moment)),
        guard=None,
        test=True,
    )
    result = dispatch(
        out_dir,
        payload,
        env=env,
        poster=poster,
        sleeper=sleeper,
        asynchronous=False,
        force=True,
    )
    _log_safe("send-test finished", ())
    return 0 if result.get("sent") else 1


def urllib_poster(url: str, headers: Mapping[str, str], body: bytes, timeout: float = TIMEOUT_S) -> int:
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1024)
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def outbox_count(out_dir: Path) -> int:
    return len(_read_outbox(out_dir / OUTBOX_NAME))


def last_ok_at(out_dir: Path) -> str | None:
    value = _load_state(out_dir).get("last_ok_at_sh")
    return value if isinstance(value, str) and value else None


def _credential_path(env: Mapping[str, str]) -> Path | None:
    explicit = (env.get("MF4_WEBHOOK_ENV_FILE") or "").strip()
    if explicit:
        return Path(explicit)
    directory = (env.get("CREDENTIALS_DIRECTORY") or "").strip()
    if directory:
        return Path(directory) / "webhook"
    return None


def _parse_env(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        parsed[key] = value.strip().strip('"').strip("'")
    return parsed


def _header_value(config: WebhookConfig) -> str:
    try:
        return config.key_format.format(key=config.key)
    except (KeyError, IndexError, ValueError):
        return f"Bearer {config.key}"


def _headers(config: WebhookConfig) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "User-Agent": "anchor-mf4-watcher/1.0",
        config.header_name: _header_value(config),
    }


def _claim(out_dir: Path, event_id: str) -> bool:
    with _lock(out_dir):
        state = _load_state(out_dir)
        sent = list(state.get("sent") or [])
        queued = list(state.get("queued") or [])
        if event_id in sent or event_id in queued:
            return False
        queued.append(event_id)
        state["sent"] = sent[-500:]
        state["queued"] = queued[-500:]
        _save_state(out_dir, state)
        return True


def _mark_sent(out_dir: Path, event_id: str, stamp: str) -> None:
    with _lock(out_dir):
        state = _load_state(out_dir)
        sent = [item for item in list(state.get("sent") or []) if item != event_id]
        sent.append(event_id)
        queued = [item for item in list(state.get("queued") or []) if item != event_id]
        state["sent"] = sent[-500:]
        state["queued"] = queued[-500:]
        state["last_ok_at_sh"] = stamp
        _save_state(out_dir, state)


def _remember_failure(out_dir: Path, payload: Mapping[str, Any], detail: str) -> None:
    event_id = str(payload.get("event_id") or "")
    path = out_dir / OUTBOX_NAME
    rows = [row for row in _read_outbox(path) if row.get("event_id") != event_id]
    rows.append(
        {
            "event_id": event_id,
            "payload": dict(payload),
            "attempts": 1,
            "last_error": detail,
        }
    )
    _write_outbox(path, rows)


def _drop_outbox(out_dir: Path, event_id: str) -> None:
    path = out_dir / OUTBOX_NAME
    kept = [row for row in _read_outbox(path) if row.get("event_id") != event_id]
    _write_outbox(path, kept)


def _read_outbox(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        blob = path.read_bytes()
    except OSError:
        return []
    if len(blob) > 64 * 1024:
        blob = blob[-64 * 1024 :]
        blob = blob.split(b"\n", 1)[-1]
    rows: list[dict[str, Any]] = []
    for line in blob.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _write_outbox(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n" for row in rows)
    _atomic_text(path, text)


def _load_state(out_dir: Path) -> dict[str, Any]:
    path = out_dir / STATE_NAME
    if not path.is_file():
        return {"sent": [], "queued": [], "last_ok_at_sh": None}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"sent": [], "queued": [], "last_ok_at_sh": None}
    if not isinstance(payload, dict):
        return {"sent": [], "queued": [], "last_ok_at_sh": None}
    payload.setdefault("sent", [])
    payload.setdefault("queued", [])
    return payload


def _save_state(out_dir: Path, state: Mapping[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _atomic_text(out_dir / STATE_NAME, json.dumps(dict(state), separators=(",", ":"), sort_keys=True))


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    try:
        os.chmod(temporary, 0o640)
    except OSError:
        pass
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o640)
    except OSError:
        pass


def _lock(out_dir: Path) -> threading.Lock:
    out_dir.mkdir(parents=True, exist_ok=True)
    key = str(out_dir.resolve())
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock


def _log_safe(message: str, secrets: tuple[str, ...]) -> None:
    _LOG.info("%s", redact(message, secrets))


def _secret_in_text(text: str, secrets: tuple[str, ...]) -> bool:
    return any(secret and secret in text for secret in secrets)


def _scrub_urls_and_bearers(text: str) -> str:
    import re

    scrubbed = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", text)
    scrubbed = re.sub(r"(?i)\bhttps?://\S+", "[REDACTED_URL]", scrubbed)
    return scrubbed


def _sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)


def _now() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)


_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()
