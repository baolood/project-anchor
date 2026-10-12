#!/usr/bin/env python3
"""Track deterministic paper results for promoted Kraken Prop candidates."""

from __future__ import annotations

import argparse
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backtest_kraken_prop_strategy import fetch_futures_ohlc
from research_kraken_prop_strategies import simulate
from walk_forward_kraken_prop_strategies import candidates

import availability_fill_v1 as sim_v1


PROMOTED = (
    "breakout_55_strength_1pct",
    "breakout_55",
    "ema_50_100_strength_1pct",
)
SYMBOLS = ("PI_XBTUSD", "PI_ETHUSD")

# Additive run-state vocabulary. An ABSENT round record means the outcome is
# UNKNOWN, never "missed"; only scheduling-side evidence may establish that a run
# was missed. This artifact therefore emits no missed/skipped marker at all.
ROUND_STATUS_WITH_SIGNAL = "SUCCESS_WITH_SIGNAL"
ROUND_STATUS_NO_SIGNAL = "SUCCESS_NO_SIGNAL"
ROUND_STATUS_FAILED = "FAILED"
RECORD_ABSENCE_POLICY = "ABSENT_RECORD_MEANS_UNKNOWN"
RECORD_ABSENCE_NOTE = (
    "An absent round record means the outcome is UNKNOWN, never 'missed'. This "
    "artifact emits no missed/skipped marker anywhere; only scheduling-side "
    "evidence (an external scheduler's own record) may establish that a run was "
    "missed."
)


