import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.mcp.backend_probe import HEALTH_URL, OPS_URL, _fetch_allowlisted, probe_backend
from app.mcp.commands import CommandResult, run_readonly_command
from app.mcp.host_sidecar import (
    BindRejected,
    create_app,
    open_loopback_listener,
    render_service_unit,
    require_loopback_bind,
    root_rejected,
    unit_problems,
)
from app.mcp.inventory import (
    CLASS_AUXILIARY,
    CLASS_CORE_RUNTIME,
    CLASS_EVALUATION,
    CLASS_INTENTIONALLY_DISABLED,
    GATING_CLASSES,
    RECOMMENDED_SERVICE_UNITS,
    RECOMMENDED_TIMER_UNITS,
    classify_unit,
)
from app.mcp.tools import TOOL_NAMES, ToolContext, call_tool


REPO = Path(__file__).resolve().parents[2]
TOKEN = "test-mcp-token-value"
HOST_ENV = {"ANCHOR_CONTROL_MCP_HOST_SIDECAR": "1"}


def _show(unit: str, active: str, result: str, unit_type: str = "simple") -> str:
    substate = "running" if active == "active" else "dead"
    return "\n".join(
        [
            f"Id={unit}",
            f"ActiveState={active}",
            f"SubState={substate}",
            "UnitFileState=enabled",
            f"Result={result}",
            f"Type={unit_type}",
            "Description=read-only unit",
        ]
    )


class HostRunner:
    def __init__(self, states: dict[str, tuple[str, str, str]]) -> None:
        self.states = states
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], timeout: float) -> CommandResult:
        self.calls.append(list(argv))
        if argv[0] == "journalctl":
            return CommandResult(True, 0, "", "")
        unit = argv[2]
        active, result, unit_type = self.states.get(unit, ("inactive", "success", "simple"))
        if unit.endswith(".timer"):
            return CommandResult(True, 0, _show(unit, active, result), "")
        return CommandResult(True, 0, _show(unit, active, result, unit_type), "")


def _healthy_states() -> dict[str, tuple[str, str, str]]:
    return {
        "docker.service": ("active", "success", "simple"),
        "project-anchor-post-production-monitoring.service": ("dead", "success", "oneshot"),
        "project-anchor-post-production-monitoring.timer": ("active", "success", "simple"),
        "nginx.service": ("inactive", "success", "simple"),
        "jev-forward-shadow-v2.service": ("inactive", "success", "simple"),
        "whisper.service": ("inactive", "success", "simple"),
        "word-converter.service": ("inactive", "success", "simple"),
        "commercial.service": ("failed", "failed", "simple"),
        "payment.service": ("inactive", "success", "simple"),
    }


def _context(root: Path, runner: HostRunner, env: dict[str, str]) -> ToolContext:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return ToolContext(
        reports_dir=reports,
        repo_root=root,
        env=env,
        run_command=runner,
        kill_switch=lambda: {"enabled": False, "source": "redis", "state": "CLOSED", "reason": "redis_read"},
        clock=lambda: "2026-09-29T00:00:00Z",
        extra_secrets=(TOKEN,),
    )


def _write_artifacts(ctx: ToolContext) -> None:
    observation = {
        "generated_at": "2026-09-29T00:00:00Z",
        "result": "PASS",
        "boundary": {"go_live": "NO-GO", "live_trading": "NO-GO"},
    }
    ledger = {
        "generated_at": "2026-09-29T00:00:00Z",
        "result": "PASS",
        "fake_transport_external_status": "FILLED",
        "boundary": {"go_live": "NO-GO", "live_trading": "NO-GO", "production_request_sent": "NO"},
    }
    (ctx.reports_dir / "forward_observation.json").write_text(json.dumps(observation), encoding="utf-8")
    (ctx.reports_dir / "official_fake_fill_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")


def _probe_ok(_env, fetch=None):
    return {
        "enabled": True,
        "ok": True,
        "reason": "health_ok",
        "health_status": 200,
        "ops_reachable": True,
        "ops_has_kill_switch": True,
        "ops_has_worker_heartbeat": False,
        "ops_has_worker_panic": False,
        "transport": "http",
        "upstream": "127.0.0.1:8000",
    }


