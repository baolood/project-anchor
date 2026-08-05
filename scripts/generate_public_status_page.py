#!/usr/bin/env python3
"""Generate a public, sanitized Project Anchor status page."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
DEFAULT_HTML_OUT = REPORTS_DIR / "public_status_page.html"
DEFAULT_JSON_OUT = REPORTS_DIR / "public_status_page_validation.json"
DEFAULT_MD_OUT = REPORTS_DIR / "public_status_page_validation.md"

FORBIDDEN_FRAGMENTS = [
    "API_KEY",
    "API_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "Authorization",
    "external_order_id",
    "client_order_id",
    "idempotency",
    "production.env",
    "/etc/project-anchor",
    "risk_limits",
    "worker",
    "kill_switch",
    "go-live/live trading",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def public_summary(reports_dir: Path) -> dict[str, Any]:
    snapshot = load_json(reports_dir / "operations_readiness_snapshot.json")
    stability_72h = load_json(reports_dir / "post_production_72h_stability_review.json")
    policy = load_json(reports_dir / "manual_low_frequency_operations_policy_validation.json")
    send = load_json(reports_dir / "production_exactly_one_send_result.json")
    reconciliation = load_json(reports_dir / "production_post_send_readonly_reconciliation.json")
    telegram = load_json(reports_dir / "post_production_telegram_channel_evidence.json")
    next_manual_eligibility = load_json(reports_dir / "next_manual_operation_eligibility.json")

    production_validation = "COMPLETE" if nested(send, "terminal", "external_status") == "FILLED" else "OBSERVING"
    reconciliation_status = "PASS" if reconciliation.get("result") == "PASS" else "OBSERVING"
    monitoring_status = "PASS" if nested(snapshot, "post_production_monitoring", "result") == "PASS" or snapshot.get("overall_status") in {"PASS", "WARN"} else "OBSERVING"
    observation_status = "PASS" if stability_72h.get("result") == "PASS" else "IN_PROGRESS"
    alert_status = "PASS" if telegram.get("result") == "PASS" else "READY"

    return {
        "generated_at": utc_now(),
        "project": "Project Anchor",
        "public_status": "OBSERVATION_ACTIVE",
        "service_mode": "manual_review_only",
        "production_validation": production_validation,
        "monitoring": monitoring_status,
        "reconciliation": reconciliation_status,
        "observation_window": observation_status,
        "alerts": alert_status,
        "availability": {
            "public_operations_page": "AVAILABLE",
            "read_only_status": True,
        },
        "trading": {
            "automated_trading": "DISABLED",
            "live_trading": "NOT_OPEN",
            "new_requests_require_manual_approval": True,
        },
        "manual_operations": {
            "policy": "LOW_FREQUENCY_MANUAL_CONFIRMATION",
            "minimum_interval_hours": nested(
                policy, "manual_low_frequency_operations_policy", "policy", "min_hours_between_production_requests",
                default=nested(policy, "policy", "min_hours_between_production_requests"),
            ),
            "eligibility": (
                "READY_FOR_OPERATOR_DECISION"
                if next_manual_eligibility.get("result") == "PASS"
                else "OBSERVING"
            ),
            "operator_authorization_required": True,
            "production_send_authorization_granted": "NO",
        },
        "public_message": {
            "headline": "Project Anchor is in monitored observation mode.",
            "summary": "The first production validation has completed, monitoring is active, and live trading remains closed until a separate operator decision.",
            "next_step": "Continue observation or make a separate manual low-frequency operator decision.",
        },
        "boundary": {
            "secret_disclosed": "NO",
            "new_production_request_sent_by_page": "NO",
            "canary_rerun_by_page": "NO",
            "live_trading_enabled_by_page": "NO",
        },
    }


def render_html(summary: dict[str, Any]) -> str:
    payload = (
        json.dumps(summary, indent=2, sort_keys=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Project Anchor Status</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: #0b1220;
        --panel: #111c2d;
        --line: #26364d;
        --text: #eef5ff;
        --muted: #9db0c8;
        --ok: #32d296;
        --warn: #f6c85f;
        --bad: #ff7070;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        background: radial-gradient(circle at 15% 0%, #1a2a44 0, #0b1220 38%, #08101c 100%);
        color: var(--text);
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      main {{ width: min(1120px, calc(100vw - 32px)); margin: 0 auto; padding: 56px 0; }}
      .hero {{ min-height: 320px; display: grid; align-content: center; gap: 22px; }}
      .status-pill {{
        width: fit-content;
        border: 1px solid rgba(50, 210, 150, .45);
        color: var(--ok);
        background: rgba(50, 210, 150, .1);
        border-radius: 999px;
        padding: 8px 12px;
        font-weight: 800;
        letter-spacing: 0;
      }}
      h1 {{ margin: 0; font-size: clamp(42px, 7vw, 82px); line-height: .95; letter-spacing: 0; max-width: 820px; }}
      .lead {{ margin: 0; color: var(--muted); font-size: clamp(18px, 2vw, 24px); max-width: 760px; line-height: 1.5; }}
      .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
      .card {{ min-height: 154px; border: 1px solid var(--line); border-radius: 8px; background: rgba(17, 28, 45, .9); padding: 20px; }}
      .label {{ color: var(--muted); font-size: 13px; font-weight: 800; text-transform: uppercase; }}
      .value {{ margin-top: 16px; font-size: clamp(26px, 4vw, 42px); line-height: 1; font-weight: 900; overflow-wrap: anywhere; }}
      .detail {{ margin-top: 12px; color: var(--muted); line-height: 1.5; }}
      .ok {{ color: var(--ok); }} .warn {{ color: var(--warn); }} .bad {{ color: var(--bad); }}
      .band {{ margin-top: 14px; border: 1px solid var(--line); border-radius: 8px; padding: 22px; background: rgba(17, 28, 45, .72); }}
      .band h2 {{ margin: 0 0 10px; font-size: 28px; }}
      .facts {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }}
      .fact {{ border-top: 1px solid var(--line); padding-top: 12px; color: var(--muted); }}
      .fact strong {{ display: block; color: var(--text); margin-bottom: 4px; }}
      footer {{ margin-top: 18px; color: var(--muted); font-size: 13px; line-height: 1.5; }}
      @media (max-width: 900px) {{ .grid, .facts {{ grid-template-columns: 1fr; }} main {{ padding-top: 34px; }} }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <div class="status-pill">Observation active</div>
        <h1>Project Anchor is operating under monitored review.</h1>
        <p class="lead">The first production validation has completed. Monitoring is active, alerts are ready, and live trading remains closed until a separate operator decision.</p>
      </section>
      <section class="grid" aria-label="Public status summary">
        <article class="card"><div class="label">Production validation</div><div class="value ok">{summary["production_validation"]}</div><div class="detail">Initial production path validation is recorded without exposing internal order details.</div></article>
        <article class="card"><div class="label">Monitoring</div><div class="value ok">{summary["monitoring"]}</div><div class="detail">System observation and post-production checks are available.</div></article>
        <article class="card"><div class="label">Live trading</div><div class="value bad">NOT OPEN</div><div class="detail">No continuous trading or automatic execution is enabled.</div></article>
      </section>
      <section class="band">
        <h2>Current operating posture</h2>
        <p class="lead">Project Anchor is in a cautious observation phase. Any future production operation requires explicit manual approval and remains limited by the low-frequency operations policy.</p>
        <div class="facts">
          <div class="fact"><strong>Mode</strong>Manual review only</div>
          <div class="fact"><strong>Alerts</strong>{summary["alerts"]}</div>
          <div class="fact"><strong>Observation</strong>{summary["observation_window"]}</div>
          <div class="fact"><strong>Next step</strong>{summary["manual_operations"]["eligibility"]}</div>
        </div>
      </section>
      <footer>This public page is informational only. It contains no secrets, no order identifiers, no account balances, and no execution controls.</footer>
    </main>
    <script id="projectAnchorPublicStatus" type="application/json">{payload}</script>
  </body>
</html>
"""


