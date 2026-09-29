import ast
import json
import os
import tempfile
import unittest
from pathlib import Path

from app.mcp import ENDPOINT_PATH, TOKEN_ENV
from app.mcp.commands import (
    CommandResult,
    journalctl_err_argv,
    run_readonly_command,
    systemctl_show_argv,
)
from app.mcp.protocol import dispatch_http
from app.mcp.sanitize import redact_text
from app.mcp.tools import TOOL_NAMES, ToolContext, call_tool, tool_definitions


TOKEN = "test-mcp-token-value"
REPO = Path(__file__).resolve().parents[2]


def _ok_show(unit: str, active: str, result: str, unit_type: str = "simple") -> str:
    return "\n".join(
        [
            f"Id={unit}",
            f"ActiveState={active}",
            "SubState=dead" if active != "active" else "SubState=running",
            "UnitFileState=enabled",
            f"Result={result}",
            f"Type={unit_type}",
            "Description=read-only unit",
            "NextElapseUSecRealtime=",
            "LastTriggerUSecRealtime=",
        ]
    )


class RecordingRunner:
    def __init__(self, journal_stdout: str = "") -> None:
        self.calls: list[list[str]] = []
        self.journal_stdout = journal_stdout

    def __call__(self, argv: list[str], timeout: float) -> CommandResult:
        self.calls.append(list(argv))
        if argv[0] == "journalctl":
            return CommandResult(True, 0, self.journal_stdout, "")
        unit = argv[2]
        if unit.endswith(".service"):
            return CommandResult(True, 0, _ok_show(unit, "active", "success", "simple"), "")
        return CommandResult(True, 0, _ok_show(unit, "active", "success"), "")


