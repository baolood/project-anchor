"""Offline closeout-wrapper boundaries; synthetic reports, no strategy/network calls."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import closeout_loop as loop


BASE = datetime(2026, 10, 9, 7, tzinfo=timezone.utc)
START = datetime(2026, 10, 12, 1, tzinfo=timezone.utc)
DEADLINE = START + timedelta(days=7)
RUN_ID = "anchor-d5-closeout-20261012"
PAIRS = (
    "breakout_55|PI_ETHUSD", "breakout_55|PI_XBTUSD",
    "breakout_55_strength_1pct|PI_ETHUSD", "ema_50_100_strength_1pct|PI_ETHUSD",
)
FLAT_PAIR = "ema_50_100_strength_1pct|PI_XBTUSD"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def initial_positions():
    return {pair: {"instruction_id": f"{100 + i:032x}", "side": -1,
                   "entry_time": (BASE + timedelta(hours=1)).isoformat(),
                   "entry_price": 100.0 + i, "stop": (100.0 + i) * 1.01,
                   "target": (100.0 + i) * .985, "fees": .4}
            for i, pair in enumerate(PAIRS)}


def sim_path(generation):
    return generation / loop.REPORTS / "sim-state-v1.json"


def append_round(generation, index, started):
    reports = generation / loop.REPORTS
    reports.mkdir(parents=True, exist_ok=True)
    rid = f"{index:032x}"
    stamp = lambda seconds: (started + timedelta(seconds=seconds)).isoformat()
    with (generation / loop.LOG).open("a") as handle:
        handle.write(json.dumps({"round_id": rid, "round_index": index, "attempt": 1,
                                 "returncode": 0, "started_at": stamp(0),
                                 "finished_at": stamp(4)}) + "\n")
    state = loop.read_json(sim_path(generation)) if sim_path(generation).exists() else {
        "version": "FILL_RULE_AVAILABILITY_T3_STRICT_OPEN_V1",
        "applied_rounds": {}, "position": initial_positions(), "trades": {},
        "pending": {pair: [] for pair in (*PAIRS, FLAT_PAIR)},
        "cursor_seconds": {pair: BASE.timestamp() for pair in (*PAIRS, FLAT_PAIR)},
        "last_observed_signal": {pair: -1 for pair in PAIRS}, "log": [],
    }
    state["applied_rounds"][rid] = f"advance-{index}"
    write_json(sim_path(generation), state)
    write_json(reports / "rounds" / f"round.{rid}.json", {
        "round_id": rid, "round_status": "SUCCESS_NO_SIGNAL",
        "computation_completed_at": stamp(1), "published_at": stamp(2),
        "simulation_v1": {"b_write_status": "OK", "advance_applied": True,
                          "b_published_at": stamp(3)}})
    write_json(reports / "forward-observation-latest.json", {"round_id": rid})
    write_json(reports / "sim-availability-v1-latest.json", {
        "round_id": rid, "source_round_t3": stamp(2)})
    return rid


def close_position(state, pair, at=START):
    pos = state["position"][pair]
    state["trades"].setdefault(pair, []).append({
        "entry_instruction_id": pos["instruction_id"], "exit_instruction_id": None,
        "side": pos["side"], "entry_time": pos["entry_time"],
        "entry_price": pos["entry_price"], "exit_time": at.isoformat(),
        "exit_price": pos["entry_price"], "exit_reason": "STOP", "labels": [],
        "fees": .8, "pnl": -.8,
    })
    state["position"][pair] = None


class CloseoutLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.initial = self.root / "checkpoints/initial"
        self.clock = START
        scripts = self.root / "bundle/scripts"
        scripts.mkdir(parents=True)
        for name in ["run_forward_round_v1.py"] + [f"dummy_{n}.py" for n in range(5)]:
            (scripts / name).write_text("# Synthetic source, never execute.\n")
        # The module never needs a socket in these tests. Fail visibly if this changes.
        self.no_network = patch("socket.socket", side_effect=AssertionError("network forbidden"))
        self.no_network.start()
        self.addCleanup(self.no_network.stop)

    def tearDown(self):
        self.temp.cleanup()

    def bootstrap(self):
        ids = [append_round(self.initial, i, BASE + timedelta(hours=4 * (i - 1)))
               for i in range(1, 13)]
        state = loop.read_json(sim_path(self.initial))
        contract = {
            "schema": 1, "mode": "closeout_only", "run_id": RUN_ID,
            "started_at": START.isoformat(), "deadline_utc": DEADLINE.isoformat(),
            "baseline_completed_rounds": 12, "max_additional_rounds": 43,
            "baseline_last_t3": (BASE + timedelta(hours=44, seconds=2)).isoformat(),
            "allowed_positions": copy.deepcopy(state["position"]),
            "baseline_cursor_seconds": copy.deepcopy(state["cursor_seconds"]),
        }
        write_json(self.root / "closeout-contract.json", contract)
        hashes = loop.report_hashes(self.initial)
        write_json(self.root / "manifest.json", {
            "schema": 1,
            "code_sha256": {p.name: loop.sha256(p) for p in (self.root / "bundle/scripts").iterdir()},
            "initial_round_ids": ids, "initial_report_sha256": hashes,
            "closeout_contract_sha256": loop.sha256(self.root / "closeout-contract.json"),
        })
        write_json(self.root / "control.json", {
            "schema": 1, "current_rel": "checkpoints/initial", "slots_consumed": 12,
            "completed_rounds": 12, "status": "waiting", "inflight": None,
            "report_sha256": hashes, "next_due": START.isoformat(),
            "run_id": RUN_ID, "started_at": START.isoformat(),
            "deadline_utc": DEADLINE.isoformat(),
        })

    def control(self):
        return loop.read_json(self.root / "control.json")

    def current_state(self):
        return loop.read_json(sim_path(self.root / self.control()["current_rel"]))

    def step(self, runner):
        with loop.exclusive_lock(self.root):
            return loop.run_due_once(self.root, runner=runner, clock=lambda: self.clock)

    def good_runner(self, stage, index):
        control = self.control()
        self.assertEqual(control["slots_consumed"], index)
        self.assertEqual(control["inflight"]["round_index"], index)
        self.assertEqual(control["completed_rounds"], index - 1)
        append_round(stage, index, self.clock)
        return 0

    def close_runner(self, pairs):
        def run(stage, index):
            self.good_runner(stage, index)
            state = loop.read_json(sim_path(stage))
            for pair in pairs:
                close_position(state, pair, self.clock)
            write_json(sim_path(stage), state)
            return 0
        return run

    def next_round(self):
        self.clock = loop.timestamp(self.control()["next_due"])

    def test_initial_twelve_advances_once_without_changing_baseline_or_contract(self):
        self.bootstrap()
        baseline = loop.report_hashes(self.initial)
        contract = (self.root / "closeout-contract.json").read_bytes()
        runner = Mock(side_effect=self.good_runner)
        self.assertEqual(self.step(runner), "waiting")
        self.assertEqual(self.control()["completed_rounds"], 13)
        self.assertEqual(self.control()["current_rel"], "runs/round-013")
        self.assertIsNone(self.control()["inflight"])
        self.assertEqual(self.control()["next_due"], (START + timedelta(seconds=14404)).isoformat())
        self.assertEqual(self.current_state()["position"], initial_positions())
        self.assertEqual(loop.report_hashes(self.initial), baseline)
        self.assertEqual((self.root / "closeout-contract.json").read_bytes(), contract)
        self.assertEqual(self.step(runner), "waiting")
        self.assertEqual(runner.call_count, 1)
        loop.validate(self.root)

    def test_fixed_deadline_and_run_identity_survive_restart(self):
        self.bootstrap()
        self.step(self.good_runner)
        # Reloading persisted state models a new wrapper process; no start-time rewrite.
        loop.validate(self.root)
        self.next_round()
        self.step(self.good_runner)
        self.assertEqual(self.control()["deadline_utc"], DEADLINE.isoformat())
        self.assertEqual(self.control()["started_at"], START.isoformat())
        self.assertEqual(self.control()["run_id"], RUN_ID)
        contract = loop.read_json(self.root / "closeout-contract.json")
        self.assertEqual(loop.timestamp(contract["deadline_utc"]) -
                         loop.timestamp(contract["started_at"]), timedelta(days=7))

    def test_all_flat_stops_without_any_further_execution(self):
        self.bootstrap()
        self.assertEqual(self.step(self.close_runner(PAIRS)), "complete")
        self.assertEqual(self.control()["stop_reason"], "all_flat")
        self.assertIsNone(self.control()["next_due"])
        runner = Mock()
        self.assertEqual(self.step(runner), "complete")
        runner.assert_not_called()
        self.assertEqual(sum(p is not None for p in self.current_state()["position"].values()), 0)
        summary = loop.read_json(self.root / "closeout-status.json")
        self.assertEqual(summary["stop_reason"], "all_flat")
        self.assertEqual(summary["open_position_count"], 0)
        self.assertEqual(summary["deadline_utc"], DEADLINE.isoformat())

    def test_deadline_stops_preserving_residual_positions_and_fees(self):
        self.bootstrap()
        self.clock = DEADLINE
        runner = Mock()
        before = loop.report_hashes(self.initial)
        self.assertEqual(self.step(runner), "complete")
        runner.assert_not_called()
        self.assertEqual(self.control()["stop_reason"], "deadline")
        self.assertEqual(self.control()["completed_rounds"], 12)
        self.assertEqual(self.current_state()["position"], initial_positions())
        self.assertEqual(self.current_state()["trades"], {})
        self.assertEqual(loop.report_hashes(self.initial), before)
        summary = loop.read_json(self.root / "closeout-status.json")
        self.assertEqual(summary["open_position_count"], 4)
        self.assertEqual(summary["deadline_utc"], DEADLINE.isoformat())

    def test_deadline_guard_waits_until_deadline_without_child_or_slot(self):
        self.bootstrap()
        self.clock = DEADLINE - timedelta(seconds=180)
        runner = Mock()
        self.assertEqual(self.step(runner), "waiting")
        runner.assert_not_called()
        self.assertEqual(self.control()["next_due"], DEADLINE.isoformat())
        self.assertEqual(self.control()["completed_rounds"], 12)
        self.assertNotEqual(self.control()["status"], "complete")
        self.clock = DEADLINE
        self.assertEqual(self.step(runner), "complete")
        self.assertEqual(self.control()["stop_reason"], "deadline")
        runner.assert_not_called()

    def test_cap_at_fifty_five_never_launches_a_fifty_sixth_round(self):
        self.bootstrap()
        # Synthetic compressed history isolates the count fuse from the time fuse.
        # It does not claim 43 additional rounds fit a seven-day four-hour cadence.
        import shutil
        generation = self.root / "runs/round-055"
        shutil.copytree(self.initial, generation)
        for index in range(13, 56):
            append_round(generation, index, START + timedelta(minutes=index - 13))
        control = self.control()
        control.update(current_rel="runs/round-055", completed_rounds=55,
                       slots_consumed=55, report_sha256=loop.report_hashes(generation),
                       next_due=(START + timedelta(hours=5)).isoformat())
        write_json(self.root / "control.json", control)
        self.clock = START + timedelta(hours=5)
        runner = Mock()
        self.assertEqual(self.step(runner), "complete")
        runner.assert_not_called()
        self.assertEqual(self.control()["stop_reason"], "round_limit")
        self.assertIsNone(self.control()["next_due"])

    def test_new_position_or_instruction_or_changed_original_is_not_published(self):
        for change in ("new_pair", "new_id", "changed_entry", "changed_fee"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                original_root, original_initial = self.root, self.initial
                self.root = Path(folder)
                self.initial = self.root / "checkpoints/initial"
                import shutil
                shutil.copytree(original_root / "bundle", self.root / "bundle")
                self.bootstrap()
                def bad(stage, index):
                    self.good_runner(stage, index)
                    state = loop.read_json(sim_path(stage))
                    if change == "new_pair":
                        state["position"][FLAT_PAIR] = copy.deepcopy(state["position"][PAIRS[0]])
                    elif change == "new_id":
                        state["position"][PAIRS[0]]["instruction_id"] = "f" * 32
                    elif change == "changed_entry":
                        state["position"][PAIRS[0]]["entry_price"] += 1
                    else:
                        state["position"][PAIRS[0]]["fees"] += .4
                    write_json(sim_path(stage), state)
                    return 0
                with self.assertRaises(loop.Refuse):
                    self.step(bad)
                self.assertEqual(self.control()["current_rel"], "checkpoints/initial")
                self.assertEqual(self.control()["status"], "failed")
                self.root, self.initial = original_root, original_initial

    def test_previously_closed_original_instruction_cannot_reopen(self):
        self.bootstrap()
        self.step(self.close_runner([PAIRS[0]]))
        self.next_round()
        def resurrect(stage, index):
            self.good_runner(stage, index)
            state = loop.read_json(sim_path(stage))
            state["position"][PAIRS[0]] = initial_positions()[PAIRS[0]]
            write_json(sim_path(stage), state)
            return 0
        with self.assertRaises(loop.Refuse):
            self.step(resurrect)
        self.assertEqual(self.control()["current_rel"], "runs/round-013")
        self.assertIsNone(self.current_state()["position"][PAIRS[0]])

    def test_historical_trade_cannot_be_removed_or_changed(self):
        self.bootstrap()
        self.step(self.close_runner([PAIRS[0]]))
        before = copy.deepcopy(self.current_state()["trades"])
        self.next_round()
        def rewrite(stage, index):
            self.good_runner(stage, index)
            state = loop.read_json(sim_path(stage))
            state["trades"][PAIRS[0]][0]["pnl"] += 100
            write_json(sim_path(stage), state)
            return 0
        with self.assertRaises(loop.Refuse):
            self.step(rewrite)
        self.assertEqual(self.current_state()["trades"], before)

    def test_disappearing_position_without_bound_closed_trade_is_refused(self):
        self.bootstrap()
        def disappear(stage, index):
            self.good_runner(stage, index)
            state = loop.read_json(sim_path(stage))
            state["position"][PAIRS[0]] = None
            write_json(sim_path(stage), state)
            return 0
        with self.assertRaises(loop.Refuse):
            self.step(disappear)
        self.assertEqual(self.control()["current_rel"], "checkpoints/initial")

    def test_enter_instruction_is_refused_even_without_an_open_leg(self):
        self.bootstrap()
        def enter(stage, index):
            self.good_runner(stage, index)
            state = loop.read_json(sim_path(stage))
            state["pending"][PAIRS[0]] = [{"kind": "ENTER", "side": 1,
                                            "instruction_id": "e" * 32,
                                            "t3": self.clock.isoformat()}]
            write_json(sim_path(stage), state)
            return 0
        with self.assertRaises(loop.Refuse):
            self.step(enter)
        self.assertEqual(self.control()["current_rel"], "checkpoints/initial")

    def test_cursor_cannot_regress_from_latest_commit_even_above_baseline(self):
        self.bootstrap()
        def advance(stage, index):
            self.good_runner(stage, index)
            state = loop.read_json(sim_path(stage))
            state["cursor_seconds"][PAIRS[0]] += 28800
            write_json(sim_path(stage), state)
            return 0
        self.step(advance)
        previous = self.current_state()["cursor_seconds"][PAIRS[0]]
        self.next_round()
        def regress(stage, index):
            self.good_runner(stage, index)
            state = loop.read_json(sim_path(stage))
            state["cursor_seconds"][PAIRS[0]] -= 14400
            write_json(sim_path(stage), state)
            return 0
        with self.assertRaises(loop.Refuse):
            self.step(regress)
        self.assertEqual(self.control()["current_rel"], "runs/round-013")
        self.assertEqual(self.current_state()["cursor_seconds"][PAIRS[0]], previous)

    def test_contract_tamper_refused_before_reservation(self):
        self.bootstrap()
        path = self.root / "closeout-contract.json"
        contract = loop.read_json(path)
        contract["deadline_utc"] = (DEADLINE + timedelta(days=1)).isoformat()
        write_json(path, contract)
        runner = Mock()
        with self.assertRaises(loop.Refuse):
            self.step(runner)
        runner.assert_not_called()
        self.assertEqual(self.control()["slots_consumed"], 12)

    def test_control_cannot_reset_deadline(self):
        self.bootstrap()
        control = self.control()
        control["deadline_utc"] = (DEADLINE + timedelta(days=1)).isoformat()
        write_json(self.root / "control.json", control)
        runner = Mock()
        with self.assertRaises(loop.Refuse):
            self.step(runner)
        runner.assert_not_called()

    def test_crash_after_reservation_never_replays_or_falls_back(self):
        self.bootstrap()
        with self.assertRaises(KeyboardInterrupt):
            self.step(Mock(side_effect=KeyboardInterrupt()))
        self.assertEqual(self.control()["slots_consumed"], 13)
        self.assertEqual(self.control()["completed_rounds"], 12)
        self.assertIsNotNone(self.control()["inflight"])
        later = Mock()
        with self.assertRaises(loop.Refuse):
            self.step(later)
        later.assert_not_called()

    def test_nonzero_exit_retains_failed_stage_and_prior_checkpoint(self):
        self.bootstrap()
        before = loop.report_hashes(self.initial)
        def partial(stage, _index):
            sim_path(stage).write_text("broken partial write")
            return 4
        with self.assertRaises(loop.Refuse):
            self.step(partial)
        self.assertEqual(self.control()["current_rel"], "checkpoints/initial")
        self.assertEqual(loop.report_hashes(self.initial), before)
        self.assertTrue((self.root / "runs/round-013").is_dir())
        self.assertEqual(self.control()["status"], "failed")

    def test_commit_write_failure_preserves_reservation_and_never_reexecutes(self):
        self.bootstrap()
        atomic = loop.atomic_json
        rejected = False
        def fail_commit(path, value):
            nonlocal rejected
            if (not rejected and path == self.root / "control.json"
                    and value.get("completed_rounds") == 13 and value.get("inflight") is None):
                rejected = True
                raise OSError("synthetic control commit failure")
            return atomic(path, value)
        with patch.object(loop, "atomic_json", side_effect=fail_commit):
            with self.assertRaises(OSError):
                self.step(self.good_runner)
        self.assertEqual(self.control()["current_rel"], "checkpoints/initial")
        self.assertEqual(self.control()["slots_consumed"], 13)
        self.assertEqual(self.control()["completed_rounds"], 12)
        self.assertIsNotNone(self.control()["inflight"])
        self.assertTrue((self.root / "runs/round-013").is_dir())
        later = Mock()
        with self.assertRaises(loop.Refuse):
            self.step(later)
        later.assert_not_called()

    def test_uncertain_error_after_commit_cannot_publish_same_round_twice(self):
        self.bootstrap()
        atomic = loop.atomic_json
        failed = False
        def fail_after_commit(path, value):
            nonlocal failed
            result = atomic(path, value)
            if (not failed and path == self.root / "control.json"
                    and value.get("completed_rounds") == 13 and value.get("inflight") is None):
                failed = True
                raise OSError("synthetic error after durable commit")
            return result
        with patch.object(loop, "atomic_json", side_effect=fail_after_commit):
            with self.assertRaises(OSError):
                self.step(self.good_runner)
        self.assertEqual(self.control()["completed_rounds"], 13)
        self.assertIsNone(self.control()["inflight"])
        later = Mock()
        self.assertEqual(self.step(later), "waiting")
        later.assert_not_called()
        self.assertEqual(len(loop.read_rounds(self.root / "runs/round-013")[2]), 13)

    def test_success_without_bound_round_record_is_not_published(self):
        self.bootstrap()
        def incomplete(stage, index):
            self.good_runner(stage, index)
            (stage / loop.REPORTS / "rounds" / f"round.{index:032x}.json").unlink()
            return 0
        with self.assertRaises(loop.Refuse):
            self.step(incomplete)
        self.assertEqual(self.control()["current_rel"], "checkpoints/initial")

    def test_appending_two_rounds_is_not_published(self):
        self.bootstrap()
        def duplicate(stage, index):
            self.good_runner(stage, index)
            append_round(stage, index + 1, self.clock + timedelta(seconds=5))
            return 0
        with self.assertRaises(loop.Refuse):
            self.step(duplicate)
        self.assertEqual(self.control()["completed_rounds"], 12)

    def test_historical_t3_bytes_cannot_change(self):
        self.bootstrap()
        def rewrite(stage, index):
            self.good_runner(stage, index)
            path = stage / loop.REPORTS / "rounds" / f"round.{1:032x}.json"
            path.write_bytes(path.read_bytes() + b"\n")
            return 0
        with self.assertRaises(loop.Refuse):
            self.step(rewrite)
        self.assertEqual(self.control()["current_rel"], "checkpoints/initial")

    def test_tampered_source_refused_before_reservation(self):
        self.bootstrap()
        (self.root / "bundle/scripts/dummy_1.py").write_text("changed")
        runner = Mock()
        with self.assertRaises(loop.Refuse):
            self.step(runner)
        runner.assert_not_called()
        self.assertEqual(self.control()["slots_consumed"], 12)

    def test_stale_stage_is_never_reused(self):
        self.bootstrap()
        (self.root / "runs/round-013").mkdir(parents=True)
        runner = Mock()
        with self.assertRaises(loop.Refuse):
            self.step(runner)
        runner.assert_not_called()
        self.assertEqual(self.control()["slots_consumed"], 12)

    def test_exclusive_lock_rejects_independent_process(self):
        self.bootstrap()
        code = "\n".join([
            "import fcntl, sys", "from pathlib import Path",
            "with (Path(sys.argv[1]) / 'loop.lock').open('a+') as h:",
            "    try: fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)",
            "    except BlockingIOError: sys.exit(0)", "    sys.exit(9)",
        ])
        with loop.exclusive_lock(self.root):
            result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(self.root)],
                                    capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        with loop.exclusive_lock(self.root):
            pass

    def test_child_environment_and_timeout_target_only_own_group(self):
        self.bootstrap()
        stage = self.root / "fake-child"
        stage.mkdir()
        child = Mock(pid=12345)
        child.wait.side_effect = [subprocess.TimeoutExpired("fake", 180), 0]
        child.poll.return_value = None
        with patch.object(loop.subprocess, "Popen", return_value=child) as spawn, \
                patch.object(loop.os, "killpg", side_effect=[None, ProcessLookupError()]) as kill, \
                patch.dict(os.environ, {"FAKE_CREDENTIAL": "must-not-pass"}):
            with self.assertRaises(subprocess.TimeoutExpired):
                loop.run_child(stage, 13)
        command, kwargs = spawn.call_args.args[0], spawn.call_args.kwargs
        self.assertEqual(kwargs["env"], loop.MINIMAL_ENV)
        self.assertNotIn("FAKE_CREDENTIAL", kwargs["env"])
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(command[command.index("--round-index") + 1], "13")
        self.assertEqual(command[command.index("--max-attempts") + 1], "1")
        self.assertEqual(kill.call_args_list, [unittest.mock.call(12345, loop.signal.SIGTERM),
                                             unittest.mock.call(12345, 0)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
