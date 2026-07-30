#!/usr/bin/env python3
"""Read-only Binance reconciliation for the exactly-one production send.

This script may read production credentials only when explicitly authorized with
--execute-readonly. It performs signed GET requests only, redacts secrets, and
never sends an order, retries an order, enables go-live, or enables live trading.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
WINDOW_PLAN = REPORTS_DIR / "production_request_send_window_plan.json"
SEND_RESULT = REPORTS_DIR / "production_exactly_one_send_result.json"
RISK_LIMITS = ROOT / "config" / "production_risk_limits.template.json"
CONTRACT_PATH = ROOT / "config" / "production_credential_contract.json"
JSON_OUT = REPORTS_DIR / "production_post_send_readonly_reconciliation.json"
MD_OUT = REPORTS_DIR / "production_post_send_readonly_reconciliation.md"
DEFAULT_RECV_WINDOW_MS = 5000
DEFAULT_HTTP_TIMEOUT_SECONDS = 10.0

sys.path.insert(0, str(ROOT / "anchor-backend"))

from app.executors.production_credentials import (  # noqa: E402
    load_production_credentials,
    redacted_credential_shape,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def fmt(ts: datetime) -> str:
    return ts.isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - reconciliation should report failure cleanly.
        return {}, f"{path.relative_to(ROOT)}:UNREADABLE:{type(exc).__name__}"
    if not isinstance(data, dict):
        return {}, f"{path.relative_to(ROOT)}:NOT_OBJECT"
    return data, None


def sign_query(api_secret: str, query: str) -> str:
    return hmac.new(api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()


def signed_get(
    credentials: dict[str, str],
    path: str,
    params: dict[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
    timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any] | list[Any] | None, dict[str, Any] | None]:
    base_url = str(credentials.get("base_url") or "").rstrip("/")
    api_key = str(credentials.get("api_key") or "")
    api_secret = str(credentials.get("api_secret") or "")
    if base_url != "https://api.binance.com":
        return None, {"code": "PRODUCTION_BASE_URL_NOT_ALLOWLISTED"}
    if not api_key or not api_secret:
        return None, {"code": "PRODUCTION_CREDENTIALS_MISSING"}

    query = urllib.parse.urlencode(params, doseq=True)
    signed_query = f"{query}&signature={sign_query(api_secret, query)}"
    request = urllib.request.Request(
        f"{base_url}{path}?{signed_query}",
        method="GET",
        headers={"X-MBX-APIKEY": api_key},
    )
    open_call = opener or urllib.request.urlopen
    try:
        with open_call(request, timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", 200))
            body = json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        body: dict[str, Any] = {}
        try:
            decoded = json.loads(exc.read().decode("utf-8") or "{}")
            body = decoded if isinstance(decoded, dict) else {}
        except Exception:
            body = {}
        finally:
            exc.close()
        return None, {
            "code": "PRODUCTION_READONLY_HTTP_REJECTED",
            "http_status": int(exc.code),
            "exchange_error_code": body.get("code"),
            "exchange_error_message_present": body.get("msg") is not None,
        }
    except Exception as exc:  # noqa: BLE001 - transport should fail closed.
        return None, {
            "code": "PRODUCTION_READONLY_TRANSPORT_FAILED",
            "transport_error_type": type(exc).__name__,
        }
    if status < 200 or status >= 300:
        return None, {"code": "PRODUCTION_READONLY_HTTP_UNEXPECTED_STATUS", "http_status": status}
    return body, None


def as_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def redacted_order(order: dict[str, Any]) -> dict[str, Any]:
    quote = as_decimal(order.get("cummulativeQuoteQty"))
    executed = as_decimal(order.get("executedQty"))
    return {
        "symbol": order.get("symbol"),
        "side": order.get("side"),
        "type": order.get("type"),
        "status": order.get("status"),
        "order_id_present": order.get("orderId") is not None,
        "client_order_id_present": order.get("clientOrderId") is not None,
        "time_present": order.get("time") is not None,
        "update_time_present": order.get("updateTime") is not None,
        "cummulative_quote_qty": str(quote) if quote is not None else None,
        "executed_qty_present": executed is not None and executed > 0,
    }


def order_matches_authorized_fill(
    order: dict[str, Any],
    *,
    symbol: str,
    side: str,
    max_notional: Decimal | None,
) -> bool:
    quote = as_decimal(order.get("cummulative_quote_qty"))
    return (
        order["symbol"] == symbol
        and order["side"] == side
        and order["type"] == "MARKET"
        and order["status"] == "FILLED"
        and order["order_id_present"] is True
        and order["executed_qty_present"] is True
        and quote is not None
        and quote > 0
        and max_notional is not None
        and quote <= max_notional
    )


def asset_present(account: dict[str, Any], asset: str) -> bool:
    balances = account.get("balances")
    if not isinstance(balances, list):
        return False
    for item in balances:
        if not isinstance(item, dict) or item.get("asset") != asset:
            continue
        free = as_decimal(item.get("free"))
        locked = as_decimal(item.get("locked"))
        return (free is not None and free >= 0) and (locked is not None and locked >= 0)
    return False


def build_report(
    *,
    execute_readonly: bool,
    credential_path: Path,
    now: datetime | None = None,
    opener: Callable[..., Any] | None = None,
) -> tuple[dict[str, Any], int]:
    current = now or utc_now()
    now_ms = int(current.timestamp() * 1000)
    window, window_error = read_json(WINDOW_PLAN)
    send, send_error = read_json(SEND_RESULT)
    risk_limits, risk_error = read_json(RISK_LIMITS)
    errors = [err for err in [window_error, send_error, risk_error] if err]

    planned_window = window.get("planned_window", {}) if isinstance(window.get("planned_window"), dict) else {}
    not_before = parse_utc(planned_window.get("not_before"))
    expires_at = parse_utc(planned_window.get("expires_at"))
    start_ms = int(not_before.timestamp() * 1000) if not_before else None
    end_ms = int(expires_at.timestamp() * 1000) if expires_at else None

    request = send.get("request", {}) if isinstance(send.get("request"), dict) else {}
    terminal = send.get("terminal", {}) if isinstance(send.get("terminal"), dict) else {}
    symbol = str(request.get("symbol") or risk_limits.get("AUTHORIZED_PRODUCTION_SYMBOLS") or "BTCUSDT")
    side = str(request.get("side") or "BUY")
    max_notional = as_decimal(request.get("max_notional") or risk_limits.get("AUTHORIZED_MAX_NOTIONAL"))

    credentials = None
    credential_report: dict[str, Any] = {"ok": False, "code": "PRODUCTION_CREDENTIAL_READ_NOT_EXECUTED"}
    orders_payload: Any = None
    account_payload: Any = None
    order_error = None
    account_error = None
    readonly_queries_attempted = "NO"

    if not execute_readonly:
        errors.append("PRODUCTION_POST_SEND_READONLY_RECONCILIATION_NOT_AUTHORIZED")
    elif start_ms is None or end_ms is None:
        errors.append("PRODUCTION_SEND_WINDOW_UNRESOLVED")
    else:
        credentials, credential_report = load_production_credentials(credential_path, allow_read=True)
        if credentials is None:
            errors.append(str(credential_report.get("code") or "PRODUCTION_CREDENTIALS_MISSING"))
        else:
            readonly_queries_attempted = "YES"
            common = {"timestamp": now_ms, "recvWindow": DEFAULT_RECV_WINDOW_MS}
            orders_payload, order_error = signed_get(
                credentials,
                "/api/v3/allOrders",
                {
                    "symbol": symbol,
                    "startTime": start_ms,
                    "endTime": end_ms,
                    "limit": 20,
                    **common,
                },
                opener=opener,
            )
            account_payload, account_error = signed_get(
                credentials,
                "/api/v3/account",
                common,
                opener=opener,
            )
            if order_error:
                errors.append(str(order_error.get("code") or "ORDER_QUERY_FAILED"))
            if account_error:
                errors.append(str(account_error.get("code") or "ACCOUNT_QUERY_FAILED"))

    orders = orders_payload if isinstance(orders_payload, list) else []
    redacted_orders = [redacted_order(item) for item in orders if isinstance(item, dict)]
    matching_orders = [
        item
        for item in redacted_orders
        if order_matches_authorized_fill(item, symbol=symbol, side=side, max_notional=max_notional)
    ]
    duplicate_orders = [item for item in redacted_orders if item["symbol"] == symbol]

    account = account_payload if isinstance(account_payload, dict) else {}
    checks: list[dict[str, str]] = []

    def check(name: str, passed: bool, evidence: str) -> None:
        checks.append({"name": name, "result": "PASS" if passed else "FAIL", "evidence": evidence})

    check("send_report_pass", send.get("result") == "PASS" and send.get("success") is True, "stored production send report is PASS")
    check("stored_terminal_filled", terminal.get("external_status") == "FILLED", "stored terminal external status is FILLED")
    check("readonly_queries_attempted", readonly_queries_attempted == "YES", "read-only order and account queries were attempted")
    check("order_query_ok", order_error is None and isinstance(orders_payload, list), "allOrders read-only query returned a list")
    check("account_query_ok", account_error is None and isinstance(account_payload, dict), "account read-only query returned an object")
    check("matching_filled_order_count_one", len(matching_orders) == 1, "exactly one matching FILLED BTCUSDT BUY market order found")
    check("no_second_symbol_order_in_window", len(duplicate_orders) == 1, "exactly one BTCUSDT order found in the authorized window")
    check("usdt_balance_visible", asset_present(account, "USDT"), "USDT balance row is visible without recording amount")
    check("btc_balance_visible", asset_present(account, "BTC"), "BTC balance row is visible without recording amount")

    failed = [item for item in checks if item["result"] != "PASS"]
    result = "PASS" if not errors and not failed else "BLOCKED"
    report = {
        "generated_at": fmt(current),
        "result": result,
        "errors": errors,
        "checks": checks,
        "inputs": {
            "send_result": str(SEND_RESULT.relative_to(ROOT)),
            "window_plan": str(WINDOW_PLAN.relative_to(ROOT)),
            "risk_limits": str(RISK_LIMITS.relative_to(ROOT)),
            "credential_path": str(credential_path),
        },
        "query_scope": {
            "symbol": symbol,
            "side": side,
            "max_notional": str(max_notional) if max_notional is not None else None,
            "window_start_present": start_ms is not None,
            "window_end_present": end_ms is not None,
            "order_query_endpoint": "/api/v3/allOrders",
            "account_query_endpoint": "/api/v3/account",
        },
        "order_reconciliation": {
            "orders_returned": len(redacted_orders),
            "matching_filled_order_count": len(matching_orders),
            "symbol_order_count_in_window": len(duplicate_orders),
            "matching_order": matching_orders[0] if len(matching_orders) == 1 else None,
            "redacted_symbol_orders": duplicate_orders,
        },
        "account_reconciliation": {
            "account_payload_visible": isinstance(account_payload, dict),
            "usdt_balance_row_present": asset_present(account, "USDT"),
            "btc_balance_row_present": asset_present(account, "BTC"),
            "balance_amounts_recorded": "NO",
        },
        "credential_shape": redacted_credential_shape(credentials, credential_report),
        "boundary": {
            "credential_file_read": "YES" if credentials is not None else "NO",
            "secret_value_disclosed": "NO",
            "secret_length_disclosed": "NO",
            "secret_prefix_suffix_disclosed": "NO",
            "secret_hash_disclosed": "NO",
            "authorization_header_value_disclosed": "NO",
            "read_only_order_query_attempted": "YES" if orders_payload is not None or order_error else "NO",
            "read_only_account_query_attempted": "YES" if account_payload is not None or account_error else "NO",
            "production_order_sent": "NO",
            "second_production_request_sent": "NO",
            "retry_performed": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
        "next_gate": "POST_PRODUCTION_SEND_OPERATIONS_DECISION",
    }
    return report, 0 if result == "PASS" else 1


def markdown(report: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- {item['name']}: {item['result']} ({item['evidence']})" for item in report["checks"]
    )
    errors = "\n".join(f"- {item}" for item in report["errors"]) or "- none"
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    order = report["order_reconciliation"]
    account = report["account_reconciliation"]
    return f"""# Production Post-Send Read-Only Reconciliation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- next gate: {report["next_gate"]}