class InventoryClassificationTests(unittest.TestCase):
    def test_founder_note_classes_and_gating(self) -> None:
        self.assertEqual(GATING_CLASSES, (CLASS_CORE_RUNTIME,))
        self.assertEqual(RECOMMENDED_SERVICE_UNITS, ("docker.service",))
        self.assertEqual(RECOMMENDED_TIMER_UNITS, ())
        expected = {
            "docker.service": CLASS_CORE_RUNTIME,
            "project-anchor-post-production-monitoring.service": CLASS_AUXILIARY,
            "project-anchor-post-production-monitoring.timer": CLASS_AUXILIARY,
            "nginx.service": CLASS_AUXILIARY,
            "jev-forward-shadow-v2.service": CLASS_INTENTIONALLY_DISABLED,
            "whisper.service": CLASS_AUXILIARY,
            "faster-whisper.service": CLASS_AUXILIARY,
            "word-converter.service": CLASS_AUXILIARY,
            "word_converter.service": CLASS_AUXILIARY,
            "commercial-preview.service": CLASS_EVALUATION,
            "payment.service": CLASS_EVALUATION,
            "anchor-payment-api.service": CLASS_EVALUATION,
        }
        for name, unit_class in expected.items():
            classified = classify_unit(name)
            self.assertEqual(classified["unit_class"], unit_class, name)
            self.assertEqual(classified["gates_overall_pass"], unit_class == CLASS_CORE_RUNTIME, name)
        disabled = classify_unit("jev-forward-shadow-v2.service")
        self.assertEqual(disabled["expectation"], "not_required")
        self.assertIs(disabled["gates_overall_pass"], False)

    def test_unknown_allowlisted_unit_stays_core(self) -> None:
        classified = classify_unit("anchor-worker.service")
        self.assertEqual(classified["unit_class"], CLASS_CORE_RUNTIME)
        self.assertIs(classified["gates_overall_pass"], True)


class HostHealthTests(unittest.TestCase):
    def test_disabled_and_auxiliary_units_do_not_gate_pass(self) -> None:
        states = _healthy_states()
        runner = HostRunner(states)
        env = {
            **HOST_ENV,
            "ANCHOR_CONTROL_MCP_SERVICE_UNITS": ",".join(
                [
                    "docker.service",
                    "whisper.service",
                    "word-converter.service",
                    "commercial.service",
                    "payment.service",
                    "jev-forward-shadow-v2.service",
                ]
            ),
        }
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _context(Path(tmp), runner, env)
            _write_artifacts(ctx)
            from app.mcp import tools as tools_module

            original = tools_module.probe_backend
            tools_module.probe_backend = _probe_ok
            try:
                status = call_tool("get_anchor_status", {}, ctx)
                services = call_tool("get_services", {}, ctx)
                timers = call_tool("get_timers", {}, ctx)
                health = call_tool("run_readonly_healthcheck", {}, ctx)
            finally:
                tools_module.probe_backend = original
        self.assertEqual(status["process"]["state"], "PASS")
        self.assertIs(status["process"]["ok"], True)
        self.assertIn("docker.service", status["process"]["gating_units"])
        self.assertIn("jev-forward-shadow-v2.service", status["process"]["ignored_for_pass"])
        self.assertIn("whisper.service", status["process"]["ignored_for_pass"])
        self.assertIn("word-converter.service", status["process"]["ignored_for_pass"])
        self.assertIn("commercial.service", status["process"]["ignored_for_pass"])
        self.assertIn("payment.service", status["process"]["ignored_for_pass"])
        by_name = {item["name"]: item for item in services["units"]}
        self.assertEqual(by_name["jev-forward-shadow-v2.service"]["unit_class"], CLASS_INTENTIONALLY_DISABLED)
        self.assertIs(by_name["jev-forward-shadow-v2.service"]["gates_overall_pass"], False)
        self.assertFalse(by_name["jev-forward-shadow-v2.service"]["healthy"])
        self.assertEqual(by_name["whisper.service"]["unit_class"], CLASS_AUXILIARY)
        self.assertEqual(by_name["payment.service"]["unit_class"], CLASS_EVALUATION)
        self.assertEqual(services["recommended_service_units"], ["docker.service"])
        self.assertEqual(services["gating_classes"], [CLASS_CORE_RUNTIME])
        self.assertEqual(timers["recommended_timer_units"], [])
        self.assertEqual(health["verdict"], "PASS")
        self.assertIn("backend_http", [item["name"] for item in health["checks"]])
        journal_units = [call[2] for call in runner.calls if call[0] == "journalctl"]
        self.assertEqual(journal_units, ["docker.service"])
        self.assertNotIn("jev-forward-shadow-v2.service", journal_units)

    def test_intentionally_disabled_unit_active_still_passes(self) -> None:
        states = _healthy_states()
        states["jev-forward-shadow-v2.service"] = ("active", "success", "simple")
        runner = HostRunner(states)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _context(Path(tmp), runner, dict(HOST_ENV))
            _write_artifacts(ctx)
            from app.mcp import tools as tools_module

            original = tools_module.probe_backend
            tools_module.probe_backend = _probe_ok
            try:
                services = call_tool("get_services", {}, ctx)
                health = call_tool("run_readonly_healthcheck", {}, ctx)
            finally:
                tools_module.probe_backend = original
        jev = next(item for item in services["units"] if item["name"] == "jev-forward-shadow-v2.service")
        self.assertEqual(jev["note"], "active_while_intentionally_disabled")
        self.assertEqual(health["verdict"], "PASS")

    def test_core_runtime_down_is_not_pass(self) -> None:
        states = _healthy_states()
        states["docker.service"] = ("inactive", "success", "simple")
        runner = HostRunner(states)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _context(Path(tmp), runner, dict(HOST_ENV))
            _write_artifacts(ctx)
            from app.mcp import tools as tools_module

            original = tools_module.probe_backend
            tools_module.probe_backend = _probe_ok
            try:
                status = call_tool("get_anchor_status", {}, ctx)
                health = call_tool("run_readonly_healthcheck", {}, ctx)
            finally:
                tools_module.probe_backend = original
        self.assertEqual(status["process"]["state"], "FAILED")
        self.assertIs(status["process"]["ok"], False)
        self.assertNotEqual(health["verdict"], "PASS")

    def test_container_mode_does_not_apply_host_classes(self) -> None:
        runner = HostRunner(_healthy_states())
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _context(Path(tmp), runner, {})
            status = call_tool("get_anchor_status", {}, ctx)
            services = call_tool("get_services", {}, ctx)
        self.assertNotIn("backend_http", status)
        self.assertNotIn("unit_class", services["units"][0])
        self.assertNotIn("host_sidecar", services)
        self.assertEqual(services["expected_units"], ["project-anchor-post-production-monitoring.service"])
        self.assertEqual(len(TOOL_NAMES), 7)