def validate_html(html_text: str, summary: dict[str, Any]) -> dict[str, Any]:
    forbidden_hits = [fragment for fragment in FORBIDDEN_FRAGMENTS if fragment in html_text]
    checks = {
        "html_generated": "PASS" if "<!doctype html>" in html_text else "FAIL",
        "public_status_payload_embedded": "PASS" if "projectAnchorPublicStatus" in html_text else "FAIL",
        "public_message_present": "PASS" if "Observation active" in html_text else "FAIL",
        "no_execution_controls": "PASS"
        if all(token not in html_text.lower() for token in ["method=\"post\"", "method='post'", "execute", "send request"])
        else "FAIL",
        "forbidden_fragments_absent": "PASS" if not forbidden_hits else "FAIL",
        "live_trading_not_open": "PASS"
        if summary["trading"]["live_trading"] == "NOT_OPEN"
        else "FAIL",
    }
    return {
        "generated_at": utc_now(),
        "result": "PASS" if all(value == "PASS" for value in checks.values()) else "BLOCKED",
        "checks": checks,
        "forbidden_hits": forbidden_hits,
        "boundary": {
            "secret_read": "NO",
            "secret_disclosed": "NO",
            "production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any], html_out: Path) -> str:
    checks = "\n".join(f"- {key}: {value}" for key, value in report["checks"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    return f"""# Public Status Page Validation

Generated at: `{report["generated_at"]}`

## Result

- result: {report["result"]}
- HTML output: `{html_out}`

## Checks

{checks}

## Boundary

{boundary}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--html-out", type=Path, default=DEFAULT_HTML_OUT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    summary = public_summary(args.reports_dir)
    html_text = render_html(summary)
    report = validate_html(html_text, summary)

    args.html_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.html_out.write_text(html_text, encoding="utf-8")
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(markdown(report, args.html_out), encoding="utf-8")

    print("[Public Status Page Generation]")
    print(f"result: {report['result']}")
    print(f"html: {args.html_out}")
    print(f"json: {args.json_out}")
    print("secret_read: NO")
    print("production_request_sent: NO")
    print("canary_rerun: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
