"""Fill price and fill time stay on the current bar-open rule."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.official_ledger.engine import (
    BAR_NOT_YET_CLOSED,
    CANDLE_FETCH_UNIT,
    DATA_GAP,
    LEDGER_UNIT,
    PENDING_NEXT_BAR,
    POLICY_ENV,
    commit_observation,
    parse_time,
    pending_reason,
    planned_fill,
    render_candle_success_drop_in,
    render_ledger_after_candle_drop_in,
    render_pending_policy_drop_in,
    resolve_fill_bar,
)


ORDER_MARKER = "synthetic-order-should-not-echo"
OPEN_PRICE = "100.25"
OTHER_OPEN = "999.00"
CLOSE_PRICE = "110.50"
DOCS = Path(__file__).resolve().parents[1] / "docs" / "systemd"


def _signal() -> dict[str, str]:
    return {
        "signal_id": "sig-1",
        "signal_available_at": "2026-10-12T10:05:00Z",
        "signal_candle_open_utc": "2026-10-12T09:00:00Z",
        "fill_event_type": "OPEN",
        "order_id": ORDER_MARKER,
    }


def _candles() -> list[dict[str, str]]:
    return [
        {
            "open_time": "2026-10-12T10:00:00Z",
            "open": OTHER_OPEN,
            "close": "1000.00",
        },
        {
            "open_time": "2026-10-12T11:00:00Z",
            "open": OPEN_PRICE,
            "high": "101.00",
            "low": "99.00",
            "close": CLOSE_PRICE,
        },
    ]


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class FillRuleTests(unittest.TestCase):
    def test_fill_bar_is_the_first_hour_open_after_signal(self) -> None:
        self.assertEqual(
            resolve_fill_bar(parse_time("2026-10-12T10:05:00Z")).isoformat(),
            "2026-10-12T11:00:00+00:00",
        )
        self.assertEqual(
            resolve_fill_bar(parse_time("2026-10-12T11:00:00Z")).isoformat(),
            "2026-10-12T12:00:00+00:00",
        )

    def test_replay_matches_the_current_rule_price_and_timestamp(self) -> None:
        now = datetime(2026, 10, 12, 12, 10, tzinfo=timezone.utc)
        plan = planned_fill(_signal(), _candles(), now)
        self.assertIsNone(plan["pending_reason"])
        self.assertEqual(plan["fill_time_utc"], "2026-10-12T11:00:00Z")
        self.assertEqual(plan["fill_price"], OPEN_PRICE)
        self.assertNotEqual(plan["fill_price"], CLOSE_PRICE)
        self.assertNotEqual(plan["fill_price"], OTHER_OPEN)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            legacy_ledger = base / "legacy.jsonl"
            new_ledger = base / "new.jsonl"
            legacy_log = base / "legacy.run.log"
            new_log = base / "new.run.log"
            commit_observation(
                legacy_ledger,
                legacy_log,
                signal=_signal(),
                candles=_candles(),
                now=now,
                effective_at=None,
                attempts=4,
            )
            commit_observation(
                new_ledger,
                new_log,
                signal=_signal(),
                candles=_candles(),
                now=now,
                effective_at=datetime(2026, 10, 12, 0, 0, tzinfo=timezone.utc),
                attempts=4,
            )
            legacy = _rows(legacy_ledger)
            fresh = _rows(new_ledger)
            self.assertEqual(len(legacy), 1)
            self.assertEqual(len(fresh), 1)
            self.assertEqual(legacy[0]["fill_price"], plan["fill_price"])
            self.assertEqual(fresh[0]["fill_price"], plan["fill_price"])
            self.assertEqual(legacy[0]["fill_time_utc"], plan["fill_time_utc"])
            self.assertEqual(fresh[0]["fill_time_utc"], plan["fill_time_utc"])
            self.assertEqual(fresh[0]["signal_available_at"], "2026-10-12T10:05:00Z")
            self.assertEqual(fresh[0]["signal_candle_open_utc"], "2026-10-12T09:00:00Z")
            self.assertEqual(fresh[0]["event_type"], "OPEN")
            blob = json.dumps(legacy + fresh)
            self.assertNotIn(ORDER_MARKER, blob)
            self.assertNotIn("order_id", blob)
            self.assertFalse(legacy_log.exists())
            self.assertFalse(new_log.exists())

    def test_bar_not_yet_closed_writes_one_pending_row_and_logs_retries(self) -> None:
        now = datetime(2026, 10, 12, 11, 10, tzinfo=timezone.utc)
        self.assertEqual(pending_reason(parse_time("2026-10-12T11:00:00Z"), now, True), BAR_NOT_YET_CLOSED)
        plan = planned_fill(_signal(), _candles(), now)
        self.assertEqual(plan["pending_reason"], BAR_NOT_YET_CLOSED)
        self.assertNotIn("fill_price", plan)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            ledger = base / "ledger.jsonl"
            run_log = base / "run.log"
            parent_mode = base.stat().st_mode
            rows = commit_observation(
                ledger,
                run_log,
                signal=_signal(),
                candles=_candles(),
                now=now,
                effective_at=datetime(2026, 10, 12, 0, 0, tzinfo=timezone.utc),
                attempts=4,
            )
            self.assertEqual(len(rows), 1)
            stored = _rows(ledger)
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["event_type"], PENDING_NEXT_BAR)
            self.assertEqual(stored[0]["pending_reason"], BAR_NOT_YET_CLOSED)
            self.assertEqual(stored[0]["fill_time_utc"], "2026-10-12T11:00:00Z")
            self.assertNotIn("fill_price", stored[0])
            self.assertNotIn(OPEN_PRICE, json.dumps(stored))
            logged = _rows(run_log)
            self.assertEqual([item["attempt"] for item in logged], [2, 3, 4])
            self.assertTrue(all(item["pending_reason"] == BAR_NOT_YET_CLOSED for item in logged))
            self.assertEqual(base.stat().st_mode, parent_mode)

    def test_data_gap_is_distinct_from_a_bar_that_is_still_open(self) -> None:
        now = datetime(2026, 10, 12, 12, 10, tzinfo=timezone.utc)
        missing = [item for item in _candles() if item["open_time"] != "2026-10-12T11:00:00Z"]
        self.assertEqual(pending_reason(parse_time("2026-10-12T11:00:00Z"), now, False), DATA_GAP)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            ledger = base / "ledger.jsonl"
            run_log = base / "run.log"
            commit_observation(
                ledger,
                run_log,
                signal=_signal(),
                candles=missing,
                now=now,
                effective_at=datetime(2026, 10, 12, 0, 0, tzinfo=timezone.utc),
                attempts=3,
            )
            stored = _rows(ledger)
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["pending_reason"], DATA_GAP)
            self.assertNotIn("fill_price", stored[0])
            self.assertEqual(len(_rows(run_log)), 2)

    def test_pre_effective_rows_stay_byte_for_byte(self) -> None:
        prior = (
            '{"event_type":"PENDING_NEXT_BAR","fill_time_utc":"2026-10-12T09:00:00Z",'
            '"ledger_event_id":"le-000009","row_hash":"abc123","signal_available_at":"2026-10-12T08:05:00Z"}\n'
            '{"event_type":"OPEN","fill_price":"50.5","fill_time_utc":"2026-10-12T09:00:00Z",'
            '"ledger_event_id":"le-000010","row_hash":"def456","signal_available_at":"2026-10-12T08:05:00Z"}\n'
        ).encode("utf-8")
        effective_at = datetime(2026, 10, 12, 11, 5, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            os.chmod(base, 0o700)
            mode = base.stat().st_mode
            ledger = base / "ledger.jsonl"
            ledger.write_bytes(prior)
            run_log = base / "run.log"
            commit_observation(
                ledger,
                run_log,
                signal=_signal(),
                candles=_candles(),
                now=datetime(2026, 10, 12, 11, 0, tzinfo=timezone.utc),
                effective_at=effective_at,
                attempts=4,
            )
            body = ledger.read_bytes()
            self.assertEqual(body[: len(prior)], prior)
            self.assertGreater(len(body), len(prior))
            appended = _rows(ledger)[2:]
            self.assertEqual(len(appended), 4)
            self.assertTrue(all("pending_reason" not in row for row in appended))
            self.assertFalse(run_log.exists())
            self.assertEqual(stat.S_IMODE(base.stat().st_mode), 0o700)
            self.assertEqual(base.stat().st_mode, mode)
            commit_observation(
                ledger,
                run_log,
                signal=_signal(),
                candles=_candles(),
                now=datetime(2026, 10, 12, 11, 10, tzinfo=timezone.utc),
                effective_at=effective_at,
                attempts=4,
            )
            later = ledger.read_bytes()
            self.assertEqual(later[: len(prior)], prior)
            fresh = _rows(ledger)[-1:]
            self.assertEqual(len(_rows(run_log)), 3)
            self.assertEqual(fresh[0]["pending_reason"], BAR_NOT_YET_CLOSED)
            self.assertEqual(sum(1 for row in _rows(ledger)[6:] if row["event_type"] == PENDING_NEXT_BAR), 1)

    def test_ordering_drop_ins_do_not_touch_state_directory_settings(self) -> None:
        after = render_ledger_after_candle_drop_in()
        started = render_candle_success_drop_in()
        policy = render_pending_policy_drop_in("2026-10-13T00:00:00Z")
        self.assertEqual((DOCS / "anchor-official-ledger.service.d" / "after-candle-fetch.conf.example").read_text(encoding="utf-8"), after)
        self.assertEqual(
            (DOCS / "anchor-candle-fetch.service.d" / "start-official-ledger.conf.example").read_text(encoding="utf-8"),
            started,
        )
        self.assertEqual(
            (DOCS / "anchor-official-ledger.service.d" / "pending-policy.conf.example").read_text(encoding="utf-8"),
            policy,
        )
        self.assertIn(f"After={CANDLE_FETCH_UNIT}", after)
        self.assertIn(f"OnSuccess={LEDGER_UNIT}", started)
        self.assertIn(f"Environment={POLICY_ENV}=2026-10-13T00:00:00Z", policy)
        combined = after + started + policy
        for forbidden in ("StateDirectory=", "DynamicUser=", "chmod", "setfacl", "User="):
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
