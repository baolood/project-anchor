#!/usr/bin/env python3
"""Public-only Kraken Futures PF_XBTUSD historical funding fetch → append-ready cache.

DEPLOY=NO. No private API. No keys. Never zero-fills missing prints.
Manual refresh only. The Official writer does not import this module, and
running it does not enable live ``funding_pnl``.
Default endpoint (2026-10-23 verified): 
  GET https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=PF_XBTUSD
Note: unhyphenated historicalfundingrates returns 404 on this host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_URL = (
    "https://futures.kraken.com/derivatives/api/v3/historical-funding-rates"
    "?symbol=PF_XBTUSD"
)
USER_AGENT = "anchor-passline-funding-cache/0.1 (public research; no auth)"
EXPECTED_CADENCE = timedelta(hours=1)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def fetch(url: str, timeout: float = 60.0) -> tuple[bytes, int]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), getattr(resp, "status", 200)


def detect_gaps(rates: list[dict]) -> list[dict]:
    gaps: list[dict] = []
    if not rates:
        return gaps
    ts_list = [parse_ts(r["timestamp"]) for r in rates]
    for i in range(1, len(ts_list)):
        delta = ts_list[i] - ts_list[i - 1]
        if delta == EXPECTED_CADENCE:
            continue
        missing = []
        t = ts_list[i - 1] + EXPECTED_CADENCE
        while t < ts_list[i]:
            missing.append(t.strftime("%Y-%m-%dT%H:%M:%SZ"))
            t += EXPECTED_CADENCE
        gaps.append(
            {
                "after": ts_list[i - 1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "before": ts_list[i].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "delta_hours": delta.total_seconds() / 3600.0,
                "n_missing": len(missing),
                "missing_timestamps": missing,
            }
        )
    return gaps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="funding package root (contains raw/ cache/ fixtures/)",
    )
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print summary only; do not write files",
    )
    args = ap.parse_args()
    out = args.out_dir
    raw_dir = out / "raw"
    cache_dir = out / "cache"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    fetched_at = utc_now_iso()
    try:
        body, status = fetch(args.url)
    except urllib.error.HTTPError as e:
        fail = {
            "record_type": "FETCH_FAIL",
            "symbol": "PF_XBTUSD",
            "endpoint": args.url,
            "fetched_at_utc": fetched_at,
            "http_status": e.code,
            "error": str(e),
            "policy": "leave prior cache; mark gap / MISSING for new window",
        }
        print(json.dumps(fail, indent=2), file=sys.stderr)
        fail_path = cache_dir / "PF_XBTUSD_last_fetch_fail.json"
        if not args.dry_run:
            fail_path.write_text(json.dumps(fail, indent=2) + "\n")
        return 2
    except Exception as e:  # noqa: BLE001 — document any egress/geo failure
        fail = {
            "record_type": "FETCH_FAIL",
            "symbol": "PF_XBTUSD",
            "endpoint": args.url,
            "fetched_at_utc": fetched_at,
            "error": repr(e),
            "policy": "leave prior cache; mark gap / MISSING for new window",
        }
        print(json.dumps(fail, indent=2), file=sys.stderr)
        if not args.dry_run:
            (cache_dir / "PF_XBTUSD_last_fetch_fail.json").write_text(
                json.dumps(fail, indent=2) + "\n"
            )
        return 3

    if status != 200:
        print(f"unexpected status {status}", file=sys.stderr)
        return 2

    data = json.loads(body)
    if data.get("result") != "success":
        print(f"API result={data.get('result')!r}", file=sys.stderr)
        return 2

    rates = data["rates"]
    resp_hash = hashlib.sha256(body).hexdigest()
    gaps = detect_gaps(rates)

    summary = {
        "symbol": "PF_XBTUSD",
        "fetched_at_utc": fetched_at,
        "serverTime": data.get("serverTime"),
        "response_sha256": resp_hash,
        "response_bytes": len(body),
        "n_rates": len(rates),
        "first_timestamp": rates[0]["timestamp"] if rates else None,
        "last_timestamp": rates[-1]["timestamp"] if rates else None,
        "n_gap_spans": len(gaps),
        "n_missing_hours": sum(g["n_missing"] for g in gaps),
        "zero_fill_policy": "FORBIDDEN",
    }
    print(json.dumps(summary, indent=2))

    if args.dry_run:
        return 0

    stamp = fetched_at.replace(":", "")
    raw_path = raw_dir / f"PF_XBTUSD_historical-funding-rates_{stamp}.json"
    raw_path.write_bytes(body)

    # Full rebuild snapshot for this package epoch (append-only across fetches:
    # callers should keep prior raw_*; this JSONL is the current scored cache view.)
    cache_path = cache_dir / "PF_XBTUSD_historicalfundingrates.jsonl"
    lines: list[str] = []
    meta = {
        "record_type": "FETCH_META",
        "symbol": "PF_XBTUSD",
        "endpoint": args.url,
        "auth": "none_public",
        "fetched_at_utc": fetched_at,
        "serverTime": data.get("serverTime"),
        "response_sha256": resp_hash,
        "response_bytes": len(body),
        "raw_path": str(raw_path.relative_to(out)),
        "n_rates_in_response": len(rates),
        "first_timestamp": summary["first_timestamp"],
        "last_timestamp": summary["last_timestamp"],
        "expected_cadence": "1h",
        "zero_fill_policy": "FORBIDDEN",
    }
    lines.append(json.dumps(meta, separators=(",", ":"), sort_keys=True))
    for r in rates:
        lines.append(
            json.dumps(
                {
                    "record_type": "RATE",
                    "symbol": "PF_XBTUSD",
                    "timestamp": r["timestamp"],
                    "fundingRate": r["fundingRate"],
                    "relativeFundingRate": r["relativeFundingRate"],
                    "source_fetch_sha256": resp_hash,
                    "fetched_at_utc": fetched_at,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
    for g in gaps:
        lines.append(
            json.dumps(
                {
                    "record_type": "GAP",
                    "symbol": "PF_XBTUSD",
                    "after": g["after"],
                    "before": g["before"],
                    "delta_hours": g["delta_hours"],
                    "n_missing": g["n_missing"],
                    "missing_timestamps": g["missing_timestamps"],
                    "policy": "NEVER_ZERO_FILL",
                    "source_fetch_sha256": resp_hash,
                    "fetched_at_utc": fetched_at,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
    cache_path.write_text("\n".join(lines) + "\n")

    gap_summary = {
        **summary,
        "expected_cadence": "1h",
        "coverage_start": summary["first_timestamp"],
        "coverage_end": summary["last_timestamp"],
        "gaps": gaps,
        "note": (
            "Missing hours are marked GAP; accrual must set "
            "FUNDING_DATA_STATUS=PARTIAL or MISSING — never coerce to 0."
        ),
    }
    (cache_dir / "PF_XBTUSD_gaps_summary.json").write_text(
        json.dumps(gap_summary, indent=2) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
