"""Host fault alarm: detection, dedupe, and webhook payload. No network."""

from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from app.mcp.inventory import (
    CLASS_AUXILIARY,
    RECOMMENDED_SERVICE_UNITS,
    RECOMMENDED_TIMER_UNITS,
    classify_unit,
)
from ops.fault_alarm.probe import (
    DECISION_NAME,
    GO_LIVE_BLOCKER,
    LIVE_TRADING_BLOCKER,
    PAYLOAD_KEYS,
    READINESS_NAME,
    REMIND_S,
    Action,
    Sources,
    SystemdUnavailable,
    WebhookConfig,
    _selected_env,
    backend_fault,
    build_payload,
    collect_faults,
    deliver_payload,
    expected_long_running,
    expected_oneshots,
    expected_timers,
    finalize_payload,
    kill_switch_fault,
    latest_completed_4h_close,
    load_state,
    long_running_fault,
    main,
    mf4_fault,
    oneshot_fault,
    plan_notifications,
    resolve_repo,
    run_probe,
    save_state,
    timer_fault,
    trade_guard_faults,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 24, 8, 30, tzinfo=timezone.utc)
CLOSE = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)


def _usec(when: datetime) -> str:
    return str(int(when.timestamp() * 1_000_000))


def _simple(name: str) -> dict[str, str]:
    return {
        "id": name,
        "load_state": "loaded",
        "active_state": "active",
        "sub_state": "running",
        "result": "success",
        "type": "simple",
    }


def _oneshot(name: str) -> dict[str, str]:
    return {
        "id": name,
        "load_state": "loaded",
        "active_state": "inactive",
        "sub_state": "dead",
        "result": "success",
        "type": "oneshot",
    }


