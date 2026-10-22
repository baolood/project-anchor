#!/usr/bin/env python3
"""Write a hashed EXTERNAL_PUBLIC_FUNDING_V1 cache from Kraken public GETs.

This helper does not open a ledger, does not send an order, and does not put
API keys on the request. The scorer never calls it. Scoring stays offline
from the file this helper writes.

The default symbol is PF_XBTUSD. Contract size is read from the public
instruments payload and stored on the cache. It is not guessed again later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval_scoring.line_a_pass_line import FORBIDDEN_PATH_MARKERS  # noqa: E402
from eval_scoring.public_funding import (  # noqa: E402
    INSTRUMENTS_URL,
    FundingCacheError,
    build_funding_cache,
    contract_size_from_instruments,
    rates_from_kraken_payload,
    source_url_for,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="PF_XBTUSD", help="Kraken Futures symbol, for example PF_XBTUSD.")
    parser.add_argument("--out", required=True, help="Cache JSON path. A .sha256 sidecar is written beside it.")
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser


def _refuse(path: Path) -> str | None:
    text = str(path.resolve())
    for marker in FORBIDDEN_PATH_MARKERS:
        if marker in text:
            return f"refusing to write under a sealed ledger path containing {marker}"
    return None


def _get_json(url: str, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "anchor-public-funding-cache/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        blob = response.read()
    payload = json.loads(blob.decode("utf-8"), parse_float=Decimal, parse_int=Decimal)
    if not isinstance(payload, dict):
        raise FundingCacheError(f"response from {url} is not an object")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    out = Path(args.out)
    refusal = _refuse(out)
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return 2
    symbol = args.symbol.strip()
    if not symbol:
        print("symbol is empty", file=sys.stderr)
        return 2
    source_url = source_url_for(symbol)
    try:
        rates_payload = _get_json(source_url, args.timeout)
        instruments_payload = _get_json(INSTRUMENTS_URL, args.timeout)
        rates = rates_from_kraken_payload(rates_payload)
        contract_size = contract_size_from_instruments(instruments_payload, symbol)
        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        document = build_funding_cache(
            symbol=symbol,
            source_url=source_url,
            fetched_at=fetched_at,
            contract_size=contract_size,
            rates=rates,
            contract_size_source=INSTRUMENTS_URL,
        )
    except (FundingCacheError, OSError, UnicodeError, json.JSONDecodeError, TimeoutError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    blob = (json.dumps(document, indent=2) + "\n").encode("utf-8")
    out.write_bytes(blob)
    sidecar = out.with_suffix(out.suffix + ".sha256")
    sidecar.write_text(hashlib.sha256(blob).hexdigest() + "\n", encoding="utf-8")
    print(
        f"wrote {out.name} rates={len(document['rates'])} "
        f"rates_sha256={document['rates_sha256']} contract_size={document['contract_size']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
