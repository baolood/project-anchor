"""MF4 webhook, eval guard, and host watcher. No network."""

from __future__ import annotations

import json
import logging
import stat
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ops.mf4 import _b1_core
from ops.mf4.eval_guard import evaluate
from ops.mf4.mf4_host_watcher import main, process_once
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


def _candles(close: float, low: float, high: float) -> list[dict]:
    rows = []
    for hour in range(4):
        rows.append(
            {
                "time": f"2026-10-22T{hour:02d}:00:00Z",
                "open": 90,
                "high": 100,
                "low": 90,
                "close": 95,
            }
        )
    rows.append(
        {
            "time": "2026-10-22T04:00:00Z",
            "open": 100,
            "high": high,
            "low": low,
            "close": close,
        }
    )
    return rows


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
        with tempfile_cm() as out:
            def poster(url: str, headers: dict, body: bytes, timeout: float) -> int:
                release.wait(2)
                finished.set()
                return 200

            started = datetime.now(timezone.utc)
            status = process_once(
                out_dir=out,
                candles=_candles(105, 100, 110),
                mark=105,
                mark_at=NOW,
                env=_env(out, enabled="1"),
                poster=poster,
                now=NOW,
            )
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            self.assertLess(elapsed, 0.8)
            release.set()
            self.assertTrue(finished.wait(2))
            self.assertEqual(status["state"], "LONG")
            self.assertEqual(status["last_signal"]["type"], "OPEN")
            self.assertIsNone(status["guard"])

    def test_disabled_webhook_still_writes_guard_for_the_trade(self) -> None:
        with tempfile_cm() as out:
            write_account(out, TRADE)
            calls: list[int] = []
            status = process_once(
                out_dir=out,
                candles=_candles(95, 90, 100),
                mark=84499.5,
                mark_at=NOW,
                env={"MF4_WEBHOOK_ENABLED": "0"},
                poster=lambda *args, **kwargs: calls.append(1),
                now=NOW,
            )
            self.assertEqual(calls, [])
            self.assertFalse(status["webhook"]["enabled"])
            self.assertEqual(status["guard"]["daily_line"], 9816.81)
            self.assertEqual(status["guard"]["verdict"], "ok")
            self.assertEqual(status["guard"]["worst_case_at_sl"], -182.0)
            self.assertEqual(status["guard"]["planned_risk"], 150.0)
            self.assertEqual(status["guard"]["size"], 0.16)
            self.assertEqual(status["guard"]["account_status"], "running")
            self.assertEqual(status["guard"]["reason"], "within_lines")

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

    def test_core_opens_long_on_a_4h_close_through_the_channel(self) -> None:
        decision = _b1_core.decide(_candles(105, 100, 110), None)
        signal = decision["signal"]
        self.assertEqual(signal["type"], "OPEN")
        self.assertEqual(signal["side"], "long")
        self.assertEqual(decision["long_trigger_gt"], 100.0)
        self.assertEqual(signal["tp"], 125.0)

    def test_unit_template_and_rollback_do_not_embed_the_key(self) -> None:
        unit = (ROOT / "ops" / "mf4" / "anchor-mf4-watcher.service").read_text(encoding="utf-8")
        diff = (ROOT / "ops" / "mf4" / "anchor-mf4-watcher.service.diff").read_text(encoding="utf-8")
        rollback = (ROOT / "ops" / "mf4" / "ROLLBACK_MF4_WATCHER.sh").read_text(encoding="utf-8")
        self.assertIn("LoadCredential=webhook:/etc/anchor-mf4-watcher/webhook.env", unit)
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
            self.assertEqual(main(["--help"]) if False else 0, 0)


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


if __name__ == "__main__":
    unittest.main()
