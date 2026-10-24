"""MF4 webhook, eval guard, and host watcher. No network."""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import stat
import subprocess
import sys
import threading
import time
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ops.mf4 import _b1_core
from ops.mf4.eval_guard import evaluate
from ops.mf4.mf4_host_watcher import EX_ANTE_FIELDS, Watcher, main, write_json
from ops.mf4 import mf4_host_watcher as watcher_mod
from ops.mf4.mf4_record_actual import main as record_main
from ops.mf4.mf4_record_actual import write_account
from ops.mf4.mf4_webhook import (
    build_payload,
    deliver,
    dispatch,
    event_id_for,
    flush_outbox,
    send_test,
    webhook_enabled,
)
from ops.mf4.sealed import sealed_reason


ROOT = Path(__file__).resolve().parents[1]
KEY = "mf4-test-key-do-not-log"
URL = "https://hooks.example.test/mf4/secret-path"
NOW = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)
TRADE = {
    "balance": "10120.42",
    "daily_ref_balance": "10120.42",
    "daily_ref_at": "2026-10-22T00:30:00Z",
    "floor": 9400,
    "target": 11000,
    "position": {
        "side": "long",
        "size": "0.176",
        "entry": "84499.5",
        "sl": "83633.1",
        "tp": "87812.6",
    },
    "snapshot_at": "2026-10-22T09:00:00Z",
}


def _payload() -> dict:
    return build_payload(
        signal="OPEN",
        price=84499.5,
        when=NOW,
        reason="close_through_4h_channel",
        event_id="mf4-fixed-open-1",
        guard={"verdict": "ok", "daily_line": 9816.81, "worst_case_at_sl": -182.0},
        test=False,
    )


CORE_SHA256 = "f2834232bccf10d546e0ef769753042cc0becda86f09ca0960c3cb1ff818ae52"
# 90-day PF_XBTUSD host replay, 2026-07-26 12:00 through 2026-10-24 13:15 Asia/Shanghai.
EXPECTED_SIGNALS = (
    ("SHORT", "2026-07-28 12:00", 63277.0),
    ("EXIT_STOP", "2026-07-28 23:15", 63940.7),
    ("SHORT", "2026-08-12 00:00", 63553.0),
    ("EXIT_STOP", "2026-08-12 17:30", 64018.2),
    ("LONG", "2026-08-19 00:00", 64805.0),
    ("EXIT_STOP", "2026-08-19 09:30", 64360.1),
    ("LONG", "2026-08-20 00:00", 68510.0),
    ("EXIT_TARGET", "2026-08-20 16:45", 71673.6),
    ("LONG", "2026-08-20 20:00", 71869.0),
    ("EXIT_STOP", "2026-08-20 21:30", 70775.4),
    ("LONG", "2026-08-21 12:00", 74470.0),
    ("EXIT_TARGET", "2026-08-24 22:30", 79821.4),
    ("LONG", "2026-08-25 12:00", 80475.0),
    ("EXIT_STOP", "2026-08-25 15:45", 79003.7),
    ("LONG", "2026-09-04 00:00", 81355.0),
    ("EXIT_STOP", "2026-09-04 20:30", 80287.5),
    ("LONG", "2026-09-19 00:00", 80682.0),
    ("EXIT_TARGET", "2026-09-21 17:15", 84799.7),
    ("LONG", "2026-09-21 20:00", 84870.0),
    ("EXIT_STOP", "2026-09-24 00:00", 83818.0),
    ("LONG", "2026-10-02 16:00", 86085.0),
    ("EXIT_STOP", "2026-10-02 23:45", 85143.1),
    ("LONG", "2026-10-12 00:00", 83830.0),
    ("EXIT_STOP", "2026-10-12 05:15", 83228.3),
    ("LONG", "2026-10-22 00:00", 84469.0),
    ("EXIT_STOP", "2026-10-22 09:30", 83633.1),
)


def _f(value):
    return None if value is None else float(value)