class ValidationError(ValueError):
    """A computed snapshot that must not be published."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def clock() -> datetime:
    """Current UTC instant; tests replace this module attribute to control the clock."""
    return datetime.now(timezone.utc)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValidationError(reason)


def validate_snapshot(payload: dict) -> None:
    """Minimal pre-publish validation of a computed snapshot.

    A snapshot that fails any check is abnormal: it must not be published and the
    round must not be marked as completed.
    """
    strategy_count = payload.get("strategy_count")
    market_count = payload.get("market_count")
    require(type(strategy_count) is int, "strategy_count_type")
    require(type(market_count) is int, "market_count_type")

    require(payload.get("result") == "PASS", "result_not_pass")
    require(
        payload.get("decision") in ("OBSERVE", "REVIEW_FOR_PROMOTION"),
        "invalid_decision",
    )
    require(
        isinstance(payload.get("generated_at"), str) and bool(payload["generated_at"]),
        "invalid_generated_at",
    )

    started_raw = payload.get("observation_started_at")
    require(isinstance(started_raw, str) and bool(started_raw), "invalid_observation_started_at")
    try:
        datetime.fromisoformat(started_raw)
    except ValueError:
        raise ValidationError("invalid_observation_started_at") from None

    observations = payload.get("observations")
    require(isinstance(observations, list), "observations_not_list")
    require(
        len(observations) == strategy_count * market_count,
        "observation_count_mismatch",
    )

    for observation in observations:
        require(isinstance(observation, dict), "observation_not_dict")
        for key in (
            "strategy",
            "symbol",
            "resolution",
            "latest_closed_candle_at",
            "signal_events_since_start",
            "current_signal",
            "new_signal",
            "paper_metrics",
        ):
            require(key in observation, "missing_observation_key")
        require(
            isinstance(observation["strategy"], str) and bool(observation["strategy"]),
            "invalid_strategy",
        )
        require(
            isinstance(observation["symbol"], str) and bool(observation["symbol"]),
            "invalid_symbol",
        )
        require(
            observation["current_signal"] in ("BUY", "SELL", "NONE"),
            "invalid_current_signal",
        )
        require(type(observation["new_signal"]) is bool, "invalid_new_signal")
        require(
            type(observation["signal_events_since_start"]) is int,
            "invalid_signal_events",
        )

        metrics = observation["paper_metrics"]
        require(isinstance(metrics, dict), "invalid_paper_metrics")
        for key, value in metrics.items():
            if value is None:
                # Legitimate "not computable" result (for example profit_factor
                # with zero gross loss); not a non-finite number.
                require(key == "profit_factor", "invalid_paper_metrics")
                continue
            require(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value),
                "non_finite_metric",
            )


def first_index_at_or_after(rows: list[dict[str, float]], timestamp: float) -> int:
    for index, row in enumerate(rows):
        if row["time"] >= timestamp:
            return index
    return len(rows)


def build_snapshot(
    market_rows: dict[str, list[dict[str, float]]],
    started_at: datetime,
    round_id: str | None = None,
) -> dict:
    """Build the round snapshot.

    ``round_id`` links every observation (and therefore every signal) to the round
    that produced it. It is generated once per snapshot when not supplied.
    """
    round_id = round_id or uuid.uuid4().hex
    builders = candidates()
    results = []
    for strategy in PROMOTED:
        signal_fn = builders[strategy]
        for symbol in SYMBOLS:
            rows = market_rows[symbol]
            signals = signal_fn(rows)
            start = first_index_at_or_after(rows, started_at.timestamp())
            metrics = simulate(rows, signals, start, len(rows))
            signal_events = sum(
                bool(signals[index]) and signals[index] != signals[index - 1]
                for index in range(max(start, 1), len(signals))
            )
            current = signals[-1]
            previous = signals[-2]
            latest_row = rows[-1]
            results.append({
                "strategy": strategy,
                "symbol": symbol,
                "resolution": "4h",
                # LEGACY SEMANTICS (documented, value unchanged): despite its name,
                # `latest_closed_candle_at` stores the OPEN time of the last closed
                # candle, not its close.
                "latest_closed_candle_at": datetime.fromtimestamp(
                    latest_row["time"], timezone.utc
                ).isoformat(),
                # NOMINAL bar boundaries, reused from the shared fetch (never
                # recomputed here). `bar_close_at` is the nominal close: it is not
                # arrival proof and not a computation/publish instant. If a row
                # carries no boundary, the value is None ("unknown") rather than a
                # fabricated instant.
                "bar_open_at": latest_row.get("bar_open_at"),
                "bar_close_at": latest_row.get("bar_close_at"),
                "round_id": round_id,
                "signal_events_since_start": signal_events,
                "current_signal": "BUY" if current > 0 else "SELL" if current < 0 else "NONE",
                "new_signal": bool(current) and current != previous,
                "paper_metrics": metrics,
            })
    closed_trades = sum(item["paper_metrics"]["trades"] for item in results)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "observation_started_at": started_at.isoformat(),
        "round_id": round_id,
        "result": "PASS",
        "decision": "OBSERVE" if closed_trades < 60 else "REVIEW_FOR_PROMOTION",
        "strategy_count": len(PROMOTED),
        "market_count": len(SYMBOLS),
        "closed_paper_trades": closed_trades,
        "minimum_closed_trades_for_review": 60,
        "observations": results,
        "private_api_attempted": False,
        "credential_file_read": False,
        "production_order_sent": False,
    }


def to_markdown(payload: dict) -> str:
    lines = [
        "# Kraken Prop Forward Observation",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Observation started: {payload['observation_started_at']}",
        f"- Decision: **{payload['decision']}**",
        f"- Closed paper trades: {payload['closed_paper_trades']}/{payload['minimum_closed_trades_for_review']}",
        "",
        "| Strategy | Market | Current | New signal | Events | Closed trades | Net PnL | PF | Max DD |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in payload["observations"]:
        metrics = item["paper_metrics"]
        lines.append(
            f"| {item['strategy']} | {item['symbol']} | {item['current_signal']} | "
            f"{'YES' if item['new_signal'] else 'NO'} | {item['signal_events_since_start']} | "
            f"{metrics['trades']} | {metrics['net_pnl']} | {metrics['profit_factor']} | "
            f"{metrics['max_drawdown_pct']}% |"
        )
    lines += [
        "",
        "## Safety",
        "",
        "- Public market data only: YES",
        "- Credential file read: NO",
        "- Private API attempted: NO",
        "- Production order sent: NO",
        "",
    ]
    return "\n".join(lines)


def load_or_initialize_start(state_path: Path, now: datetime) -> datetime:
    if state_path.is_file():
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        return datetime.fromisoformat(payload["observation_started_at"])
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"observation_started_at": now.isoformat()}, indent=2) + "\n",
        encoding="utf-8",
    )
    return now


def write_artifacts(out_json: Path, out_md: Path, payload: dict) -> None:
    """Write the JSON and Markdown artifacts; propagates OSError on failure."""
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(to_markdown(payload), encoding="utf-8")


def round_record_path(rounds_dir: Path, round_id: str) -> Path:
    return rounds_dir / f"round.{round_id}.json"


def write_round_record(rounds_dir: Path, record: dict) -> Path:
    """Write the per-round run-state record; propagates OSError on failure."""
    rounds_dir.mkdir(parents=True, exist_ok=True)
    path = round_record_path(rounds_dir, record["round_id"])
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def fail_round(rounds_dir: Path, round_id: str, reason: str, artifact_path: Path,
               computation_completed_at: str | None = None) -> int:
    """Emit an explicit FAILED run-state and persist it in the round record.

    The success artifact is never given a success marker by this path, and the record
    carries no `published_at`. If the round record itself cannot be written, that is
    reported explicitly and the run does not claim the publish audit completed.
    """
    print(f"ROUND_FAILED reason={reason}")
    print(f"ROUND_STATUS={ROUND_STATUS_FAILED}")
    print(f"FAILURE_REASON={reason}")
    record = {
        "round_id": round_id,
        "round_status": ROUND_STATUS_FAILED,
        "failure_reason": reason,
        "artifact_path": str(artifact_path),
        "record_absence_policy": RECORD_ABSENCE_POLICY,
        "record_absence_note": RECORD_ABSENCE_NOTE,
    }
    if computation_completed_at is not None:
        record["computation_completed_at"] = computation_completed_at
    try:
        path = write_round_record(rounds_dir, record)
    except OSError as exc:
        print(f"ROUND_RECORD_WRITE_FAILED reason={type(exc).__name__}")
        return 3
    print(f"ROUND_RECORD={path}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Track Kraken Prop forward paper evidence.")
    parser.add_argument("--state", type=Path, default=Path("reports/kraken_prop/forward-observation-state.json"))
    parser.add_argument("--out-json", type=Path, default=Path("reports/kraken_prop/forward-observation-latest.json"))
    parser.add_argument("--out-md", type=Path, default=Path("reports/kraken_prop/forward-observation-latest.md"))
    parser.add_argument("--round-record-dir", type=Path, default=Path("reports/kraken_prop/rounds"))
    parser.add_argument("--sim-state-v1", type=Path,
                        default=Path("reports/kraken_prop/sim-state-v1.json"))
    parser.add_argument("--availability-out-json", type=Path,
                        default=Path("reports/kraken_prop/sim-availability-v1-latest.json"))
    parser.add_argument("--round-id", type=str, default=None,
                        help="reuse a round id (retry of the same round; never a catch-up round)")
    parser.add_argument("--lookback-days", type=int, default=180)
    args = parser.parse_args()

    now = clock()
    started_at = load_or_initialize_start(args.state, now)
    market_rows = {
        symbol: fetch_futures_ohlc(
            "https://futures.kraken.com", symbol, "4h", args.lookback_days
        )
        for symbol in SYMBOLS
    }
    payload = build_snapshot(market_rows, started_at, round_id=args.round_id)
    round_id = payload["round_id"]
    try:
        validate_snapshot(payload)
    except ValidationError as error:
        return fail_round(args.round_record_dir, round_id, error.reason, args.out_json)

    # T2 - computation AND validation are complete. This is the round's completion
    # instant (existing field, reused; not duplicated) and it stays in the artifact.
    payload["observation_completed_at"] = clock().isoformat()

    # Run state is NOT stored in the success artifact: it lives in the separate
    # per-round record written below. "with signal" == at least one observation has
    # new_signal true.
    has_signal = any(observation["new_signal"] for observation in payload["observations"])
    round_status = ROUND_STATUS_WITH_SIGNAL if has_signal else ROUND_STATUS_NO_SIGNAL

    # --- simulation v1 (additive): plan BEFORE publishing A -------------------
    # A carries signal-driven correlation ids only: NO T3 of its own and NO claim that
    # the instructions were registered. Both live in the later record written below.
    sim_state = sim_v1.load_state(args.sim_state_v1)
    current_signals: dict[str, int] = {}
    signal_closes: dict[str, str | None] = {}
    series_by_pair: dict[str, list] = {}
    for observation in payload["observations"]:
        pair = sim_v1.pair_key(observation["strategy"], observation["symbol"])
        current_signals[pair] = (
            1 if observation["current_signal"] == "BUY"
            else -1 if observation["current_signal"] == "SELL" else 0
        )
        signal_closes[pair] = observation["bar_close_at"]
        series_by_pair[pair] = market_rows[observation["symbol"]]
    plan = sim_v1.plan_round(sim_state, round_id=round_id, current_signals=current_signals,
                             signal_bar_close_at=signal_closes)
    payload["simulation_v1"] = sim_v1.build_artifact_a(plan, round_id=round_id)

    # Publish the artifact. The success artifact may carry `round_id` only: no run
    # state, no failure reason, no publication timestamp.
    try:
        write_artifacts(args.out_json, args.out_md, payload)
    except OSError:
        return fail_round(args.round_record_dir, round_id, "artifact_write_failed", args.out_json,
                          computation_completed_at=payload["observation_completed_at"])

    # T3 - publication instant. Captured ONLY after the artifact was written
    # successfully; a pre-write timestamp is never presented as publication success.
    published_at = clock().isoformat()

    # --- simulation v1: backlog first, then register; state saved before B -----
    # Order is binding: the engine advances over already-closed bars with the OLD
    # pending instructions, and only then registers THIS round's instructions, so a
    # new signal can never erase a fill that was already due.
    sim_block: dict = {"fill_rule_version": sim_v1.FILL_RULE_VERSION, "b_write_status": "OK"}
    b_write_error: str | None = None

    def write_b(report: dict) -> None:
        # B deliberately carries no timestamp taken after this write; T3' is recorded
        # in the round record instead.
        args.availability_out_json.parent.mkdir(parents=True, exist_ok=True)
        args.availability_out_json.write_text(json.dumps(report, indent=2) + "\n",
                                              encoding="utf-8")

    sim_result = None
    try:
        sim_result = sim_v1.execute_round(
            sim_state, round_id=round_id, t3=published_at,
            series_by_pair=series_by_pair, current_signals=current_signals,
            signal_bar_close_at=signal_closes, state_path=args.sim_state_v1,
            report_writer=write_b)
    except OSError as error:
        b_write_error = type(error).__name__
        sim_block["b_write_status"] = "FAILED"
        sim_block["b_write_error"] = b_write_error

    if sim_result is not None:
        report = sim_result["report"]
        sim_block["b_artifact_path"] = str(args.availability_out_json)
        sim_block["b_published_at"] = clock().isoformat()   # T3' - after B was written
        sim_block["advance_applied"] = report["advance_applied"]
        sim_block["registered_instructions"] = report["registered_instructions"]
        sim_block["metrics_v1"] = report["metrics_v1"]

    record = {
        "round_id": round_id,
        "round_status": round_status,
        "computation_completed_at": payload["observation_completed_at"],
        "published_at": published_at,
        "artifact_path": str(args.out_json),
        "simulation_v1": sim_block,
        "record_absence_policy": RECORD_ABSENCE_POLICY,
        "record_absence_note": RECORD_ABSENCE_NOTE,
    }
    try:
        record_path = write_round_record(args.round_record_dir, record)
    except OSError as error:
        # The artifact was published but its run-state record was not. Report that
        # explicitly and do NOT claim the publish audit completed.
        print(f"ROUND_RECORD_WRITE_FAILED reason={type(error).__name__}")
        print(f"ROUND_ID={round_id}")
        return 3

    print(f"RESULT={payload['result']}")
    print(f"DECISION={payload['decision']}")
    print(f"CLOSED_PAPER_TRADES={payload['closed_paper_trades']}")
    print(f"ROUND_ID={round_id}")
    print(f"ROUND_STATUS={round_status}")
    print(f"ROUND_RECORD={record_path}")
    print("CREDENTIAL_FILE_READ=NO")
    print("PRIVATE_API_ATTEMPTED=NO")
    print("PRODUCTION_ORDER_SENT=NO")
    print(f"ROUND_COMPLETED_AT={payload['observation_completed_at']}")
    print(f"PUBLISHED_AT={published_at}")
    print(f"SIM_FILL_RULE_VERSION={sim_v1.FILL_RULE_VERSION}")
    print(f"SIM_B_WRITE_STATUS={sim_block['b_write_status']}")
    if sim_result is not None:
        print(f"SIM_B_PUBLISHED_AT={sim_block['b_published_at']}")
        print(f"SIM_TRADES_V1={sum(i['trades'] for i in sim_block['metrics_v1'].values())}")
        print(f"SIM_NET_PNL_V1={sum(i['net_pnl'] for i in sim_block['metrics_v1'].values())}")
    # A failed B write is reported explicitly: the engine state is already saved, so the
    # same round can be retried without duplicating fills or fees.
    if b_write_error is not None:
        print(f"SIM_B_WRITE_FAILED reason={b_write_error}")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