def _timer(name: str, now: datetime = NOW) -> dict[str, str]:
    return {
        "id": name,
        "load_state": "loaded",
        "active_state": "active",
        "sub_state": "waiting",
        "result": "success",
        "type": "",
        "last_trigger_usec": _usec(now - timedelta(seconds=60)),
        "next_elapse_usec": _usec(now + timedelta(seconds=600)),
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _guards(repo: Path, *, go_live: str = "NO-GO", live: str = "NO-GO", blockers: list[str] | None = None) -> None:
    _write_json(
        repo / "reports" / READINESS_NAME,
        {
            "blockers": blockers
            if blockers is not None
            else [GO_LIVE_BLOCKER, LIVE_TRADING_BLOCKER, "production signing not authorized"],
            "canary": "SECRET_CANARY_should_not_leak",
        },
    )
    _write_json(
        repo / "reports" / DECISION_NAME,
        {"boundary": {"go_live": go_live, "live_trading": live}, "canary": "SECRET_CANARY_should_not_leak"},
    )


def _decision(directory: Path, stamp: str, kind: str = "SIGNAL_4H") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    row = {"event_type": kind, "bar4h_close_utc": stamp, "signal_available_at": stamp}
    (directory / "mf4_forward_events.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")


def _show_for(now: datetime = NOW):
    long_running = set(expected_long_running())

    def show(name: str) -> dict[str, str]:
        if name.endswith(".timer"):
            return _timer(name, now)
        if name in long_running:
            return _simple(name)
        return _oneshot(name)

    return show


def _sources(root: Path, *, now: datetime = NOW, show=None, kill=None, backend=None) -> Sources:
    repo = root / "repo"
    mf4 = root / "mf4"
    _guards(repo)
    _decision(mf4, latest_completed_4h_close(now).strftime("%Y-%m-%dT%H:%M:%SZ"))
    return Sources(
        show=show or _show_for(now),
        now=now,
        mf4_dir=mf4,
        repo=repo,
        kill_switch=kill or (lambda: {"state": "CLOSED", "enabled": False, "source": "redis"}),
        backend=backend or (lambda: {"ok": True, "reason": "health_ok"}),
    )


def _override(base, name: str, props: dict[str, str]):
    def show(unit: str) -> dict[str, str]:
        if unit == name:
            return props
        return base(unit)

    return show


class InventoryWatchListTests(unittest.TestCase):
    def test_watch_list_reuses_inventory_and_covers_the_named_units(self) -> None:
        self.assertTrue(set(RECOMMENDED_SERVICE_UNITS).issubset(expected_long_running()))
        self.assertTrue(set(RECOMMENDED_TIMER_UNITS).issubset(expected_timers()))
        for name in ("nginx.service", "anchor-mf4-watcher.service", "anchor-control-mcp.service"):
            self.assertIn(name, expected_long_running())
        for name in (
            "anchor-official-ledger.service",
            "anchor-official-ledger-c6.service",
            "anchor-ledger-readonly-mirror.service",
        ):
            self.assertIn(name, expected_oneshots())
        self.assertIn("anchor-official-ledger-c6.timer", expected_timers())
        self.assertIn("anchor-official-ledger.timer", expected_timers())
        self.assertIn("anchor-ledger-readonly-mirror.timer", expected_timers())
        self.assertNotIn("anchor-fault-alarm.service", expected_long_running())
        self.assertNotIn("anchor-fault-alarm.timer", expected_timers())
        self.assertNotIn("project-anchor-jev-forward-shadow-v2.service", expected_long_running())

    def test_fault_alarm_units_do_not_gate_pass(self) -> None:
        for name in ("anchor-fault-alarm.service", "anchor-fault-alarm.timer", "extra-fault-alarm.service"):
            classified = classify_unit(name)
            self.assertEqual(classified["unit_class"], CLASS_AUXILIARY, name)
            self.assertIs(classified["gates_overall_pass"], False, name)

    def test_guard_strings_match_the_post_production_snapshot(self) -> None:
        text = (ROOT / "scripts" / "generate_post_production_monitoring_snapshot.py").read_text(encoding="utf-8")
        self.assertIn(f'"{GO_LIVE_BLOCKER}"', text)
        self.assertIn(f'"{LIVE_TRADING_BLOCKER}"', text)
        self.assertIn('boundary_value(decision, "go_live") == "NO-GO"', text)
        self.assertIn('boundary_value(decision, "live_trading") == "NO-GO"', text)


class DetectionTests(unittest.TestCase):
    def test_latest_4h_close_is_the_utc_grid(self) -> None:
        self.assertEqual(latest_completed_4h_close(NOW), CLOSE)
        self.assertEqual(latest_completed_4h_close(CLOSE), CLOSE)

    def test_healthy_host_has_no_faults(self) -> None:
        with self._tmp() as root:
            faults = collect_faults(_sources(root))
        self.assertEqual(faults, [])

    def test_inactive_long_running_unit_is_a_fault(self) -> None:
        with self._tmp() as root:
            base = _show_for()
            props = _simple("nginx.service")
            props["active_state"] = "inactive"
            props["sub_state"] = "dead"
            props["inactive_enter_usec"] = _usec(CLOSE)
            sources = _sources(root, show=_override(base, "nginx.service", props))
            faults = collect_faults(sources)
        self.assertEqual([item.check for item in faults], ["service:nginx.service"])
        self.assertEqual(faults[0].since, "2026-10-24T08:00:00Z")
        self.assertIn("not active (inactive/dead)", faults[0].detail)
        self.assertEqual(faults[0].severity, "critical")

    def test_oneshot_success_is_healthy_and_failure_is_not(self) -> None:
        self.assertIsNone(oneshot_fault("anchor-official-ledger.service", _oneshot("anchor-official-ledger.service"), NOW))
        failed = _oneshot("anchor-official-ledger.service")
        failed["result"] = "failed"
        fault = oneshot_fault("anchor-official-ledger.service", failed, NOW)
        self.assertIsNotNone(fault)
        assert fault is not None
        self.assertIn("not success", fault.detail)
        running = _oneshot("anchor-official-ledger-c6.service")
        running["active_state"] = "activating"
        self.assertIsNone(oneshot_fault("anchor-official-ledger-c6.service", running, NOW))

    def test_missing_unit_is_a_fault(self) -> None:
        fault = long_running_fault("anchor-mf4-watcher.service", {"load_state": "not-found", "id": "anchor-mf4-watcher.service"}, NOW)
        self.assertIsNotNone(fault)
        assert fault is not None
        self.assertIn("not loaded (not-found)", fault.detail)

    def test_timer_missed_elapse_and_inactive_are_faults(self) -> None:
        missed = _timer("anchor-official-ledger.timer")
        missed["last_trigger_usec"] = _usec(NOW - timedelta(hours=2))
        missed["next_elapse_usec"] = _usec(NOW - timedelta(minutes=20))
        fault = timer_fault("anchor-official-ledger.timer", missed, NOW)
        self.assertIsNotNone(fault)
        assert fault is not None
        self.assertIn("missed its elapse", fault.detail)
        self.assertEqual(fault.check, "timer:anchor-official-ledger.timer")

        inactive = _timer("anchor-ledger-readonly-mirror.timer")
        inactive["active_state"] = "inactive"
        inactive["sub_state"] = "dead"
        down = timer_fault("anchor-ledger-readonly-mirror.timer", inactive, NOW)
        self.assertIsNotNone(down)
        assert down is not None
        self.assertIn("not active", down.detail)

    def test_armed_timer_that_has_not_fired_yet_is_healthy(self) -> None:
        waiting = _timer("anchor-official-ledger-c6.timer")
        waiting["last_trigger_usec"] = "0"
        waiting["next_elapse_usec"] = _usec(NOW + timedelta(minutes=5))
        self.assertIsNone(timer_fault("anchor-official-ledger-c6.timer", waiting, NOW))
        never = dict(waiting)
        never["next_elapse_usec"] = "0"
        fault = timer_fault("anchor-official-ledger-c6.timer", never, NOW)
        self.assertIsNotNone(fault)
        assert fault is not None
        self.assertIn("has not fired", fault.detail)

    def test_failed_timer_companion_is_a_fault(self) -> None:
        with self._tmp() as root:
            base = _show_for()
            props = _oneshot("project-anchor-post-production-monitoring.service")
            props["result"] = "failed"
            sources = _sources(root, show=_override(base, "project-anchor-post-production-monitoring.service", props))
            faults = collect_faults(sources)
        self.assertEqual([item.check for item in faults], ["service:project-anchor-post-production-monitoring.service"])

    def test_mf4_decision_grace_and_staleness(self) -> None:
        stamp = "2026-10-24T08:00:00Z"
        with self._tmp() as root:
            mf4 = root / "mf4"
            mf4.mkdir()
            during = CLOSE + timedelta(minutes=19, seconds=59)
            self.assertIsNone(mf4_fault(mf4, during))
            at_grace = CLOSE + timedelta(minutes=20)
            stale = mf4_fault(mf4, at_grace)
            self.assertIsNotNone(stale)
            assert stale is not None
            self.assertEqual(stale.check, "mf4:decision")
            self.assertIn(stamp, stale.detail)
            _decision(mf4, stamp, "SIGNAL_4H_SKIPPED")
            self.assertIsNone(mf4_fault(mf4, NOW))
            (mf4 / "mf4_forward_events.jsonl").write_text(
                json.dumps({"event_type": "SIGNAL_4H", "bar4h_close_utc": "2026-10-24T04:00:00Z"}) + "\n",
                encoding="utf-8",
            )
            wrong = mf4_fault(mf4, NOW)
            self.assertIsNotNone(wrong)
            assert wrong is not None
            self.assertIn(stamp, wrong.detail)

    def test_mf4_symlink_and_sealed_path_are_unreadable(self) -> None:
        with self._tmp() as root:
            mf4 = root / "mf4"
            mf4.mkdir()
            target = root / "events.jsonl"
            target.write_text("{}\n", encoding="utf-8")
            (mf4 / "mf4_forward_events.jsonl").symlink_to(target)
            fault = mf4_fault(mf4, NOW)
            self.assertIsNotNone(fault)
            assert fault is not None
            self.assertEqual(fault.detail, "MF4 decision log is unreadable")
            sealed = root / "anchor-official-ledger-sample"
            sealed.mkdir()
            sealed_fault = mf4_fault(sealed, NOW)
            self.assertIsNotNone(sealed_fault)
            assert sealed_fault is not None
            self.assertEqual(sealed_fault.detail, "MF4 decision log is unreadable")
            self.assertEqual(list(sealed.iterdir()), [])

    def test_kill_switch_open_and_unreadable(self) -> None:
        self.assertIsNone(kill_switch_fault({"state": "CLOSED", "enabled": False, "source": "redis"}, NOW))
        opened = kill_switch_fault({"state": "OPEN", "enabled": True, "source": "env"}, NOW)
        self.assertIsNotNone(opened)
        assert opened is not None
        self.assertEqual(opened.detail, "kill switch is OPEN")
        unread = kill_switch_fault({"state": "UNKNOWN", "enabled": None, "source": "unavailable"}, NOW)
        self.assertIsNotNone(unread)
        assert unread is not None
        self.assertEqual(unread.detail, "kill switch is unreadable")

    def test_trade_guards_port_the_two_snapshot_checks(self) -> None:
        with self._tmp() as root:
            repo = root / "repo"
            _guards(repo)
            self.assertEqual(trade_guard_faults(repo, NOW), [])
            _guards(repo, go_live="YES")
            flags = {item.check: item.detail for item in trade_guard_faults(repo, NOW)}
            self.assertEqual(flags, {"guard:go_live": "go-live is not blocked"})
            _guards(repo, blockers=[LIVE_TRADING_BLOCKER])
            flags = {item.check: item.detail for item in trade_guard_faults(repo, NOW)}
            self.assertEqual(flags, {"guard:go_live": "go-live is not blocked"})
            _guards(repo, live="YES")
            flags = {item.check: item.detail for item in trade_guard_faults(repo, NOW)}
            self.assertEqual(set(flags), {"guard:live_trading"})
            empty = root / "empty"
            empty.mkdir()
            unread = {item.check: item.detail for item in trade_guard_faults(empty, NOW)}
            self.assertEqual(
                unread,
                {
                    "guard:go_live": "go-live evidence is unreadable",
                    "guard:live_trading": "live trading evidence is unreadable",
                },
            )

    def test_backend_health(self) -> None:
        self.assertIsNone(backend_fault({"ok": True, "reason": "health_ok"}, NOW))
        fault = backend_fault({"ok": False, "reason": "unreachable"}, NOW)
        self.assertIsNotNone(fault)
        assert fault is not None
        self.assertEqual(fault.check, "backend:127.0.0.1:8000")
        self.assertIn("unreachable", fault.detail)
        self.assertNotIn("http://", fault.detail)

    def test_missing_systemctl_is_one_fault(self) -> None:
        def show(_name: str) -> dict[str, str]:
            raise SystemdUnavailable("systemctl_missing")

        with self._tmp() as root:
            faults = collect_faults(_sources(root, show=show))
        self.assertEqual([item.check for item in faults], ["systemd:show"])

    def _tmp(self):
        return _TempDir()


class _TempDir:
    def __enter__(self) -> Path:
        import tempfile

        self._cm = tempfile.TemporaryDirectory()
        return Path(self._cm.__enter__())

    def __exit__(self, exc_type, exc, tb) -> None:
        self._cm.__exit__(exc_type, exc, tb)


class _Poster:
    def __init__(self, status: int = 204, fail_checks: set[str] | None = None, explode: bool = False) -> None:
        self.status = status
        self.fail_checks = fail_checks or set()
        self.explode = explode
        self.calls: list[tuple[str, dict, bytes]] = []

    def __call__(self, url: str, headers: dict, body: bytes, timeout: float) -> int:
        self.calls.append((url, dict(headers), body))
        if self.explode:
            raise RuntimeError(f"boom {url} supersecretvalue")
        payload = json.loads(body)
        if payload.get("check") in self.fail_checks:
            return 500
        return self.status


def _config() -> WebhookConfig:
    return WebhookConfig(
        url="https://alerts.example/hook",
        key="supersecretvalue",
        header_name="Authorization",
        key_format="Bearer {key}",
    )


class DedupeTests(unittest.TestCase):
    def test_reports_once_then_suppresses_until_change_or_12h(self) -> None:
        with _TempDir() as root:
            sources = _sources(root, kill=lambda: {"state": "OPEN", "enabled": True, "source": "redis"})
            state = root / "state"
            poster = _Poster()
            first = run_probe(sources, state, post_json=poster, webhook_config=_config())
            self.assertEqual(first["sent"], 1)
            self.assertEqual(first["payloads"][0]["repeat"], False)
            self.assertEqual(poster.calls[0][1]["Authorization"], "Bearer supersecretvalue")
            self.assertEqual(poster.calls[0][1]["User-Agent"], "anchor-fault-alarm/1.0")
            stored = load_state(state)
            self.assertEqual(stored["faults"]["kill_switch"]["last_alert"], "2026-10-24T08:30:00Z")
            again = run_probe(sources, state, post_json=_Poster(), webhook_config=_config())
            self.assertEqual(again["payloads"], [])
            self.assertEqual(again["sent"], 0)

            seeded = load_state(state)
            seeded["faults"]["kill_switch"]["last_alert"] = "2026-10-23T20:29:00Z"
            seeded["faults"]["kill_switch"]["since"] = "2026-10-24T01:00:00Z"
            save_state(state, seeded)
            reminded = run_probe(sources, state, post_json=_Poster(), webhook_config=_config())
            self.assertEqual(len(reminded["payloads"]), 1)
            self.assertIs(reminded["payloads"][0]["repeat"], True)
            self.assertEqual(reminded["payloads"][0]["since"], "2026-10-24T01:00:00Z")

            recent = load_state(state)
            recent["faults"]["kill_switch"]["fingerprint"] = "critical|kill switch is unreadable"
            recent["faults"]["kill_switch"]["detail"] = "kill switch is unreadable"
            recent["faults"]["kill_switch"]["last_alert"] = "2026-10-24T08:30:00Z"
            save_state(state, recent)
            changed = run_probe(sources, state, post_json=_Poster(), webhook_config=_config())
            self.assertEqual(changed["payloads"][0]["detail"], "kill switch is OPEN")
            self.assertIs(changed["payloads"][0]["repeat"], False)

    def test_twelve_hour_boundary(self) -> None:
        fault = kill_switch_fault({"state": "OPEN", "enabled": True}, NOW)
        assert fault is not None
        just_inside = {
            "faults": {
                "kill_switch": {
                    "fingerprint": fault.fingerprint,
                    "since": fault.since,
                    "last_alert": (NOW - timedelta(seconds=REMIND_S - 1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "severity": "critical",
                    "detail": fault.detail,
                }
            }
        }
        self.assertEqual(plan_notifications([fault], just_inside, NOW), [])
        due = {
            "faults": {
                "kill_switch": {
                    **just_inside["faults"]["kill_switch"],
                    "last_alert": (NOW - timedelta(seconds=REMIND_S)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            }
        }
        actions = plan_notifications([fault], due, NOW)
        self.assertEqual(len(actions), 1)
        self.assertTrue(actions[0].repeat)

    def test_recovery_is_sent_once(self) -> None:
        with _TempDir() as root:
            state = root / "state"
            open_sources = _sources(root, kill=lambda: {"state": "OPEN", "enabled": True})
            run_probe(open_sources, state, post_json=_Poster(), webhook_config=_config())
            healthy = _sources(root)
            poster = _Poster()
            cleared = run_probe(healthy, state, post_json=poster, webhook_config=_config())
            self.assertEqual(cleared["recovered"], 1)
            self.assertEqual(cleared["payloads"][0]["state"], "recovered")
            self.assertEqual(cleared["payloads"][0]["type"], "anchor_fault")
            self.assertEqual(cleared["payloads"][0]["check"], "kill_switch")
            self.assertEqual(load_state(state)["faults"], {})
            quiet = run_probe(healthy, state, post_json=_Poster(), webhook_config=_config())
            self.assertEqual(quiet["payloads"], [])

    def test_failed_send_does_not_advance_dedupe(self) -> None:
        with _TempDir() as root:
            sources = _sources(root, kill=lambda: {"state": "OPEN", "enabled": True})
            state = root / "state"
            failed = run_probe(sources, state, post_json=_Poster(status=503), webhook_config=_config())
            self.assertEqual(failed["sent"], 0)
            self.assertFalse((state / "fault_alarm_state.json").exists())
            retried = run_probe(sources, state, post_json=_Poster(), webhook_config=_config())
            self.assertEqual(retried["sent"], 1)

    def test_partial_failure_retries_only_the_unsent_fault(self) -> None:
        with _TempDir() as root:
            base = _show_for()
            props = _simple("nginx.service")
            props["active_state"] = "inactive"
            sources = _sources(
                root,
                show=_override(base, "nginx.service", props),
                kill=lambda: {"state": "OPEN", "enabled": True},
            )
            state = root / "state"
            first = run_probe(
                sources,
                state,
                post_json=_Poster(fail_checks={"service:nginx.service"}),
                webhook_config=_config(),
            )
            self.assertEqual(first["sent"], 1)
            self.assertIn("kill_switch", load_state(state)["faults"])
            self.assertNotIn("service:nginx.service", load_state(state)["faults"])
            second = run_probe(sources, state, post_json=_Poster(), webhook_config=_config())
            self.assertEqual([item["check"] for item in second["payloads"]], ["service:nginx.service"])

    def test_dry_run_prints_payloads_without_sending_or_writing(self) -> None:
        with _TempDir() as root:
            sources = _sources(root, kill=lambda: {"state": "OPEN", "enabled": True})
            state = root / "state"
            poster = _Poster()
            result = run_probe(sources, state, dry_run=True, post_json=poster, webhook_config=_config())
            self.assertTrue(result["dry_run"])
            self.assertEqual(poster.calls, [])
            self.assertEqual(result["payloads"][0]["type"], "anchor_fault")
            self.assertFalse(state.exists())


class PayloadTests(unittest.TestCase):
    def test_payload_shape_is_distinct_from_mf4_signals(self) -> None:
        action = Action(
            kind="fault",
            check="service:anchor-mf4-watcher.service",
            since="2026-10-24T12:05:00Z",
            severity="critical",
            detail="anchor-mf4-watcher.service is not active (inactive/dead); result=success",
            fingerprint="critical|anchor-mf4-watcher.service is not active (inactive/dead); result=success",
            repeat=False,
        )
        payload = finalize_payload(build_payload(action, NOW), ("supersecretvalue", "https://alerts.example/hook"))
        self.assertEqual(set(payload), set(PAYLOAD_KEYS))
        self.assertEqual(payload["type"], "anchor_fault")
        self.assertEqual(payload["source"], "anchor-fault-alarm")
        self.assertEqual(payload["state"], "fault")
        self.assertEqual(payload["severity"], "critical")
        self.assertEqual(payload["since"], "2026-10-24T12:05:00Z")
        self.assertTrue(payload["event_id"].startswith("fault-"))
        self.assertEqual(len(payload["event_id"]), len("fault-") + 20)
        self.assertNotIn("signal", payload)
        self.assertNotIn("strategy", payload)
        self.assertNotIn("supersecretvalue", json.dumps(payload))
        self.assertNotIn("alerts.example", json.dumps(payload))

    def test_secret_in_a_detail_is_redacted(self) -> None:
        action = Action(
            kind="fault",
            check="kill_switch",
            since="2026-10-24T08:30:00Z",
            severity="critical",
            detail="kill switch is OPEN supersecretvalue",
            fingerprint="x",
            repeat=False,
        )
        payload = finalize_payload(build_payload(action, NOW), ("supersecretvalue",))
        self.assertNotIn("supersecretvalue", json.dumps(payload))
        self.assertIn("[REDACTED]", payload["detail"])

    def test_delivery_error_does_not_log_the_secret(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ok = deliver_payload(
                {"type": "anchor_fault"},
                _config(),
                _Poster(explode=True),
            )
        self.assertFalse(ok)
        logged = buf.getvalue()
        self.assertIn("network_error", logged)
        self.assertNotIn("supersecretvalue", logged)
        self.assertNotIn("alerts.example", logged)

    def test_sent_state_and_probe_output_omit_secrets_and_canaries(self) -> None:
        with _TempDir() as root:
            sources = _sources(root, kill=lambda: {"state": "UNKNOWN", "enabled": None})
            state = root / "state"
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(buf):
                result = run_probe(sources, state, post_json=_Poster(), webhook_config=_config())
            blob = json.dumps(result) + (state / "fault_alarm_state.json").read_text(encoding="utf-8") + buf.getvalue()
            self.assertNotIn("supersecretvalue", blob)
            self.assertNotIn("alerts.example", blob)
            self.assertNotIn("SECRET_CANARY_should_not_leak", blob)

    def test_selected_env_keeps_only_kill_switch_keys(self) -> None:
        with _TempDir() as root:
            path = root / "mcp.env"
            path.write_text(
                "\n".join(
                    (
                        "ANCHOR_CONTROL_MCP_TOKEN=mcp-token-value",
                        "REDIS_URL=redis://127.0.0.1:6379/0",
                        "export ANCHOR_KILL_SWITCH=0",
                    )
                ),
                encoding="utf-8",
            )
            found = _selected_env(path, ("REDIS_URL", "ANCHOR_KILL_SWITCH"))
        self.assertEqual(found, {"REDIS_URL": "redis://127.0.0.1:6379/0", "ANCHOR_KILL_SWITCH": "0"})
        self.assertNotIn("mcp-token-value", json.dumps(found))

    def test_unreadable_host_checkout_falls_back_to_the_source_tree(self) -> None:
        with mock.patch.dict(os.environ, {"ANCHOR_FAULT_REPO_ROOT": ""}, clear=False), mock.patch.object(
            Path, "is_file", side_effect=PermissionError(13, "Permission denied")
        ):
            resolved = resolve_repo(None)
        self.assertEqual(resolved, ROOT)

    def test_main_dry_run_does_not_post(self) -> None:
        with _TempDir() as root:
            sources = _sources(root, kill=lambda: {"state": "OPEN", "enabled": True})
            buf = io.StringIO()
            with mock.patch("ops.fault_alarm.probe.build_sources", return_value=sources), mock.patch(
                "ops.fault_alarm.probe.urllib_post_json",
                side_effect=AssertionError("network"),
            ), contextlib.redirect_stdout(buf):
                code = main(["--dry-run", "--state-dir", str(root / "state")])
            self.assertEqual(code, 0)
            printed = json.loads(buf.getvalue())
            self.assertTrue(printed["dry_run"])
            self.assertEqual(printed["payloads"][0]["type"], "anchor_fault")
            self.assertNotIn("supersecretvalue", buf.getvalue())


class UnitFileTests(unittest.TestCase):
    def test_units_are_read_only_and_timer_is_five_minutes(self) -> None:
        service = (ROOT / "ops" / "fault_alarm" / "anchor-fault-alarm.service").read_text(encoding="utf-8")
        timer = (ROOT / "ops" / "fault_alarm" / "anchor-fault-alarm.timer").read_text(encoding="utf-8")
        install = (ROOT / "ops" / "fault_alarm" / "install_fault_alarm.sh").read_text(encoding="utf-8")
        rollback = (ROOT / "ops" / "fault_alarm" / "ROLLBACK_FAULT_ALARM.sh").read_text(encoding="utf-8")
        probe = (ROOT / "ops" / "fault_alarm" / "probe.py").read_text(encoding="utf-8")
        self.assertIn("StateDirectory=anchor-fault-alarm", service)
        self.assertIn("OnUnitActiveSec=5min", timer)
        self.assertIn("LoadCredential=webhook:/etc/anchor-mf4-watcher/webhook.env", service)
        self.assertIn("InaccessiblePaths=", service)
        self.assertIn("/var/lib/anchor-official-ledger-20261010", service)
        self.assertIn("/var/lib/private", service)
        self.assertIn("/var/lib/anchor-ledger-mirror", service)
        self.assertIn('["systemctl", "show"', probe)
        for text in (service, timer, install, probe):
            self.assertNotIn("systemctl restart", text)
            self.assertNotIn("systemctl start anchor-official-ledger", text)
            self.assertNotIn("chmod ", text)
            self.assertNotIn("setfacl", text)
        self.assertIn("systemctl enable --now anchor-fault-alarm.timer", install)
        self.assertIn("systemctl start anchor-fault-alarm.service", install)
        self.assertNotRegex(rollback, r"rm\s+.*anchor-official-ledger")
        self.assertNotRegex(rollback, r"rm\s+.*webhook\.env")
        self.assertNotRegex(rollback, r"chmod\s+")
        self.assertIn("STATE_DIR_REMOVED=NO", rollback)

    def test_install_and_rollback_refuse_non_root(self) -> None:
        if os.geteuid() == 0:
            self.skipTest("non-root refusal is the path under test")
        for name in ("install_fault_alarm.sh", "ROLLBACK_FAULT_ALARM.sh"):
            result = subprocess.run(
                ["bash", str(ROOT / "ops" / "fault_alarm" / name)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("must_run_as_root", result.stdout + result.stderr)

    def test_state_dir_rejects_symlinks_and_sealed_ledger_paths(self) -> None:
        with _TempDir() as root:
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaises(Exception) as raised:
                save_state(link, {"version": 1, "faults": {}})
            self.assertEqual(getattr(raised.exception, "reason", ""), "state_dir_symlink")
            sealed = root / "anchor-official-ledger-20261010"
            sealed.mkdir()
            mode = stat.S_IMODE(sealed.stat().st_mode)
            with self.assertRaises(Exception) as raised:
                save_state(sealed, {"version": 1, "faults": {}})
            self.assertEqual(getattr(raised.exception, "reason", ""), "state_dir_rejected")
            self.assertEqual(stat.S_IMODE(sealed.stat().st_mode), mode)
            self.assertEqual(list(sealed.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