def _context(root: Path, runner: RecordingRunner | None = None, env: dict | None = None) -> ToolContext:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    selected_env = env or {}
    return ToolContext(
        reports_dir=reports,
        repo_root=root,
        env=selected_env,
        run_command=runner or RecordingRunner(),
        kill_switch=lambda: {"enabled": False, "source": "redis", "state": "CLOSED", "reason": "redis_read"},
        clock=lambda: "2026-09-29T00:00:00Z",
        extra_secrets=(TOKEN,),
    )


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class AnchorControlMcpToolTests(unittest.TestCase):
    def test_registry_is_exactly_the_seven_tools(self) -> None:
        self.assertEqual(
            TOOL_NAMES,
            (
                "get_anchor_status",
                "get_latest_observation",
                "get_ledger_summary",
                "get_services",
                "get_timers",
                "get_recent_errors",
                "run_readonly_healthcheck",
            ),
        )
        advertised = tuple(tool["name"] for tool in tool_definitions())
        self.assertEqual(advertised, TOOL_NAMES)
        for tool in tool_definitions():
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["destructiveHint"])

    def test_main_mounts_mcp_router(self) -> None:
        main_path = REPO / "anchor-backend" / "app" / "main.py"
        tree = ast.parse(main_path.read_text(encoding="utf-8"))
        mounted = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "include_router"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "anchor_control_mcp_router"
            ):
                mounted = True
        self.assertTrue(mounted)

    def test_status_observation_ledger_and_healthcheck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = RecordingRunner()
            ctx = _context(root, runner)
            _write(
                ctx.reports_dir / "forward_observation.json",
                {
                    "generated_at": "2026-09-29T00:00:00Z",
                    "result": "PASS",
                    "next_gate": "CONTINUE_OBSERVATION",
                    "boundary": {"go_live": "NO-GO", "live_trading": "NO-GO", "runtime_modified": "NO"},
                    "checks": [{"name": "window", "result": "PASS", "evidence": "API_KEY=should-not-leak"}],
                    "errors": [],
                    "api_key": "should-not-leak",
                },
            )
            _write(
                ctx.reports_dir / "official_fake_fill_ledger.json",
                {
                    "generated_at": "2026-09-28T00:00:00Z",
                    "result": "PASS",
                    "fake_transport_external_status": "FILLED",
                    "fake_transport_called_once": True,
                    "fake_transport_external_order_id_present": True,
                    "external_order_id": "999",
                    "boundary": {
                        "go_live": "NO-GO",
                        "live_trading": "NO-GO",
                        "production_request_sent": "NO",
                    },
                    "credential_path": "/etc/project-anchor/production.env",
                },
            )
            _write(
                ctx.reports_dir / "production_exactly_one_send_result.json",
                {"generated_at": "2026-09-29T01:00:00Z", "secret": "real-send-secret", "result": "PASS"},
            )
            status = call_tool("get_anchor_status", {}, ctx)
            observation = call_tool("get_latest_observation", {}, ctx)
            ledger = call_tool("get_ledger_summary", {}, ctx)
            services = call_tool("get_services", {}, ctx)
            timers = call_tool("get_timers", {}, ctx)
            health = call_tool("run_readonly_healthcheck", {}, ctx)
            blob = json.dumps(
                {"status": status, "observation": observation, "ledger": ledger, "services": services, "timers": timers, "health": health}
            )
            self.assertEqual(status["process"]["state"], "PASS")
            self.assertEqual(status["process"]["ok"], True)
            self.assertEqual(status["process"]["source"], "systemctl show")
            self.assertEqual(status["kill_switch"]["state"], "CLOSED")
            self.assertEqual(status["kill_switch"]["enabled"], False)
            process_check = next(item for item in health["checks"] if item["name"] == "process")
            kill_check = next(item for item in health["checks"] if item["name"] == "kill_switch")
            self.assertEqual(process_check["result"], "PASS")
            self.assertEqual(kill_check["result"], "PASS")
            self.assertEqual(observation["observation_class"], "forward")
            self.assertEqual(observation["source"], "forward_observation.json")
            self.assertEqual(observation["result"], "PASS")
            self.assertNotIn("evidence", blob)
            self.assertEqual(ledger["kind"], "official_fake_fill")
            self.assertEqual(ledger["fill_status"], "FILLED")
            self.assertEqual(services["units"][0]["healthy"], True)
            self.assertEqual(timers["units"][0]["healthy"], True)
            self.assertEqual(health["verdict"], "PASS")
            self.assertEqual([item["name"] for item in health["checks"]], [
                "process",
                "kill_switch",
                "observation",
                "ledger",
                "services",
                "timers",
                "recent_errors",
            ])
            self.assertNotIn("should-not-leak", blob)
            self.assertNotIn("real-send-secret", blob)
            self.assertNotIn("external_order_id", blob)
            self.assertNotIn("production.env", blob)
            self.assertNotIn(TOKEN, blob)
            self.assertTrue(all(call[0] in {"systemctl", "journalctl"} for call in runner.calls))
            self.assertFalse(any("start" in call or "stop" in call for call in runner.calls))

    def test_invalid_unit_override_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = RecordingRunner()
            ctx = _context(
                root,
                runner,
                env={"ANCHOR_CONTROL_MCP_SERVICE_UNITS": "nginx.service;reboot"},
            )
            payload = call_tool("get_services", {}, ctx)
            self.assertEqual(payload["unit_config"], "invalid_override_ignored")
            self.assertEqual(payload["expected_units"], ["project-anchor-post-production-monitoring.service"])
            self.assertTrue(all("reboot" not in part for call in runner.calls for part in call))

    def test_process_unknown_or_failed_is_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_ctx = _context(root, RecordingRunner())

            def unavailable(argv: list[str], timeout: float) -> CommandResult:
                if argv[0] == "journalctl":
                    return CommandResult(False, None, "", "command_not_found")
                return CommandResult(False, None, "", "command_not_found")

            missing_ctx.run_command = unavailable
            status = call_tool("get_anchor_status", {}, missing_ctx)
            health = call_tool("run_readonly_healthcheck", {}, missing_ctx)
            self.assertEqual(status["process"]["state"], "UNKNOWN")
            self.assertIsNone(status["process"]["ok"])
            self.assertNotEqual(status["process"]["state"], "PASS")
            process_check = next(item for item in health["checks"] if item["name"] == "process")
            self.assertEqual(process_check["result"], "UNKNOWN")
            self.assertNotEqual(health["verdict"], "PASS")

            def failed(argv: list[str], timeout: float) -> CommandResult:
                unit = argv[2]
                if argv[0] == "journalctl":
                    return CommandResult(True, 0, "", "")
                if unit.endswith(".service"):
                    return CommandResult(True, 0, _ok_show(unit, "failed", "failed"), "")
                return CommandResult(True, 0, _ok_show(unit, "active", "success"), "")

            failed_ctx = _context(root, RecordingRunner())
            failed_ctx.run_command = failed
            failed_status = call_tool("get_anchor_status", {}, failed_ctx)
            failed_health = call_tool("run_readonly_healthcheck", {}, failed_ctx)
            self.assertEqual(failed_status["process"]["state"], "FAILED")
            self.assertIs(failed_status["process"]["ok"], False)
            failed_check = next(item for item in failed_health["checks"] if item["name"] == "process")
            self.assertEqual(failed_check["result"], "DEGRADED")
            self.assertNotEqual(failed_health["verdict"], "PASS")

    def test_stopped_long_running_service_with_success_is_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def stopped(argv: list[str], timeout: float) -> CommandResult:
                unit = argv[2]
                if argv[0] == "journalctl":
                    return CommandResult(True, 0, "", "")
                if unit.endswith(".service"):
                    return CommandResult(True, 0, _ok_show(unit, "inactive", "success", "simple"), "")
                return CommandResult(True, 0, _ok_show(unit, "active", "success"), "")

            ctx = _context(root, RecordingRunner())
            ctx.run_command = stopped
            status = call_tool("get_anchor_status", {}, ctx)
            services = call_tool("get_services", {}, ctx)
            health = call_tool("run_readonly_healthcheck", {}, ctx)
            self.assertEqual(services["units"][0]["healthy"], False)
            self.assertEqual(services["units"][0]["properties"]["active_state"], "inactive")
            self.assertEqual(services["units"][0]["properties"]["result"], "success")
            self.assertEqual(status["process"]["state"], "FAILED")
            self.assertIs(status["process"]["ok"], False)
            process_check = next(item for item in health["checks"] if item["name"] == "process")
            self.assertEqual(process_check["result"], "DEGRADED")
            self.assertNotEqual(health["verdict"], "PASS")

            def oneshot_idle(argv: list[str], timeout: float) -> CommandResult:
                unit = argv[2]
                if argv[0] == "journalctl":
                    return CommandResult(True, 0, "", "")
                if unit.endswith(".service"):
                    return CommandResult(True, 0, _ok_show(unit, "dead", "success", "oneshot"), "")
                return CommandResult(True, 0, _ok_show(unit, "active", "success"), "")

            oneshot_ctx = _context(root, RecordingRunner())
            oneshot_ctx.run_command = oneshot_idle
            oneshot_status = call_tool("get_anchor_status", {}, oneshot_ctx)
            self.assertEqual(oneshot_status["process"]["state"], "PASS")
            self.assertIs(oneshot_status["process"]["ok"], True)

    def test_unread_kill_switch_is_unknown_not_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _context(Path(tmp), RecordingRunner())
            ctx.kill_switch = lambda: {"enabled": False, "source": "none"}
            status = call_tool("get_anchor_status", {}, ctx)
            health = call_tool("run_readonly_healthcheck", {}, ctx)
            self.assertEqual(status["kill_switch"]["state"], "UNKNOWN")
            self.assertIsNone(status["kill_switch"]["enabled"])
            self.assertNotEqual(status["kill_switch"]["state"], "CLOSED")
            kill_check = next(item for item in health["checks"] if item["name"] == "kill_switch")
            self.assertEqual(kill_check["result"], "UNKNOWN")
            self.assertNotEqual(health["verdict"], "PASS")

            ctx.kill_switch = lambda: {"enabled": True, "source": "env", "state": "OPEN", "reason": "env_flag"}
            opened = call_tool("get_anchor_status", {}, ctx)
            opened_health = call_tool("run_readonly_healthcheck", {}, ctx)
            self.assertEqual(opened["kill_switch"]["state"], "OPEN")
            self.assertIs(opened["kill_switch"]["enabled"], True)
            opened_check = next(item for item in opened_health["checks"] if item["name"] == "kill_switch")
            self.assertEqual(opened_check["result"], "DEGRADED")
            self.assertNotEqual(opened_health["verdict"], "PASS")

    def test_recent_errors_are_sanitized_and_limited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = RecordingRunner("boom API_KEY=abcdef123456 database postgres://anchor:secret@db/anchor\n")
            ctx = _context(root, runner)
            _write(
                ctx.reports_dir / "forward_observation.json",
                {
                    "generated_at": "2026-09-29T00:00:00Z",
                    "result": "FAIL",
                    "errors": ["token=another-secret-value"],
                },
            )
            payload = call_tool("get_recent_errors", {"limit": 5}, ctx)
            blob = json.dumps(payload)
            self.assertIn("[REDACTED]", blob)
            self.assertIn("[REDACTED_URL]", blob)
            self.assertNotIn("abcdef123456", blob)
            self.assertNotIn("another-secret-value", blob)
            self.assertNotIn("postgres://", blob)
            with self.assertRaises(ValueError):
                call_tool("get_recent_errors", {"limit": 0}, ctx)
            with self.assertRaises(ValueError):
                call_tool("get_anchor_status", {"unit": "nginx.service"}, ctx)

    def test_symlink_and_env_paths_are_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = _context(root, RecordingRunner())
            secret = root / "production.env"
            secret.write_text("API_KEY=supersecretvalue\n", encoding="utf-8")
            link = ctx.reports_dir / "official_fake_fill_ledger.json"
            link.symlink_to(secret)
            payload = call_tool("get_ledger_summary", {}, ctx)
            self.assertFalse(payload["available"])
            self.assertNotIn("supersecretvalue", json.dumps(payload))

    def test_repo_report_projection_drops_order_and_credential_fields(self) -> None:
        ctx = ToolContext(
            reports_dir=REPO / "reports",
            repo_root=REPO,
            env={},
            run_command=RecordingRunner(),
            kill_switch=lambda: {"enabled": False, "source": "redis", "state": "CLOSED", "reason": "redis_read"},
            clock=lambda: "2026-09-29T00:00:00Z",
        )
        ledger = call_tool("get_ledger_summary", {}, ctx)
        observation = call_tool("get_latest_observation", {}, ctx)
        blob = json.dumps({"ledger": ledger, "observation": observation})
        self.assertEqual(ledger["kind"], "official_fake_fill")
        self.assertEqual(observation["observation_class"], "forward")
        self.assertNotIn("external_order_id", blob)
        self.assertNotIn("production.env", blob)
        self.assertNotIn("idempotency", blob.lower())
        self.assertNotIn("45.76.190.109", blob)
        self.assertNotIn("TELEGRAM", blob)