## Order Reconciliation

- orders returned: {order["orders_returned"]}
- matching FILLED order count: {order["matching_filled_order_count"]}
- BTCUSDT order count in window: {order["symbol_order_count_in_window"]}
- matching order present: {str(order["matching_order"] is not None).lower()}

## Account Reconciliation

- account payload visible: {str(account["account_payload_visible"]).lower()}
- USDT balance row present: {str(account["usdt_balance_row_present"]).lower()}
- BTC balance row present: {str(account["btc_balance_row_present"]).lower()}
- balance amounts recorded: {account["balance_amounts_recorded"]}

## Checks

{checks}

## Errors

{errors}

## Boundary

{boundary}
"""


def parse_args() -> argparse.Namespace:
    contract, _ = read_json(CONTRACT_PATH)
    parser = argparse.ArgumentParser(description="Read-only post-send production reconciliation.")
    parser.add_argument(
        "--credential-file",
        default=str(contract.get("canonical_path") or "/etc/project-anchor/production.env"),
    )
    parser.add_argument(
        "--execute-readonly",
        action="store_true",
        help="Execute signed read-only Binance queries. Without this flag the script fails closed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report, exit_code = build_report(
        execute_readonly=args.execute_readonly,
        credential_path=Path(args.credential_file),
    )
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(report), encoding="utf-8")
    print("[Production Post-Send Read-Only Reconciliation]")
    print(f"report JSON: {JSON_OUT.relative_to(ROOT)}")
    print(f"report Markdown: {MD_OUT.relative_to(ROOT)}")
    print(f"generated_at: {report['generated_at']}")
    print(f"result: {report['result']}")
    print(f"matching_filled_order_count: {report['order_reconciliation']['matching_filled_order_count']}")
    print(f"symbol_order_count_in_window: {report['order_reconciliation']['symbol_order_count_in_window']}")
    print(f"usdt_balance_row_present: {report['account_reconciliation']['usdt_balance_row_present']}")
    print(f"btc_balance_row_present: {report['account_reconciliation']['btc_balance_row_present']}")
    print("production_order_sent: NO")
    print("second_production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
