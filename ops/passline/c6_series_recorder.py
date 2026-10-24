#!/usr/bin/env python3
"""Record the C6 pass-line series. DEPLOY=NO.

This is the repo copy of the host script installed at
``/opt/anchor-passline-host/bin/c6_series_recorder.py``. Running it from a
checkout writes only under ``--root`` (default ``/var/lib/anchor-passline``).
It does not open Line A, the sealed StateDirectory, the legacy equity CSV,
or ``governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl``.

One run:

- births the v2.1 equity file (``CREATED``) or appends one FLAT row
  (``APPENDED``)
- appends one public PF_XBTUSD mark, or ``MARK_MISSING`` when the fetch
  fails. A missing mark is not replaced with a made-up price
- leaves the events JSONL empty. There is no C6 event writer
- stores public funding rates that were actually returned. A missing hour
  is a gap. It is not written as zero
- keeps writer ``funding_pnl`` null and ``open_legs`` at ``NO_OPEN_LEGS``
- appends one governance deploy record the first time, then leaves it

Exit 0 means the outcome was recorded, including a missed fetch.
Exit 2 means the root is a Line A path and nothing was written.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


def _bootstrap_repo() -> None:
    """Find eval_recording from a checkout or from the host clone.

    The git copy lives at ``ops/passline/c6_series_recorder.py``. The host
    copy lives at ``/opt/anchor-passline-host/bin/c6_series_recorder.py`` and
    imports the checkout at ``/opt/project-anchor-passline``.
    """
    here = Path(__file__).resolve()
    candidates = []
    if here.parent.name == "passline" and here.parent.parent.name == "ops":
        candidates.append(here.parents[2])
    candidates.append(Path("/opt/project-anchor-passline"))
    for candidate in candidates:
        if (candidate / "eval_recording").is_dir():
            text = str(candidate)
            if text not in sys.path:
                sys.path.insert(0, text)
            return


_bootstrap_repo()

from eval_recording.equity_v21_dual_write import (  # noqa: E402
    EQUITY_V21_COLUMNS,
    GENESIS_OBSERVATION_ID,
    MARK_RULE_UNBOUND,
    NEW_EQUITY_FILENAME,
    SAMPLE_CLASS_NON_SCORING,
    genesis_row,
    record_equity_v21,
)
from eval_recording.funding.accrual import AccrualResult  # noqa: E402
from eval_recording.funding.recording import writer_funding_record  # noqa: E402

DEPLOY = "NO"
LIVE_TRADING = "NO-GO"
SERIES_ID = "affl-v2-official-ledger-c6"
DEFAULT_ROOT = Path("/var/lib/anchor-passline")
SERIES_DIRNAME = SERIES_ID
STARTING_EQUITY = "10000"
SYMBOL = "PF_XBTUSD"
MARK_URL = "https://futures.kraken.com/derivatives/api/v3/tickers/PF_XBTUSD"
FUNDING_URL = (
    "https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=PF_XBTUSD"
)
USER_AGENT = "anchor-c6-series-recorder/1.0 (public research; no auth)"
EVENTS_NAME = "c6_events.jsonl"
MARKS_NAME = "pf_xbtusd_marks.jsonl"
FUNDING_CACHE_NAME = "PF_XBTUSD_historicalfundingrates.jsonl"
FUNDING_FAIL_NAME = "PF_XBTUSD_last_fetch_fail.json"
GOVERNANCE_NAME = "C9_SERIES_REGISTER.jsonl"
WRITER_NAME = "writer_funding.jsonl"
DIR_MODE = 0o750
FILE_MODE = 0o640
HOUR = timedelta(hours=1)

FetchMark = Callable[[], Mapping[str, Any] | None]
FetchFunding = Callable[[], Mapping[str, Any] | None]


class SeriesRootRefused(Exception):
    """The requested root is a Line A path this recorder must not write."""


def _chmod(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        return


def _mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _chmod(path, DIR_MODE)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)
    _chmod(path, FILE_MODE)


def _append_text(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
    _chmod(path, FILE_MODE)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _stamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _root_refusal(root: Path) -> str | None:
    """Refuse Line A directories. The C6 series name is not one of them."""
    try:
        resolved = root.resolve()
    except OSError:
        resolved = root
    text = str(resolved)
    if "/var/lib/private" in text:
        return "refusing Line A private state directory"
    for part in resolved.parts:
        if part in {"affl-v2-official-ledger", "anchor-official-ledger"}:
            return f"refusing Line A path component {part}"
        if part.startswith("anchor-official-ledger") and part != "anchor-official-ledger-c6":
            return "refusing Line A ledger path"
        if "affl-v2-official-ledger" in part and part != SERIES_DIRNAME:
            return "refusing Line A ledger path"
        if part == "anchor_fake_fill_equity_v2_official.csv":
            return "refusing legacy equity CSV"
    return None


def _json_line(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def _price_text(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if value != value or value in {float("inf"), float("-inf")}:  # NaN
            return None
        return format(value, ".10f").rstrip("0").rstrip(".") or "0"
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"null", "none", "missing"}:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        if number != number or number in {float("inf"), float("-inf")}:
            return None
        return format(number, ".10f").rstrip("0").rstrip(".") or "0"
    return None


def mark_from_ticker_payload(payload: Mapping[str, Any]) -> str | None:
    """Return a public markPrice. Missing or unusable payloads return None."""
    ticker = payload.get("ticker")
    if isinstance(ticker, dict):
        price = _price_text(ticker.get("markPrice"))
        if price is not None:
            return price
    tickers = payload.get("tickers")
    if isinstance(tickers, list):
        for item in tickers:
            if isinstance(item, dict) and item.get("symbol") in {None, SYMBOL}:
                price = _price_text(item.get("markPrice"))
                if price is not None:
                    return price
    return None


def _rate_number(value: Any) -> str | None:
    return _price_text(value)


def rates_from_funding_payload(payload: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    """Split a public payload into real prints and hours that must stay missing.

    A clock hour with no print is not emitted as fundingRate 0. An explicit
    exchange 0 is kept, because that print was returned.
    """
    raw_rates = payload.get("rates")
    if not isinstance(raw_rates, list):
        return [], []
    kept: list[dict[str, str]] = []
    omitted: list[str] = []
    for item in raw_rates:
        if not isinstance(item, dict):
            continue
        stamp = item.get("timestamp")
        if not isinstance(stamp, str) or not stamp.strip():
            continue
        try:
            when = _stamp(_parse_time(stamp))
        except ValueError:
            omitted.append(stamp.strip())
            continue
        funding = _rate_number(item.get("fundingRate"))
        relative = _rate_number(item.get("relativeFundingRate"))
        if funding is None or relative is None:
            omitted.append(when)
            continue
        kept.append(
            {
                "timestamp": when,
                "fundingRate": funding,
                "relativeFundingRate": relative,
            }
        )
    kept.sort(key=lambda row: row["timestamp"])
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in kept:
        if row["timestamp"] in seen:
            continue
        seen.add(row["timestamp"])
        deduped.append(row)
    return deduped, omitted


def gap_hours(rates: Sequence[Mapping[str, str]]) -> list[str]:
    """Hours between the first and last print that the payload did not include."""
    if len(rates) < 2:
        return []
    stamps = [_parse_time(str(row["timestamp"])) for row in rates]
    present = {_stamp(item) for item in stamps}
    missing: list[str] = []
    cursor = stamps[0] + HOUR
    last = stamps[-1]
    while cursor < last:
        label = _stamp(cursor)
        if label not in present:
            missing.append(label)
        cursor += HOUR
    return missing


def _get_json(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            blob = response.read()
    except urllib.error.URLError as exc:
        raise OSError(exc.__class__.__name__) from exc
    payload = json.loads(blob.decode("utf-8"))
    if not isinstance(payload, dict):
        raise OSError("payload_not_object")
    return payload


def fetch_public_mark(timeout: float = 20.0) -> dict[str, Any]:
    payload = _get_json(MARK_URL, timeout)
    price = mark_from_ticker_payload(payload)
    if price is None:
        return {"status": "MARK_MISSING"}
    return {"status": "RECORDED", "markPrice": price}


def fetch_public_funding(timeout: float = 60.0) -> dict[str, Any]:
    payload = _get_json(FUNDING_URL, timeout)
    if payload.get("result") not in {None, "success"}:
        raise OSError("funding_result_not_success")
    return payload


def _last_equity(path: Path) -> dict[str, str] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return None
    last = rows[-1]
    if any(column not in last or last[column] is None for column in EQUITY_V21_COLUMNS):
        return None
    return {column: str(last[column]) for column in EQUITY_V21_COLUMNS}


def _equity_row(path: Path, now: str) -> dict[str, str]:
    previous = _last_equity(path)
    if previous is None:
        return genesis_row(
            timestamp_utc=now,
            net_liquidation_equity=STARTING_EQUITY,
            cash_reserve=STARTING_EQUITY,
            sample_class=SAMPLE_CLASS_NON_SCORING,
            mark_rule_id=MARK_RULE_UNBOUND,
        )
    row = dict(previous)
    row["timestamp_utc"] = now
    row["observation_id"] = "c6-" + now.replace("-", "").replace(":", "")
    row["position"] = previous["position"] if previous["position"] in {"FLAT", "LONG", "SHORT"} else "FLAT"
    row["mark_rule_id"] = MARK_RULE_UNBOUND
    row["sample_class"] = SAMPLE_CLASS_NON_SCORING
    if row["observation_id"] == GENESIS_OBSERVATION_ID:
        raise SeriesRootRefused("refusing to append a second genesis observation")
    return row


def _events_path(series: Path) -> Path:
    return series / "out" / EVENTS_NAME


def _ensure_empty_events(path: Path) -> None:
    """Create an empty events file once. Never append and never truncate."""
    if path.exists():
        return
    _write_bytes(path, b"")


def _null_funding_record(now: str) -> dict[str, Any]:
    """No open leg, so nothing is accrued and the writer amount stays null."""
    result = AccrualResult(
        status="MISSING",
        funding_pnl=None,
        n_expected=0,
        n_present=0,
        missing_timestamps=(),
        used_timestamps=(),
    )
    record = writer_funding_record(result)
    if record.get("funding_pnl") is not None:
        raise RuntimeError("writer funding_pnl must stay null")
    record["open_legs"] = "NO_OPEN_LEGS"
    record["zero_filled"] = False
    record["timestamp_utc"] = now
    record["series_id"] = SERIES_ID
    return record


def _record_mark(path: Path, now: str, fetched: Mapping[str, Any] | None, failed: bool) -> str:
    price = None if failed or fetched is None else _price_text(fetched.get("markPrice"))
    status = "RECORDED" if price is not None and not failed else "MARK_MISSING"
    if status == "MARK_MISSING":
        price = None
    row = {
        "funding_pnl": None,
        "invented": False,
        "markPrice": price,
        "open_legs": "NO_OPEN_LEGS",
        "record_type": "PUBLIC_MARK",
        "source": "public_markPrice",
        "status": status,
        "symbol": SYMBOL,
        "timestamp_utc": now,
        "zero_filled": False,
    }
    _append_text(path, _json_line(row))
    return status


def _record_funding(cache_dir: Path, now: str, payload: Mapping[str, Any] | None, failed: bool) -> bool:
    """Write real prints and gap hours. Return whether any rate was stored as zero by us.

    The return is always False: this function does not invent a zero print.
    """
    cache_path = cache_dir / FUNDING_CACHE_NAME
    fail_path = cache_dir / FUNDING_FAIL_NAME
    if failed or payload is None:
        if not cache_path.exists():
            _write_bytes(
                fail_path,
                _json_line(
                    {
                        "error_class": "fetch_failed",
                        "fetched_at_utc": now,
                        "funding_pnl": None,
                        "policy": "NEVER_ZERO_FILL",
                        "record_type": "FETCH_FAIL",
                        "symbol": SYMBOL,
                        "zero_filled": False,
                    }
                ).encode("utf-8"),
            )
        return False
    rates, omitted = rates_from_funding_payload(payload)
    missing = list(dict.fromkeys([*omitted, *gap_hours(rates)]))
    lines = [
        _json_line(
            {
                "fetched_at_utc": now,
                "funding_pnl": None,
                "n_rates": len(rates),
                "policy": "NEVER_ZERO_FILL",
                "record_type": "FETCH_META",
                "symbol": SYMBOL,
                "zero_filled": False,
            }
        )
    ]
    for rate in rates:
        lines.append(
            _json_line(
                {
                    "fundingRate": rate["fundingRate"],
                    "record_type": "RATE",
                    "relativeFundingRate": rate["relativeFundingRate"],
                    "symbol": SYMBOL,
                    "timestamp": rate["timestamp"],
                }
            )
        )
    if missing:
        lines.append(
            _json_line(
                {
                    "missing_timestamps": missing,
                    "policy": "NEVER_ZERO_FILL",
                    "record_type": "GAP",
                    "symbol": SYMBOL,
                    "zero_filled": False,
                }
            )
        )
    _write_bytes(cache_path, "".join(lines).encode("utf-8"))
    return False


def _record_deploy(path: Path, now: str) -> str:
    if path.exists() and path.stat().st_size > 0:
        return "DEPLOY_PRESENT"
    row = {
        "deploy": DEPLOY,
        "description": (
            "C6 pass-line series recorder. EVALUATION. NON_SCORING. "
            "No C6 event writer. Not a Line A attestation."
        ),
        "funding_pnl": None,
        "live_trading": LIVE_TRADING,
        "not_a_c9_attestation": True,
        "open_legs": "NO_OPEN_LEGS",
        "position_state": "FLAT",
        "record_type": "DEPLOY",
        "recorder": "c6_series_recorder",
        "scoring_status": SAMPLE_CLASS_NON_SCORING,
        "series_id": SERIES_ID,
        "time_utc": now,
        "zero_filled": False,
    }
    _write_bytes(path, _json_line(row).encode("utf-8"))
    return "DEPLOY_RECORDED"


def run_series(
    root: Path | str,
    *,
    now: str | None = None,
    fetch_mark: FetchMark | None = None,
    fetch_funding: FetchFunding | None = None,
) -> dict[str, Any]:
    """Record one C6 series sample under ``root``. Fetches are injectable."""
    destination = Path(root)
    refusal = _root_refusal(destination)
    if refusal is not None:
        raise SeriesRootRefused(refusal)
    stamped = now or utc_now_iso()
    _parse_time(stamped)
    series = destination / SERIES_DIRNAME
    for folder in (series / "out", series / "marks", series / "governance", destination / "funding-cache"):
        _mkdir(folder)
    equity_path = series / "out" / NEW_EQUITY_FILENAME
    equity = record_equity_v21(equity_path, _equity_row(equity_path, stamped), enabled=True)
    _chmod(equity_path, FILE_MODE)
    _ensure_empty_events(_events_path(series))

    mark_failed = False
    fetched_mark: Mapping[str, Any] | None = None
    mark_fn = fetch_mark if fetch_mark is not None else fetch_public_mark
    try:
        fetched_mark = mark_fn()
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, ValueError):
        mark_failed = True
        fetched_mark = None
    mark_status = _record_mark(series / "marks" / MARKS_NAME, stamped, fetched_mark, mark_failed)

    funding_failed = False
    fetched_funding: Mapping[str, Any] | None = None
    funding_fn = fetch_funding if fetch_funding is not None else fetch_public_funding
    cache_dir = destination / "funding-cache"
    prior_cache = cache_dir / FUNDING_CACHE_NAME
    prior_bytes = prior_cache.read_bytes() if prior_cache.is_file() else None
    try:
        fetched_funding = funding_fn()
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, ValueError):
        funding_failed = True
        fetched_funding = None
    if funding_failed and prior_bytes is not None:
        # Leave the last good public cache in place. Do not rewrite it with zeros.
        zero_filled = False
    else:
        zero_filled = _record_funding(cache_dir, stamped, fetched_funding, funding_failed)
    if prior_bytes is not None and funding_failed:
        current = prior_cache.read_bytes() if prior_cache.is_file() else None
        if current != prior_bytes:
            raise RuntimeError("funding fetch failure must not rewrite the cache")

    writer = _null_funding_record(stamped)
    _append_text(series / "out" / WRITER_NAME, _json_line(writer))
    governance = _record_deploy(series / "governance" / GOVERNANCE_NAME, stamped)
    events = _events_path(series)
    return {
        "deploy": DEPLOY,
        "equity_reason": equity["reason"],
        "events": "EMPTY" if events.is_file() and events.stat().st_size == 0 else "NONEMPTY",
        "events_writer": "NO_C6_WRITER",
        "funding_pnl": writer["funding_pnl"],
        "funding_zero_filled": zero_filled,
        "governance": governance,
        "live_trading": LIVE_TRADING,
        "mark_status": mark_status,
        "open_legs": "NO_OPEN_LEGS",
        "position_state": "FLAT",
        "scoring_status": SAMPLE_CLASS_NON_SCORING,
        "series_id": SERIES_ID,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Pass-line data root. Not a Line A directory.")
    parser.add_argument("--now", default=None, help="ISO-8601 UTC timestamp for this sample.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = run_series(args.root, now=args.now)
    except SeriesRootRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    sys.stdout.write(_json_line(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