def _bind_env(updates: dict[str, str | None]) -> dict[str, str | None]:
    previous = {key: os.environ.get(key) for key in updates}
    for key, value in updates.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return previous


def _restore_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _breakout(t_close: int | None = None):
    """Small PF-shaped series that breaks the 4h channel with the daily EMA50 filter on."""
    if t_close is None:
        t_close = 1_762_000_000
    t_close -= t_close % 14400
    n4 = 25
    b4 = []
    for i in range(n4):
        open_t = t_close - 14400 * (n4 - i)
        if i < n4 - 1:
            b4.append([open_t, 95.0, 100.0, 90.0, 95.0])
        else:
            b4.append([open_t, 100.0, 120.0, 100.0, 115.0])
    nd = 80
    bd = []
    for i in range(nd):
        open_t = t_close - 86400 * (nd - i)
        close = 50.0 if i < nd - 5 else 200.0
        bd.append([open_t, close, close, close, close])
    t_open = t_close - 900
    b15 = {t_open: [t_open, 115.0, 116.0, 114.0, 115.0]}
    return t_close, t_open, {row[0]: row for row in b4}, {row[0]: row for row in bd}, b15


def _env(work: Path, enabled: str = "1") -> dict[str, str]:
    """Credential file is the operator secret. Status and logs must not copy it."""
    secret_dir = work / "credentials"
    secret_dir.mkdir(parents=True, exist_ok=True)
    path = secret_dir / "webhook.env"
    path.write_text(
        "\n".join(
            [
                f"EVAL_WEBHOOK_URL={URL}",
                f"EVAL_WEBHOOK_KEY={KEY}",
                "EVAL_WEBHOOK_KEY_HEADER=Authorization",
                "EVAL_WEBHOOK_KEY_FORMAT=Bearer {key}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "MF4_WEBHOOK_ENABLED": enabled,
        "MF4_WEBHOOK_ENV_FILE": str(path),
    }


class _Logs(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


class GuardTests(unittest.TestCase):
    def test_october_22_trade_is_ok(self) -> None:
        result = evaluate(TRADE, "84499.5", now=NOW)
        self.assertEqual(result["daily_line"], 9816.81)
        self.assertEqual(result["floor"], 9400.0)
        self.assertEqual(result["target"], 11000.0)
        self.assertEqual(result["worst_case_at_sl"], -182.0)
        self.assertEqual(result["verdict"], "ok")
        self.assertGreater(result["headroom_daily"], 0)
        self.assertGreater(result["headroom_floor"], 0)
        self.assertGreater(result["est_equity"], result["daily_line"])

    def test_stale_snapshot_is_unknown(self) -> None:
        account = dict(TRADE)
        account["snapshot_at"] = (NOW - timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = evaluate(account, "84499.5", now=NOW)
        self.assertEqual(result["verdict"], "unknown")
        self.assertNotEqual(result["verdict"], "ok")
        self.assertEqual(result["reason"], "snapshot_stale")

    def test_daily_ref_before_0030_utc_is_unknown(self) -> None:
        account = dict(TRADE)
        account["daily_ref_at"] = "2026-10-21T00:30:00Z"
        result = evaluate(account, "84499.5", now=NOW)
        self.assertEqual(result["verdict"], "unknown")
        self.assertEqual(result["reason"], "daily_ref_before_reset")

    def test_warn_when_headroom_is_under_half_the_daily_budget(self) -> None:
        account = {
            "balance": "9800",
            "daily_ref_balance": "10000",
            "daily_ref_at": "2026-10-22T00:30:00Z",
            "floor": 9400,
            "target": 11000,
            "position": None,
            "snapshot_at": "2026-10-22T09:00:00Z",
        }
        result = evaluate(account, None, now=NOW)
        self.assertEqual(result["verdict"], "warn")

    def test_block_when_equity_is_through_the_floor(self) -> None:
        account = {
            "balance": "9300",
            "daily_ref_balance": "10000",
            "daily_ref_at": "2026-10-22T00:30:00Z",
            "floor": 9400,
            "target": 11000,
            "position": None,
            "snapshot_at": "2026-10-22T09:00:00Z",
        }
        result = evaluate(account, None, now=NOW)
        self.assertEqual(result["verdict"], "block")


class WebhookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logs = _Logs()
        self.logger = logging.getLogger("ops.mf4.webhook")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.logs)

    def tearDown(self) -> None:
        self.logger.removeHandler(self.logs)

    def test_default_flag_is_off_and_does_not_post(self) -> None:
        self.assertFalse(webhook_enabled({}))
        with self._tmp() as out:
            calls: list[str] = []

            def poster(url: str, headers: dict, body: bytes, timeout: float) -> int:
                calls.append(url)
                return 200

            result = dispatch(out, _payload(), env={"MF4_WEBHOOK_ENABLED": "0"}, poster=poster)
            self.assertEqual(result["skipped"], "disabled")
            self.assertEqual(calls, [])

    def test_dedup_survives_a_second_process(self) -> None:
        with self._tmp() as out:
            calls: list[int] = []

            def poster(url: str, headers: dict, body: bytes, timeout: float) -> int:
                calls.append(1)
                self.assertNotIn(KEY, url)
                self.assertNotIn(KEY, body.decode("utf-8"))
                self.assertEqual(headers["Authorization"], f"Bearer {KEY}")
                return 204

            env = _env(out)
            first = dispatch(out, _payload(), env=env, poster=poster)
            second = dispatch(out, _payload(), env=env, poster=poster)
            self.assertTrue(first["sent"])
            self.assertEqual(second["skipped"], "duplicate")
            self.assertEqual(sum(calls), 1)
            self._assert_key_absent(out)

    def test_outbox_retries_on_the_next_flush(self) -> None:
        with self._tmp() as out:
            state = {"fail": True}
            delays: list[float] = []

            def poster(url: str, headers: dict, body: bytes, timeout: float) -> int:
                if state["fail"]:
                    raise OSError(f"down {URL} {KEY}")
                return 200

            env = _env(out)
            failed = dispatch(out, _payload(), env=env, poster=poster, sleeper=delays.append)
            self.assertTrue(failed["queued"])
            self.assertEqual(delays, [2, 5, 15])
            self.assertTrue((out / "webhook_outbox.jsonl").is_file())
            state["fail"] = False
            delivered = flush_outbox(out, env=env, poster=poster, sleeper=lambda _seconds: None)
            self.assertEqual(delivered, 1)
            self.assertEqual((out / "webhook_outbox.jsonl").read_text(encoding="utf-8"), "")
            self._assert_key_absent(out)

    def test_send_test_posts_without_enabling_the_flag(self) -> None:
        with self._tmp() as out:
            seen: list[dict] = []

            def poster(url: str, headers: dict, body: bytes, timeout: float) -> int:
                seen.append(json.loads(body.decode("utf-8")))
                return 200

            code = send_test(out, env=_env(out, enabled="0"), poster=poster, sleeper=lambda _seconds: None)
            self.assertEqual(code, 0)
            self.assertTrue(seen[0]["test"])
            self.assertEqual(seen[0]["source"], "anchor-host")
            self.assertEqual(seen[0]["strategy"], "MF4_BRK4H_4R")
            self.assertFalse(webhook_enabled({"MF4_WEBHOOK_ENABLED": "0"}))
            self._assert_key_absent(out)

    def _assert_key_absent(self, out: Path) -> None:
        blob = "\n".join(self.logs.lines)
        for path in out.rglob("*"):
            if not path.is_file() or path.name == "webhook.env":
                continue
            blob += path.read_text(encoding="utf-8", errors="replace")
        self.assertNotIn(KEY, blob)
        self.assertNotIn(URL, blob)

    def _tmp(self):
        return tempfile_cm()


class WatcherTests(unittest.TestCase):
    def test_open_signal_does_not_wait_for_the_webhook(self) -> None:
        release = threading.Event()
        finished = threading.Event()
        seen: list[bytes] = []
        with tempfile_cm() as out:
            def poster(url: str, headers: dict, body: bytes, timeout: float) -> int:
                seen.append(body)
                self.assertNotIn(KEY, body.decode("utf-8"))
                self.assertEqual(headers["Authorization"], f"Bearer {KEY}")
                release.wait(2)
                finished.set()
                return 200

            env = _bind_env({**_env(out, enabled="1"), "MF4_OUT_DIR": str(out)})
            events: list[dict] = []
            original = watcher_mod.append_event
            watcher_mod.append_event = lambda event: events.append(event) or event
            try:
                watcher = self._watcher(out)
                watcher.poster = poster
                watcher.sleeper = lambda _seconds: None
                watcher.now = NOW
                _t_close, t_open, b4, bd, b15 = _breakout()
                watcher.b4 = b4
                watcher.bd = bd
                watcher.b15 = b15
                started = datetime.now(timezone.utc)
                watcher.step(t_open)
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                self.assertLess(elapsed, 0.8)
                release.set()
                self.assertTrue(finished.wait(2))
                deadline = time.time() + 2
                last_ok = None
                while time.time() < deadline:
                    state_path = out / "webhook_state.json"
                    if state_path.is_file():
                        try:
                            last_ok = json.loads(state_path.read_text(encoding="utf-8")).get("last_ok_at_sh")
                        except json.JSONDecodeError:
                            last_ok = None
                    if last_ok:
                        break
                    time.sleep(0.02)
                self.assertTrue(last_ok)
                watcher.proc = t_open
                status = watcher.status()
            finally:
                watcher_mod.append_event = original
                _restore_env(env)
            self.assertEqual(status["state"], "long")
            self.assertEqual(status["last_signal"]["type"], "OPEN")
            self.assertEqual(status["last_signal"]["side"], "long")
            self.assertIsNone(status["guard"])
            self.assertTrue(status["webhook"]["enabled"])
            opened = [event for event in events if event["event_type"] == "OPEN"]
            self.assertEqual(len(opened), 1)
            for name in EX_ANTE_FIELDS:
                self.assertIn(name, opened[0])
            self.assertEqual(len(EX_ANTE_FIELDS), 16)
            self.assertEqual(len(seen), 1)
            self.assertNotIn(KEY, json.dumps(status))

    def test_disabled_webhook_still_writes_guard_and_status_fields(self) -> None:
        with tempfile_cm() as out:
            write_account(out, TRADE)
            calls: list[int] = []
            env = _bind_env({"MF4_OUT_DIR": str(out), "MF4_WEBHOOK_ENABLED": "0", "MF4_WEBHOOK_ENV_FILE": None})
            try:
                bar_t = int(NOW.timestamp()) // 900 * 900
                if (bar_t + 900) % 14400 == 0:
                    bar_t -= 900
                close_4h = int(NOW.timestamp()) // 14400 * 14400
                (out / "compare.jsonl").write_text(
                    "\n".join(
                        [
                            json.dumps({"match": True, "at": "2026-10-24 08:00"}),
                            json.dumps({"match": False, "at": "2026-10-24 12:00"}),
                            json.dumps({"match": True, "at": "2026-10-24 13:00"}),
                            json.dumps({"match": True}),
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )
                watcher = Watcher()
                watcher.poster = lambda *args, **kwargs: calls.append(1)
                watcher.now = NOW
                watcher.proc = bar_t
                watcher.b15 = {bar_t: [bar_t, 84499.5, 84500.0, 84400.0, 84499.5]}
                watcher.b4 = {}
                watcher.bd = {}
                watcher.last = {
                    "side": None,
                    "close": 84490.0,
                    "hh20": 85000.0,
                    "ll20": 82000.0,
                    "daily_close": 86000.0,
                    "daily_ema50": 80000.0,
                    "atr4h": 400.0,
                    "bar4h_close_utc": close_4h,
                    "daily_bar_utc": close_4h - 86400,
                }
                watcher.last_signal = {
                    "type": "OPEN",
                    "side": "long",
                    "price": 84469.0,
                    "at_sh": "2026-10-22 00:00",
                }
                watcher.reason = "NO_SIGNAL"
                watcher.step(bar_t)
                status = watcher.status()
                backend = str(ROOT / "anchor-backend")
                if backend not in sys.path:
                    sys.path.insert(0, backend)
                from app.mcp.mf4_eval import MF4_DIR_ENV, read_mf4_status

                shown = read_mf4_status({MF4_DIR_ENV: str(out)}, NOW)
            finally:
                _restore_env(env)
            self.assertEqual(calls, [])
            self.assertFalse(status["webhook"]["enabled"])
            self.assertEqual(_f(status["guard"]["daily_line"]), 9816.81)
            self.assertEqual(status["guard"]["verdict"], "ok")
            self.assertEqual(_f(status["guard"]["worst_case_at_sl"]), -182.0)
            self.assertEqual(_f(status["guard"]["planned_risk"]), 150.0)
            self.assertEqual(_f(status["guard"]["size"]), 0.16)
            self.assertEqual(status["guard"]["account_status"], "running")
            self.assertEqual(status["guard"]["reason"], "within_lines")
            self.assertEqual(_f(status["price"]["last"]), 84499.5)
            self.assertEqual(status["price"]["at"], "2026-10-22T10:00:00Z")
            self.assertEqual(_f(status["last_4h_close"]["close"]), 84490.0)
            self.assertEqual(status["last_signal"]["type"], "OPEN")
            self.assertEqual(status["compare"]["consecutive_matches"], 2)
            self.assertEqual(status["compare"]["last_diff_at"], "2026-10-24 12:00")
            self.assertEqual(status["trend"], "up(long only)")
            self.assertTrue(shown["available"])
            self.assertEqual(shown["price"]["fresh"], True)
            self.assertEqual(shown["price"]["last"], 84499.5)
            self.assertEqual(shown["last_4h_close"]["close"], 84490.0)
            self.assertEqual(shown["last_signal"]["side"], "long")
            self.assertEqual(shown["compare"]["consecutive_matches"], 2)
            self.assertEqual(shown["compare"]["last_diff_at"], "2026-10-24 12:00")
            self.assertFalse(shown["webhook"]["enabled"])
            self.assertEqual(_f(shown["long_trigger_gt"]), 85000.0)

    def test_resume_loads_text_numbers_and_the_stop_still_fires(self) -> None:
        with tempfile_cm() as out:
            env = _bind_env({"MF4_OUT_DIR": str(out), "MF4_WEBHOOK_ENABLED": "0"})
            events: list[dict] = []
            original = watcher_mod.append_event
            watcher_mod.append_event = lambda event: events.append(event) or event
            try:
                t = 1_760_000_000
                t -= t % 900
                if (t + 900) % 14400 == 0:
                    t -= 900
                state = {
                    "proc": t - 900,
                    "equity": 10000.0,
                    "pos": {
                        "side": "long",
                        "entry": 84469.0,
                        "stop": 83633.1,
                        "target": 87812.6,
                        "sd": 835.9,
                        "size": 0.176,
                        "trade_id": "tr_mf4_2026-10-22",
                        "equity_at_open": "10000",
                        "risk_usd": 150.0,
                    },
                    "last": {
                        "side": "long",
                        "close": 84469.0,
                        "hh20": 84846.2,
                        "ll20": 80422.4,
                        "daily_close": 84000.0,
                        "daily_ema50": 80000.0,
                        "atr4h": 500.0,
                        "bar4h_close_utc": t,
                        "daily_bar_utc": t - 86400,
                    },
                    "last_signal": {
                        "type": "OPEN",
                        "side": "long",
                        "price": 84469.0,
                        "at_sh": "2026-10-22 00:00",
                    },
                    "reason": "MF4_LONG",
                }
                write_json(str(out / "state.json"), state)
                loaded = json.loads((out / "state.json").read_text(encoding="utf-8"))
                self.assertIsInstance(loaded["pos"]["stop"], str)
                watcher = Watcher()
                watcher.resume_from(loaded)
                self.assertIsInstance(watcher.pos["stop"], float)
                self.assertEqual(watcher.pos["side"], "long")
                watcher.b15 = {t: [t, 84000.0, 84100.0, 83600.0, 83900.0]}
                watcher.b4 = {}
                watcher.bd = {}
                watcher.now = NOW
                watcher.step(t)
                watcher.proc = t
                status = watcher.status()
            finally:
                watcher_mod.append_event = original
                _restore_env(env)
            self.assertEqual(events[0]["event_type"], "HARD_STOP_EXIT")
            self.assertEqual(round(float(events[0]["exit_price"]), 1), 83633.1)
            for name in EX_ANTE_FIELDS:
                self.assertIn(name, events[0])
            self.assertEqual(status["state"], "flat")
            self.assertEqual(status["last_signal"]["type"], "EXIT")
            self.assertEqual(_f(status["long_trigger_gt"]), 84846.2)
            self.assertEqual(status["pos"], None)

    def test_target_exit_is_stop_first_on_the_15m_bar(self) -> None:
        with tempfile_cm() as out:
            env = _bind_env({"MF4_OUT_DIR": str(out), "MF4_WEBHOOK_ENABLED": "0"})
            events: list[dict] = []
            original = watcher_mod.append_event
            watcher_mod.append_event = lambda event: events.append(event) or event
            try:
                watcher = self._watcher(out)
                _t_close, t_open, b4, bd, b15 = _breakout()
                watcher.b4 = b4
                watcher.bd = bd
                watcher.b15 = dict(b15)
                watcher.step(t_open)
                target = watcher.pos["target"]
                stop = watcher.pos["stop"]
                t_hit = t_open + 900
                if (t_hit + 900) % 14400 == 0:
                    t_hit += 900
                watcher.b15[t_hit] = [t_hit, target - 1, target + 1, stop + 1, target]
                watcher.step(t_hit)
            finally:
                watcher_mod.append_event = original
                _restore_env(env)
            kinds = [event["event_type"] for event in events]
            self.assertEqual(kinds, ["SIGNAL_4H", "OPEN", "FLAT_EXIT"])
            self.assertIn("TARGET_4R_TOUCHED", events[-1]["reason_code"])

    def _watcher(self, out: Path) -> Watcher:
        watcher = Watcher()
        watcher.now = NOW
        return watcher

    def test_record_account_is_atomic_0640_and_refuses_sealed_paths(self) -> None:
        with tempfile_cm() as out:
            source = out / "typed.json"
            source.write_text(json.dumps(TRADE), encoding="utf-8")
            from contextlib import redirect_stdout
            from io import StringIO

            with redirect_stdout(StringIO()):
                code = record_main(["--account", str(source), "--out-dir", str(out / "dest")])
            self.assertEqual(code, 0)
            written = out / "dest" / "eval_account.json"
            self.assertEqual(stat.S_IMODE(written.stat().st_mode), 0o640)
            self.assertEqual(json.loads(written.read_text(encoding="utf-8"))["balance"], "10120.42")
        self.assertIsNotNone(sealed_reason(Path("/var/lib/private/anchor-official-ledger-20261010")))
        with self.assertRaises(ValueError):
            write_account(Path("/var/lib/private/anchor-official-ledger-20261010"), TRADE)

    def test_core_file_is_the_live_mf4_bytes(self) -> None:
        path = ROOT / "ops" / "mf4" / "_b1_core.py"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, CORE_SHA256)
        text = path.read_text(encoding="utf-8")
        self.assertIn("https://futures.kraken.com/api/charts/v1/trade/PF_XBTUSD/", text)
        self.assertEqual(_b1_core.LOOKBACK, 20)
        self.assertEqual(_b1_core.EMA_N, 50)
        self.assertEqual(_b1_core.MIN_SD, 0.0035)
        self.assertEqual(_b1_core.TP_R, 4.0)
        self.assertFalse(hasattr(_b1_core, "decide"))
        source = (ROOT / "ops" / "mf4" / "mf4_host_watcher.py").read_text(encoding="utf-8")
        self.assertIn("os.environ.get('MF4_RISK_USD', '150')", source)
        self.assertIn("MARKET = 'PF_XBTUSD'", source)

    def test_unit_template_and_rollback_do_not_embed_the_key(self) -> None:
        unit = (ROOT / "ops" / "mf4" / "anchor-mf4-watcher.service").read_text(encoding="utf-8")
        diff = (ROOT / "ops" / "mf4" / "anchor-mf4-watcher.service.diff").read_text(encoding="utf-8")
        rollback = (ROOT / "ops" / "mf4" / "ROLLBACK_MF4_WATCHER.sh").read_text(encoding="utf-8")
        self.assertIn("LoadCredential=webhook:/etc/anchor-mf4-watcher/webhook.env", unit)
        self.assertIn("Environment=MF4_RISK_USD=150", unit)
        self.assertIn("Environment=MF4_WEBHOOK_ENABLED=0", unit)
        self.assertIn("/etc/anchor-mf4-watcher", unit)
        self.assertIn("LoadCredential=webhook:/etc/anchor-mf4-watcher/webhook.env", diff)
        self.assertIn("Environment=MF4_WEBHOOK_ENABLED=0", diff)
        self.assertIn("LINE_A_TOUCHED=NO", rollback)
        self.assertIn("WEBHOOK_ENV_PRINTED=NO", rollback)
        self.assertNotIn("EVAL_WEBHOOK_KEY=", unit)
        self.assertNotIn("cat ", rollback)

    def test_tree_has_no_order_endpoint(self) -> None:
        banned = ("sendorder", "cancelorder", "place_order", "withdrawal", "addorder")
        for path in (ROOT / "ops" / "mf4").iterdir():
            if path.suffix not in {".py", ".service", ".diff", ".sh"}:
                continue
            text = path.read_text(encoding="utf-8").lower()
            for token in banned:
                self.assertNotIn(token, text, f"{path.name} contains {token}")
            if path.suffix == ".py":
                self.assertNotIn("/private/", text, path.name)

    def test_send_test_payload_is_marked_test(self) -> None:
        with tempfile_cm() as out:
            seen: list[bytes] = []

            def poster(url: str, headers: dict, body: bytes, timeout: float) -> int:
                seen.append(body)
                return 200

            payload = build_payload(
                signal="TEST",
                price=0,
                when=NOW,
                reason="operator_send_test",
                event_id=event_id_for("TEST", "none", "fixed"),
                guard=None,
                test=True,
            )
            result = dispatch(out, payload, env=_env(out, "0"), poster=poster, force=True)
            self.assertTrue(result["sent"])
            self.assertTrue(json.loads(seen[0].decode("utf-8"))["test"])
            with self.assertRaises(SystemExit) as raised:
                main(["--help"])
            self.assertEqual(raised.exception.code, 0)
            refused = main(["--send-test", "--out-dir", "/var/lib/private/anchor-official-ledger-20261010"])
            self.assertEqual(refused, 2)


class tempfile_cm:  # noqa: N801 - small context helper
    def __enter__(self) -> Path:
        import tempfile

        self._cm = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        return Path(self._cm.__enter__())

    def __exit__(self, exc_type, exc, tb) -> None:
        self._cm.__exit__(exc_type, exc, tb)


class DeliverIsolationTests(unittest.TestCase):
    def test_network_error_does_not_raise(self) -> None:
        from ops.mf4.mf4_webhook import WebhookConfig

        config = WebhookConfig(url=URL, key=KEY, header_name="Authorization", key_format="Bearer {key}")

        def poster(url: str, headers: dict, body: bytes, timeout: float) -> int:
            raise TimeoutError(KEY)

        ok, detail = deliver(config=config, payload={"event_id": "x"}, poster=poster, sleeper=lambda _seconds: None)
        self.assertFalse(ok)
        self.assertNotIn(KEY, detail)


class ReplayTests(unittest.TestCase):
    def test_ninety_day_pf_fixture_matches_the_live_host(self) -> None:
        """13 trades / 26 signals, 2026-07-26 12:00 through 2026-10-24 13:15 Asia/Shanghai."""
        original_open = urllib.request.urlopen

        def _refuse_network(*_args, **_kwargs):
            raise AssertionError("network")

        urllib.request.urlopen = _refuse_network
        events: list[dict] = []
        original_append = watcher_mod.append_event
        original_risk = watcher_mod.RISK_USD
        watcher_mod.append_event = lambda event: events.append(event) or event
        watcher_mod.RISK_USD = 150.0
        env = _bind_env({"MF4_WEBHOOK_ENABLED": "0"})
        signals = []
        closes = 0
        skipped = 0
        watcher = Watcher()
        try:
            with gzip.open(ROOT / "tests" / "fixtures" / "mf4_pf_xbtusd_90d.json.gz", "rt", encoding="utf-8") as handle:
                data = json.load(handle)
            self.assertEqual(data["pair"], "PF_XBTUSD")
            self.assertEqual(data["window_sh"], ["2026-07-26 12:00", "2026-10-24 13:15"])
            watcher.b15 = {row[0]: row for row in data["b15"]}
            watcher.b4 = {row[0]: row for row in data["b4"]}
            watcher.bd = {row[0]: row for row in data["bd"]}
            for row in data["b15"]:
                t = row[0]
                start = len(events)
                watcher.step(t)
                for event in events[start:]:
                    kind = event["event_type"]
                    if kind == "SIGNAL_4H":
                        closes += 1
                    elif kind == "SIGNAL_4H_SKIPPED":
                        skipped += 1
                    elif kind == "OPEN":
                        signals.append((event["side"], watcher_mod.sh(t + 900), round(float(event["effective_price"]), 1)))
                    elif kind in ("HARD_STOP_EXIT", "FLAT_EXIT"):
                        label = "EXIT_STOP" if kind == "HARD_STOP_EXIT" else "EXIT_TARGET"
                        signals.append((label, watcher_mod.sh(t), round(float(event["exit_price"]), 1)))
        finally:
            urllib.request.urlopen = original_open
            watcher_mod.append_event = original_append
            watcher_mod.RISK_USD = original_risk
            _restore_env(env)
        self.assertEqual(signals, list(EXPECTED_SIGNALS))
        self.assertEqual(len(signals), 26)
        self.assertEqual(sum(1 for kind, _at, _price in signals if kind in {"LONG", "SHORT"}), 13)
        self.assertEqual(closes, 540)
        self.assertEqual(skipped, 0)
        self.assertEqual(signals[-2], ("LONG", "2026-10-22 00:00", 84469.0))
        self.assertEqual(signals[-1], ("EXIT_STOP", "2026-10-22 09:30", 83633.1))
        self.assertIsNone(watcher.pos)

    def test_forward_stream_chain_verifies(self) -> None:
        with tempfile_cm() as out:
            env = _bind_env({"MF4_OUT_DIR": str(out), "MF4_WEBHOOK_ENABLED": "0"})
            try:
                first = watcher_mod.append_event({"event_type": "SERVICE_START", "reason_code": "TEST"})
                second = watcher_mod.append_event({"event_type": "SIGNAL_4H", "reason_code": "NO_SIGNAL"})
                path = out / "mf4_forward_events.jsonl"
                self.assertEqual(first["prev_hash"], "GENESIS")
                self.assertEqual(second["prev_hash"], first["row_hash"])
                self.assertEqual(watcher_mod.row_hash(first), first["row_hash"])
                self.assertEqual(watcher_mod.row_hash(second), second["row_hash"])
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "ops" / "mf4" / "verify_chain.py"), str(path)],
                    check=False,
                    capture_output=True,
                    text=True,
                    cwd=str(ROOT),
                    env={**os.environ, "PYTHONPATH": str(ROOT), "MF4_OUT_DIR": str(out)},
                )
            finally:
                _restore_env(env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("OK", proc.stdout)
            self.assertIn("2", proc.stdout)


if __name__ == "__main__":
    unittest.main()
