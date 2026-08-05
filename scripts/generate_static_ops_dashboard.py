#!/usr/bin/env python3
"""Generate a sanitized static Project Anchor ops dashboard."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
DEFAULT_HTML_OUT = REPORTS_DIR / "ops_static_dashboard.html"
DEFAULT_JSON_OUT = REPORTS_DIR / "ops_static_dashboard_validation.json"
DEFAULT_MD_OUT = REPORTS_DIR / "ops_static_dashboard_validation.md"

REPORT_NAMES = {
    "production_send": "production_exactly_one_send_result.json",
    "reconciliation": "production_post_send_readonly_reconciliation.json",
    "monitoring": "post_production_monitoring_run.json",
    "alerting": "post_production_alerting_readiness.json",
    "telegram": "post_production_monitoring_telegram_send_result.json",
    "telegram_channel": "post_production_telegram_channel_evidence.json",
    "timer_runtime": "post_production_monitoring_timer_runtime_validation.json",
    "timer_stability": "post_production_monitoring_timer_stability_validation.json",
    "operations": "post_production_operations_decision.json",
    "manual_policy": "manual_low_frequency_operations_policy_validation.json",
    "manual_runbook": "manual_low_frequency_operations_runbook_validation.json",
    "next_manual_eligibility": "next_manual_operation_eligibility.json",
}

FORBIDDEN_FRAGMENTS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "API_SECRET",
    "API_KEY",
    "Authorization",
    '"external_order_id"',
    "client_order_id",
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


def pick_report(reports_dir: Path, name: str) -> dict[str, Any]:
    return load_json(reports_dir / REPORT_NAMES[name])


def sanitize_summary(reports_dir: Path) -> dict[str, Any]:
    send = pick_report(reports_dir, "production_send")
    reconciliation = pick_report(reports_dir, "reconciliation")
    monitoring = pick_report(reports_dir, "monitoring")
    alerting = pick_report(reports_dir, "alerting")
    telegram = pick_report(reports_dir, "telegram")
    telegram_channel = pick_report(reports_dir, "telegram_channel")
    timer_runtime = pick_report(reports_dir, "timer_runtime")
    timer_stability = pick_report(reports_dir, "timer_stability")
    operations = pick_report(reports_dir, "operations")
    manual_policy = pick_report(reports_dir, "manual_policy")
    manual_runbook = pick_report(reports_dir, "manual_runbook")
    next_manual_eligibility = pick_report(reports_dir, "next_manual_eligibility")

    return {
        "generated_at": utc_now(),
        "production_send": {
            "result": send.get("result"),
            "success": send.get("success"),
            "external_status": nested(send, "terminal", "external_status"),
            "external_order_reference_present": nested(send, "terminal", "external_order_id_present"),
            "http_status": nested(send, "http", "status"),
            "symbol": nested(send, "request", "symbol"),
            "side": nested(send, "request", "side"),
            "max_notional": nested(send, "risk_limits", "max_notional"),
        },
        "reconciliation": {
            "result": reconciliation.get("result"),
            "status": reconciliation.get("status"),
            "errors": len(reconciliation.get("errors", []))
            if isinstance(reconciliation.get("errors"), list)
            else reconciliation.get("errors", 0),
        },
        "monitoring": {
            "result": monitoring.get("result"),
            "status": monitoring.get("status"),
            "snapshot_status": monitoring.get("snapshot_status"),
            "generated_at": monitoring.get("generated_at"),
        },
        "alerting": {
            "result": alerting.get("result"),
            "status": alerting.get("status"),
            "failure_code": alerting.get("failure_code"),
        },
        "telegram": {
            "result": telegram_channel.get("result") or telegram.get("result"),
            "status": telegram_channel.get("status") or telegram.get("status"),
            "failure_code": telegram.get("failure_code"),
            "send_attempted": telegram.get("send_attempted"),
            "send_result": telegram_channel.get("delivery_observed") or telegram.get("send_result"),
            "evidence_source": telegram_channel.get("evidence_source"),
        },
        "timer": {
            "runtime_result": timer_runtime.get("result"),
            "timer_active": nested(timer_runtime, "timer", "active_state"),
            "timer_enabled": nested(timer_runtime, "timer", "unit_file_state"),
            "stability_result": timer_stability.get("result"),
            "consecutive_successes": timer_stability.get("latest_consecutive_success_count"),
        },
        "operations": {
            "result": operations.get("result"),
            "decision": operations.get("decision"),
            "next_gate": operations.get("next_gate"),
        },
        "manual_low_frequency": {
            "policy_result": manual_policy.get("result"),
            "policy_status": manual_policy.get("status"),
            "runbook_result": manual_runbook.get("result"),
            "runbook_status": manual_runbook.get("status"),
            "eligibility_result": next_manual_eligibility.get("result"),
            "eligibility_decision": next_manual_eligibility.get("decision"),
            "eligible_for_operator_authorization_decision": nested(
                next_manual_eligibility,
                "eligibility",
                "eligible_for_operator_authorization_decision",
            ),
            "production_send_authorization_granted": nested(
                next_manual_eligibility,
                "eligibility",
                "production_send_authorization_granted",
            ),
            "hours_since_last_production_request": nested(
                next_manual_eligibility,
                "eligibility",
                "hours_since_last_production_request",
            ),
            "observed_production_requests_last_7d": nested(
                next_manual_eligibility,
                "eligibility",
                "observed_production_requests_last_7d",
            ),
            "eligibility_blockers": next_manual_eligibility.get("blockers", []),
            "mode": nested(manual_policy, "policy", "mode"),
            "symbols": nested(manual_policy, "policy", "symbols", default=[]),
            "sides": nested(manual_policy, "policy", "sides", default=[]),
            "max_notional_per_request": nested(
                manual_policy, "policy", "max_notional_per_request"
            ),
            "min_hours_between_requests": nested(
                manual_policy, "policy", "min_hours_between_production_requests"
            ),
            "recommended_max_requests_per_week": nested(
                manual_policy, "policy", "recommended_max_requests_per_week"
            ),
            "operator_authorization_required": nested(
                manual_policy,
                "policy",
                "requires_explicit_operator_authorization_per_request",
            ),
            "before_request_steps": nested(
                manual_runbook, "runbook", "before_request_steps"
            ),
            "after_request_steps": nested(
                manual_runbook, "runbook", "after_request_steps"
            ),
        },
        "boundary": {
            "secret_disclosed": "NO",
            "production_request_sent_by_dashboard": "NO",
            "second_production_request_sent": "NO",
            "telegram_send_triggered_by_dashboard": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
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
    <title>Project Anchor Ops</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: #0f1724;
        --panel: #141f2e;
        --line: #2c3b50;
        --text: #eef4ff;
        --muted: #9cadc4;
        --ok: #36d399;
        --warn: #f6c453;
        --bad: #ff6b6b;
        --link: #8ec7ff;
      }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; min-height: 100vh; background: #0f1724; color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
      main {{ width: min(1180px, calc(100vw - 32px)); margin: 40px auto; }}
      header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 18px; }}
      h1 {{ margin: 0 0 8px; font-size: clamp(34px, 5vw, 54px); line-height: 1; letter-spacing: 0; }}
      p {{ color: var(--muted); line-height: 1.55; }}
      button {{ min-width: 118px; border: 1px solid var(--line); border-radius: 8px; background: #192638; color: var(--text); padding: 11px 14px; font-weight: 700; cursor: pointer; }}
      .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 18px 0; }}
      .panel {{ border: 1px solid var(--line); border-radius: 8px; background: var(--panel); padding: 18px; min-height: 126px; }}
      .label {{ color: var(--muted); font-size: 13px; font-weight: 700; text-transform: uppercase; }}
      .value {{ margin-top: 10px; font-size: 28px; font-weight: 800; overflow-wrap: anywhere; }}
      .small {{ margin-top: 8px; color: var(--muted); font-size: 13px; line-height: 1.45; overflow-wrap: anywhere; }}
      .ok {{ color: var(--ok); }} .warn {{ color: var(--warn); }} .bad {{ color: var(--bad); }}
      .wide {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 0.9fr); gap: 14px; }}
      dl {{ display: grid; grid-template-columns: minmax(150px, 0.42fr) minmax(0, 1fr); gap: 10px 16px; margin: 0; }}
      dt {{ color: var(--muted); }} dd {{ margin: 0; overflow-wrap: anywhere; }}
      a {{ color: var(--link); }}
      pre {{ max-height: 360px; overflow: auto; margin: 0; padding: 14px; border-radius: 8px; background: #0a101b; color: #d6e4f7; font-size: 12px; line-height: 1.45; }}
      footer {{ margin-top: 18px; color: var(--muted); font-size: 13px; }}
      @media (max-width: 980px) {{ header, .wide {{ display: block; }} .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .panel + .panel {{ margin-top: 14px; }} }}
      @media (max-width: 560px) {{ main {{ width: min(100vw - 22px, 1180px); margin: 24px auto; }} .grid, dl {{ grid-template-columns: 1fr; }} }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <div>
          <h1>Project Anchor Ops</h1>
          <p>Read-only operations view. No production send, no canary rerun, no go-live, and no live trading controls exist on this page.</p>
        </div>
        <button type="button" onclick="refreshOps()">Refresh</button>
      </header>
      <section class="grid">
        <article class="panel"><div class="label">Production Send</div><div id="sendResult" class="value warn">Loading</div><div id="sendDetail" class="small">Loading</div></article>
        <article class="panel"><div class="label">Monitoring</div><div id="monitorResult" class="value warn">Loading</div><div id="monitorDetail" class="small">Loading</div></article>
        <article class="panel"><div class="label">Telegram</div><div id="telegramResult" class="value warn">Loading</div><div id="telegramDetail" class="small">Loading</div></article>
        <article class="panel"><div class="label">Go-Live</div><div class="value bad">NO-GO</div><div class="small">Live trading remains NO-GO.</div></article>
      </section>
      <section class="grid">
        <article class="panel"><div class="label">Timer</div><div id="timerResult" class="value warn">Loading</div><div id="timerDetail" class="small">Loading</div></article>
        <article class="panel"><div class="label">Reconciliation</div><div id="reconResult" class="value warn">Loading</div><div id="reconDetail" class="small">Loading</div></article>
        <article class="panel"><div class="label">Manual Ops</div><div id="manualOpsResult" class="value warn">Loading</div><div id="manualOpsDetail" class="small">Loading</div></article>
        <article class="panel"><div class="label">Boundary</div><div class="value ok">SAFE</div><div id="boundaryDetail" class="small">No new request from dashboard.</div></article>
      </section>
      <section class="grid">
        <article class="panel"><div class="label">Next Gate</div><div id="nextGate" class="value warn">Loading</div><div class="small">Operator authorization remains required for any new production request.</div></article>
      </section>
      <section class="wide">
        <article class="panel">
          <h2>Current State</h2>
          <dl>
            <dt>Last refreshed</dt><dd id="refreshedAt">Loading</dd>
            <dt>Backend health</dt><dd id="healthDetail">Loading</dd>
            <dt>Worker heartbeat</dt><dd id="workerHeartbeat">Loading</dd>
            <dt>Runtime mode</dt><dd>Read-only view</dd>
            <dt>Live trading</dt><dd class="bad">NO-GO</dd>
          </dl>
          <p><a href="/healthz">/healthz</a> · <a href="/ops/state">/ops/state</a> · <a href="/ops/worker">/ops/worker</a></p>
        </article>
        <article class="panel"><h2>Sanitized Snapshot</h2><pre id="rawSnapshot">Loading</pre></article>
      </section>
      <footer>This static page uses sanitized report facts embedded at deploy time and GET-only health probes. It does not expose secrets and has no execution controls.</footer>
    </main>
    <script id="projectAnchorReports" type="application/json">{payload}</script>
    <script>
      const reportSummary = JSON.parse(document.getElementById("projectAnchorReports").textContent);
      const text = (value, fallback) => value === undefined || value === null || value === "" ? fallback : String(value);
      const tone = (value) => value === "PASS" || value === "FILLED" || value === "DELIVERED" || value === true ? "ok" : value === "BLOCKED" || value === "SUPPRESSED" ? "warn" : "bad";
      const setValue = (id, value) => {{ const el = document.getElementById(id); el.textContent = value; el.className = "value " + tone(value); }};
      async function getText(path) {{ const response = await fetch(path, {{ cache: "no-store" }}); const body = await response.text(); if (!response.ok) throw new Error(path + " returned " + response.status); return body.trim(); }}
      async function getJson(path) {{ const response = await fetch(path, {{ cache: "no-store" }}); const body = await response.text(); if (!response.ok) throw new Error(path + " returned " + response.status); try {{ return JSON.parse(body); }} catch {{ return {{ raw: body }}; }} }}
      function renderReports() {{
        const send = reportSummary.production_send || {{}};
        const monitoring = reportSummary.monitoring || {{}};
        const telegram = reportSummary.telegram || {{}};
        const timer = reportSummary.timer || {{}};
        const recon = reportSummary.reconciliation || {{}};
        const ops = reportSummary.operations || {{}};
        const manual = reportSummary.manual_low_frequency || {{}};
        setValue("sendResult", text(send.external_status || send.result, "UNKNOWN"));
        document.getElementById("sendDetail").textContent = `${{text(send.symbol, "?")}} ${{text(send.side, "?")}} · notional ${{text(send.max_notional, "?")}} · order reference present ${{text(send.external_order_reference_present, "?")}}`;
        setValue("monitorResult", text(monitoring.result, "UNKNOWN"));
        document.getElementById("monitorDetail").textContent = text(monitoring.snapshot_status || monitoring.status, "Monitoring status unavailable");
        setValue("telegramResult", text(telegram.send_result || telegram.result, "UNKNOWN"));
        document.getElementById("telegramDetail").textContent = `${{text(telegram.status, "?")}} · attempted ${{text(telegram.send_attempted, "NO")}} · reason ${{text(telegram.failure_code, "none")}}`;
        setValue("timerResult", text(timer.stability_result || timer.runtime_result, "UNKNOWN"));
        document.getElementById("timerDetail").textContent = `active ${{text(timer.timer_active, "?")}} · enabled ${{text(timer.timer_enabled, "?")}} · successes ${{text(timer.consecutive_successes, "?")}}`;
        setValue("reconResult", text(recon.result, "UNKNOWN"));
        document.getElementById("reconDetail").textContent = `${{text(recon.status, "reconciled")}} · errors ${{text(recon.errors, 0)}}`;
        const manualStatus = manual.policy_result === "PASS" && manual.runbook_result === "PASS" && manual.eligibility_result === "PASS" ? "PASS" : text(manual.eligibility_result || manual.policy_result || manual.runbook_result, "UNKNOWN");
        setValue("manualOpsResult", manualStatus);
        document.getElementById("manualOpsDetail").textContent = `${{text((manual.symbols || []).join(", "), "?")}} · ${{text((manual.sides || []).join(", "), "?")}} · max ${{text(manual.max_notional_per_request, "?")}} · elapsed ${{text(manual.hours_since_last_production_request, "?")}}h · 7d requests ${{text(manual.observed_production_requests_last_7d, "?")}} · authorization granted ${{text(manual.production_send_authorization_granted, "NO")}}`;
        document.getElementById("nextGate").textContent = text(manual.eligibility_decision || ops.next_gate || ops.decision, "NO-GO");
        document.getElementById("boundaryDetail").textContent = `new request ${{text(reportSummary.boundary.production_request_sent_by_dashboard, "NO")}} · second request ${{text(reportSummary.boundary.second_production_request_sent, "NO")}} · Telegram send by dashboard ${{text(reportSummary.boundary.telegram_send_triggered_by_dashboard, "NO")}}`;
      }}
      async function refreshOps() {{
        renderReports();
        const snapshot = {{ reports: reportSummary }};
        document.getElementById("refreshedAt").textContent = new Date().toISOString();
        try {{ snapshot.health = await getText("/healthz"); document.getElementById("healthDetail").textContent = snapshot.health || "ok"; }}
        catch (error) {{ snapshot.health_error = error.message; document.getElementById("healthDetail").textContent = error.message; }}
        try {{ snapshot.worker = await getJson("/ops/worker"); }} catch (error) {{ snapshot.worker_error = error.message; }}
        const heartbeat = snapshot.worker?.last_heartbeat_at || snapshot.worker?.worker_heartbeat_at || snapshot.worker?.worker?.last_heartbeat_at;
        document.getElementById("workerHeartbeat").textContent = text(heartbeat, snapshot.worker_error || "No heartbeat field found");
        document.getElementById("rawSnapshot").textContent = JSON.stringify(snapshot, null, 2);
      }}
      refreshOps();
    </script>
  </body>
</html>
"""