class BackendProbeTests(unittest.TestCase):
    def test_only_loopback_backend_urls_are_fetched(self) -> None:
        self.assertEqual(_fetch_allowlisted("http://127.0.0.1:8000/mcp")["reason"], "url_rejected")
        self.assertEqual(_fetch_allowlisted("http://169.254.169.254/latest")["reason"], "url_rejected")
        self.assertEqual(_fetch_allowlisted("unix:///var/run/docker.sock")["reason"], "url_rejected")
        seen: list[str] = []

        def fetch(url: str) -> dict:
            seen.append(url)
            if url == HEALTH_URL:
                return {"ok": True, "status": 200, "reason": "ok", "json": {"ok": True, "token": "secret-token"}}
            return {
                "ok": True,
                "status": 200,
                "reason": "ok",
                "json": {
                    "kill_switch": {"enabled": False},
                    "worker_heartbeat": {"last_seen_at": "2026-09-29T00:00:00Z"},
                    "worker_panic": {},
                    "recent_ops_events": [{"payload": "secret-token"}],
                },
            }

        result = probe_backend(HOST_ENV, fetch=fetch)
        self.assertEqual(seen, [HEALTH_URL, OPS_URL])
        self.assertIs(result["ok"], True)
        self.assertIs(result["ops_has_kill_switch"], True)
        blob = json.dumps(result)
        self.assertNotIn("secret-token", blob)
        self.assertNotIn("json", result)
        disabled = probe_backend({**HOST_ENV, "ANCHOR_CONTROL_MCP_BACKEND_PROBE": "0"}, fetch=fetch)
        self.assertIs(disabled["enabled"], False)
        self.assertEqual(disabled["reason"], "probe_disabled")
        self.assertEqual(len(seen), 2)
        untouched = probe_backend({}, fetch=fetch)
        self.assertEqual(untouched["reason"], "not_host_sidecar")
        self.assertEqual(len(seen), 2)

    def test_live_loopback_probe_drops_body(self) -> None:
        result = probe_backend(HOST_ENV)
        self.assertIs(result["enabled"], True)
        self.assertIn(result["ok"], (True, False))
        self.assertNotIn("body", result)
        self.assertNotIn("json", result)
        self.assertEqual(result["upstream"], "127.0.0.1:8000")