class CommandGuardTests(unittest.TestCase):
    def test_only_allowlisted_readonly_argv_runs(self) -> None:
        unit = "project-anchor-post-production-monitoring.service"
        show = systemctl_show_argv(unit)
        self.assertEqual(show[0], "systemctl")
        self.assertEqual(show[1], "show")
        journal = journalctl_err_argv(unit, 20)
        self.assertEqual(journal[0], "journalctl")
        rejected = [
            ["ssh", "root@host"],
            ["bash", "-c", "id"],
            ["systemctl", "start", unit],
            ["systemctl", "stop", unit],
            ["systemctl", "show", unit + ";id", "--no-pager", show[4]],
            ["journalctl", "-u", unit, "-p", "err", "-n", "20", "--no-pager", "--output=json"],
            ["systemctl", "show", unit, "--no-pager", "--property=FragmentPath"],
        ]
        for argv in rejected:
            result = run_readonly_command(argv, timeout=1)
            self.assertFalse(result.ok)
            self.assertEqual(result.stderr, "command_rejected")
            self.assertEqual(result.stdout, "")


class ProtocolTests(unittest.TestCase):
    def _env(self) -> dict[str, str]:
        return {TOKEN_ENV: TOKEN}

    def _post(self, payload: dict | str | None, headers: dict | None = None, env: dict | None = None, query: str = "", context: ToolContext | None = None):
        merged = {"authorization": f"Bearer {TOKEN}", "host": "ops.example.com", "accept": "application/json"}
        if headers:
            merged.update(headers)
        if payload is None:
            body = b""
        elif isinstance(payload, str):
            body = payload.encode("utf-8")
        else:
            body = json.dumps(payload).encode("utf-8")
        return dispatch_http("POST", merged, body, query_string=query, env=env if env is not None else self._env(), context=context)

    def test_fail_closed_without_token(self) -> None:
        result = self._post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, env={})
        self.assertEqual(result.status, 503)
        self.assertIn(TOKEN_ENV, result.body.decode("utf-8"))

    def test_auth_and_query_token_rejection(self) -> None:
        missing = self._post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"authorization": ""})
        self.assertEqual(missing.status, 401)
        wrong = self._post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"authorization": "Bearer nope"})
        self.assertEqual(wrong.status, 401)
        leaked = self._post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, query=f"token={TOKEN}")
        self.assertEqual(leaked.status, 400)
        self.assertNotIn(TOKEN, leaked.body.decode("utf-8"))

    def test_origin_must_match_host_unless_allowlisted(self) -> None:
        bad = self._post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"origin": "https://evil.example"})
        self.assertEqual(bad.status, 403)
        good = self._post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"origin": "https://ops.example.com"})
        self.assertEqual(good.status, 200)
        allowed = self._post(
            {"jsonrpc": "2.0", "id": 1, "method": "ping"},
            headers={"origin": "https://grok.example"},
            env={TOKEN_ENV: TOKEN, "ANCHOR_CONTROL_MCP_ALLOWED_ORIGINS": "https://grok.example"},
        )
        self.assertEqual(allowed.status, 200)

    def test_initialize_lists_only_seven_tools_and_rejects_other_methods(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _context(Path(tmp), RecordingRunner())
            init = self._post(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
                context=ctx,
            )
            body = json.loads(init.body)
            self.assertEqual(body["result"]["protocolVersion"], "2025-03-26")
            self.assertEqual(body["result"]["serverInfo"]["name"], "anchor-control-mcp")
            listed = self._post({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, context=ctx)
            tools = json.loads(listed.body)["result"]["tools"]
            self.assertEqual([tool["name"] for tool in tools], list(TOOL_NAMES))
            for forbidden in ("ssh", "shell", "start_service", "read_file", "place_order"):
                denied = self._post(
                    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": forbidden, "arguments": {}}},
                    context=ctx,
                )
                self.assertEqual(json.loads(denied.body)["error"]["code"], -32602)
            method = self._post({"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {}}, context=ctx)
            self.assertEqual(json.loads(method.body)["error"]["code"], -32601)
            note = dispatch_http(
                "POST",
                {"authorization": f"Bearer {TOKEN}", "host": "ops.example.com"},
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode("utf-8"),
                env=self._env(),
                context=ctx,
            )
            self.assertEqual(note.status, 202)
            self.assertIsNone(note.body)

    def test_tools_call_and_sse_and_disabled_verbs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = _context(root, RecordingRunner())
            _write(
                ctx.reports_dir / "forward_observation.json",
                {"generated_at": "2026-09-29T00:00:00Z", "result": "PASS", "boundary": {"go_live": "NO-GO", "live_trading": "NO-GO"}},
            )
            _write(
                ctx.reports_dir / "official_fake_fill_ledger.json",
                {"generated_at": "2026-09-29T00:00:00Z", "result": "PASS", "fake_transport_external_status": "FILLED", "boundary": {"go_live": "NO-GO", "live_trading": "NO-GO", "production_request_sent": "NO"}},
            )
            called = self._post(
                {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "get_anchor_status", "arguments": {}}},
                context=ctx,
            )
            result = json.loads(called.body)["result"]
            self.assertFalse(result["isError"])
            structured = result["structuredContent"]
            self.assertEqual(structured["tool"], "get_anchor_status")
            self.assertNotIn(TOKEN, called.body.decode("utf-8"))
            sse = self._post(
                {"jsonrpc": "2.0", "id": 8, "method": "ping"},
                headers={"accept": "text/event-stream"},
                context=ctx,
            )
            self.assertEqual(sse.headers["content-type"], "text/event-stream")
            self.assertTrue(sse.body.startswith(b"event: message\ndata: "))
            get_result = dispatch_http("GET", {"authorization": f"Bearer {TOKEN}", "host": "ops.example.com"}, b"", env=self._env())
            self.assertEqual(get_result.status, 405)
            self.assertIn("POST", get_result.headers["allow"])
            deleted = dispatch_http("DELETE", {"authorization": f"Bearer {TOKEN}", "host": "ops.example.com"}, b"", env=self._env())
            self.assertEqual(deleted.status, 204)

    def test_nginx_example_documents_mcp_route_without_claiming_it_is_live(self) -> None:
        example = (REPO / "anchor-backend" / "docs" / "nginx" / "anchor-control-mcp.location.example.conf").read_text(encoding="utf-8")
        self.assertIn("location = /mcp", example)
        self.assertIn("proxy_pass http://127.0.0.1:8001/mcp;", example)
        self.assertNotIn("proxy_pass http://127.0.0.1:8000/mcp;", example)
        self.assertIn("127.0.0.1:8000", example)
        self.assertIn("EXAMPLE ONLY", example)
        self.assertNotIn("ssl_certificate_key", example)
        doc = (REPO / "anchor-backend" / "docs" / "ANCHOR_CONTROL_MCP_V1.md").read_text(encoding="utf-8")
        self.assertIn(TOKEN_ENV, doc)
        self.assertIn(ENDPOINT_PATH, doc)
        for name in TOOL_NAMES:
            self.assertIn(name, doc)


class RouterMountTests(unittest.TestCase):
    def test_fastapi_route_is_mcp(self) -> None:
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            from app.mcp.router import router
        except Exception as exc:  # pragma: no cover - environment without FastAPI
            self.skipTest(f"fastapi test client unavailable: {exc}")
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        previous = os.environ.get(TOKEN_ENV)
        os.environ.pop(TOKEN_ENV, None)
        try:
            denied = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
            self.assertEqual(denied.status_code, 503)
            os.environ[TOKEN_ENV] = TOKEN
            allowed = client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
        finally:
            if previous is None:
                os.environ.pop(TOKEN_ENV, None)
            else:
                os.environ[TOKEN_ENV] = previous
        self.assertEqual(allowed.status_code, 200)
        names = [tool["name"] for tool in allowed.json()["result"]["tools"]]
        self.assertEqual(names, list(TOOL_NAMES))


class KillSwitchReadTests(unittest.TestCase):
    def test_env_flag_does_not_open_redis(self) -> None:
        from app.mcp.status import read_kill_switch

        previous_flag = os.environ.get("ANCHOR_KILL_SWITCH")
        previous_url = os.environ.get("REDIS_URL")
        os.environ["ANCHOR_KILL_SWITCH"] = "1"
        os.environ["REDIS_URL"] = "redis://secret-user:secret-pass@127.0.0.1:1/0"
        try:
            opened = read_kill_switch()
            self.assertEqual(opened["state"], "OPEN")
            self.assertIs(opened["enabled"], True)
            self.assertEqual(opened["source"], "env")
            self.assertNotIn("secret-pass", json.dumps(opened))
            os.environ.pop("ANCHOR_KILL_SWITCH", None)
            os.environ.pop("REDIS_URL", None)
            unread = read_kill_switch()
            self.assertEqual(unread["state"], "UNKNOWN")
            self.assertIsNone(unread["enabled"])
            self.assertNotEqual(unread["state"], "CLOSED")
            os.environ["REDIS_URL"] = "redis://secret-user:secret-pass@127.0.0.1:1/0"
            failed = read_kill_switch()
            self.assertEqual(failed["state"], "UNKNOWN")
            self.assertIsNone(failed["enabled"])
            self.assertNotIn("secret-pass", json.dumps(failed))
            self.assertNotIn("secret-user", json.dumps(failed))
        finally:
            if previous_flag is None:
                os.environ.pop("ANCHOR_KILL_SWITCH", None)
            else:
                os.environ["ANCHOR_KILL_SWITCH"] = previous_flag
            if previous_url is None:
                os.environ.pop("REDIS_URL", None)
            else:
                os.environ["REDIS_URL"] = previous_url


class SanitizeTests(unittest.TestCase):
    def test_redact_text_covers_common_secret_shapes(self) -> None:
        text = redact_text("API_KEY=abc123 Bearer super-token postgresql://u:p@h/db sk-abcdefghijklmnopqrstuvwxyz")
        self.assertNotIn("abc123", text)
        self.assertNotIn("super-token", text)
        self.assertNotIn("postgresql://", text)
        self.assertNotIn("sk-", text)