def validate_html(html_text: str, summary: dict[str, Any]) -> dict[str, Any]:
    forbidden_hits = [token for token in FORBIDDEN_FRAGMENTS if token in html_text]
    checks = {
        "html_generated": "PASS" if "<!doctype html>" in html_text else "FAIL",
        "sanitized_payload_embedded": "PASS" if "projectAnchorReports" in html_text else "FAIL",
        "telegram_status_present": "PASS" if "Telegram" in html_text else "FAIL",
        "no_execution_controls": "PASS"
        if all(token not in html_text for token in ["execute_exactly_one_production_request.py", "method=\"post\"", "method='post'"])
        else "FAIL",
        "forbidden_fragments_absent": "PASS" if not forbidden_hits else "FAIL",
        "go_live_no_go": "PASS" if summary["boundary"]["go_live"] == "NO-GO" else "FAIL",
        "live_trading_no_go": "PASS" if summary["boundary"]["live_trading"] == "NO-GO" else "FAIL",
    }
    result = "PASS" if all(value == "PASS" for value in checks.values()) else "BLOCKED"
    return {
        "generated_at": utc_now(),
        "result": result,
        "checks": checks,
        "forbidden_hits": forbidden_hits,
        "boundary": {
            "secret_read": "NO",
            "secret_disclosed": "NO",
            "telegram_send_triggered": "NO",
            "production_request_sent": "NO",
            "second_production_request_sent": "NO",
            "canary_rerun": "NO",
            "go_live": "NO-GO",
            "live_trading": "NO-GO",
        },
    }


def markdown(report: dict[str, Any], html_out: Path) -> str:
    checks = "\n".join(f"- {key}: {value}" for key, value in report["checks"].items())
    boundary = "\n".join(f"- {key}: {value}" for key, value in report["boundary"].items())
    return f"""# Static Ops Dashboard Validation

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

    summary = sanitize_summary(args.reports_dir)
    html_text = render_html(summary)
    report = validate_html(html_text, summary)

    args.html_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.html_out.write_text(html_text, encoding="utf-8")
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(markdown(report, args.html_out), encoding="utf-8")

    print("[Static Ops Dashboard Generation]")
    print(f"result: {report['result']}")
    print(f"html: {args.html_out}")
    print(f"json: {args.json_out}")
    print("secret_read: NO")
    print("telegram_send_triggered: NO")
    print("production_request_sent: NO")
    print("go_live: NO-GO")
    print("live_trading: NO-GO")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