class PackagingAndEntrypointTests(unittest.TestCase):
    def test_bind_policy_and_non_root(self) -> None:
        self.assertEqual(require_loopback_bind({}), ("127.0.0.1", 8001))
        self.assertEqual(require_loopback_bind({"ANCHOR_CONTROL_MCP_BIND": "127.0.0.1:8001"}), ("127.0.0.1", 8001))
        for raw in ("0.0.0.0:8001", "127.0.0.1:8000", "[::]:8001", "127.0.0.1:8001/mcp"):
            with self.assertRaises(BindRejected):
                require_loopback_bind({"ANCHOR_CONTROL_MCP_BIND": raw})
        self.assertIs(root_rejected(0), True)
        self.assertIs(root_rejected(999), False)

    def test_listener_is_loopback_8001(self) -> None:
        try:
            sock = open_loopback_listener({})
        except OSError as exc:
            self.skipTest(f"port 8001 unavailable: {exc}")
        try:
            self.assertEqual(sock.getsockname(), ("127.0.0.1", 8001))
        finally:
            sock.close()

    def test_unit_example_matches_renderer_and_forbids_control_paths(self) -> None:
        rendered = render_service_unit()
        example = (REPO / "anchor-backend/docs/systemd/anchor-control-mcp.service.example").read_text(encoding="utf-8")
        self.assertEqual(example, rendered)
        self.assertEqual(unit_problems(rendered), [])
        self.assertIn("User=anchor-mcp", rendered)
        self.assertNotIn("User=root", rendered)
        probe_src = (REPO / "anchor-backend/app/mcp/backend_probe.py").read_text(encoding="utf-8")
        self.assertNotIn("docker.sock", probe_src)
        self.assertNotIn("subprocess", probe_src)
        for argv in (
            ["docker", "ps"],
            ["ssh", "vultr"],
            ["systemctl", "start", "docker.service"],
            ["systemctl", "stop", "docker.service"],
        ):
            result = run_readonly_command(argv)
            self.assertEqual(result.stderr, "command_rejected")
            self.assertEqual(result.stdout, "")

    def test_render_script_prints_the_example(self) -> None:
        path = REPO / "scripts/render_anchor_control_mcp_host_unit.py"
        spec = importlib.util.spec_from_file_location("render_anchor_control_mcp_host_unit", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = module.main()
        self.assertEqual(code, 0)
        self.assertEqual(buffer.getvalue(), render_service_unit())

    def test_sidecar_app_exposes_only_mcp(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except Exception as exc:  # pragma: no cover - environment without FastAPI
            self.skipTest(f"fastapi test client unavailable: {exc}")
        app = create_app()
        paths: list[str] = []
        pending = list(app.router.routes)
        while pending:
            route = pending.pop()
            path = getattr(route, "path", None)
            if isinstance(path, str):
                paths.append(path)
            nested = getattr(route, "original_router", None)
            if nested is not None:
                pending.extend(list(getattr(nested, "routes", [])))
            extra = getattr(route, "routes", None)
            if extra:
                pending.extend(list(extra))
        self.assertIn("/mcp", paths)
        for path in paths:
            self.assertNotIn("trade", path)
            self.assertNotIn("order", path)
            self.assertNotIn("/ops", path)
        previous = os.environ.get("ANCHOR_CONTROL_MCP_TOKEN")
        os.environ.pop("ANCHOR_CONTROL_MCP_TOKEN", None)
        try:
            client = TestClient(app)
            denied = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertEqual(denied.status_code, 503)
            os.environ["ANCHOR_CONTROL_MCP_TOKEN"] = TOKEN
            allowed = client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
        finally:
            if previous is None:
                os.environ.pop("ANCHOR_CONTROL_MCP_TOKEN", None)
            else:
                os.environ["ANCHOR_CONTROL_MCP_TOKEN"] = previous
        self.assertEqual(allowed.status_code, 200)
        names = [tool["name"] for tool in allowed.json()["result"]["tools"]]
        self.assertEqual(names, list(TOOL_NAMES))

    def test_docker_backend_port_is_unchanged(self) -> None:
        compose = (REPO / "anchor-backend/docker-compose.yml").read_text(encoding="utf-8")
        dockerfile = (REPO / "anchor-backend/Dockerfile").read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1:8000:8000"', compose)
        self.assertNotIn("8001", compose)
        self.assertIn('--port", "8000"', dockerfile)
        example = (REPO / "anchor-backend/docs/nginx/anchor-control-mcp.location.example.conf").read_text(encoding="utf-8")
        self.assertIn("proxy_pass http://127.0.0.1:8001/mcp;", example)
        self.assertNotIn("proxy_pass http://127.0.0.1:8000/mcp;", example)


if __name__ == "__main__":
    unittest.main()
