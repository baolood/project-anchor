"""Offline safety tests. Synthetic files and a fake runner; no strategy imports."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "cloud-package"))
import cloud_loop as loop


BASE = datetime(2026, 10, 9, 7, tzinfo=timezone.utc)
CLOCK = datetime(2026, 10, 13, 0, tzinfo=timezone.utc)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def append_round(generation, index, started):
    reports = generation / loop.REPORTS
    reports.mkdir(parents=True, exist_ok=True)
    rid = f"{index:032x}"
    stamp = lambda seconds: (started + timedelta(seconds=seconds)).isoformat()
    entry = {"round_id": rid, "round_index": index, "attempt": 1,
             "returncode": 0, "started_at": stamp(0), "finished_at": stamp(4)}
    with (generation / loop.LOG).open("a") as handle:
        handle.write(json.dumps(entry) + "\n")
    sim_path = reports / "sim-state-v1.json"
    sim = loop.read_json(sim_path) if sim_path.exists() else {
        "applied_rounds": {}, "positions": {"retained": {"commission": 0.8}},
        "instructions": {"historical": {"t3": BASE.isoformat()}}}
    sim["applied_rounds"][rid] = f"advance-{index}"
    write_json(sim_path, sim)
    write_json(reports / "rounds" / f"round.{rid}.json", {
        "round_id": rid, "round_status": "SUCCESS_NO_SIGNAL",
        "computation_completed_at": stamp(1), "published_at": stamp(2),
        "simulation_v1": {"b_write_status": "OK", "advance_applied": True,
                          "b_published_at": stamp(3)}})
    write_json(reports / "forward-observation-latest.json", {"round_id": rid})
    write_json(reports / "sim-availability-v1-latest.json", {
        "round_id": rid, "source_round_t3": stamp(2)})
    return rid


class CloudLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.initial = self.root / "checkpoints/initial"
        scripts = self.root / "bundle/scripts"
        scripts.mkdir(parents=True)
        for name in ["run_forward_round_v1.py"] + [f"dummy_{n}.py" for n in range(5)]:
            (scripts / name).write_text("# synthetic source; never execute\n")

    def tearDown(self):
        self.temp.cleanup()

    def bootstrap(self, count=3):
        ids = [append_round(self.initial, i, BASE + timedelta(hours=4 * (i - 1)))
               for i in range(1, count + 1)]
        hashes = loop.report_hashes(self.initial)
        write_json(self.root / "manifest.json", {
            "schema": 1, "code_sha256": {p.name: loop.sha256(p)
                                         for p in (self.root / "bundle/scripts").iterdir()},
            "initial_round_ids": ids, "initial_report_sha256": hashes})
        write_json(self.root / "control.json", {
            "schema": 1, "current_rel": "checkpoints/initial", "slots_consumed": count,
            "completed_rounds": count, "status": "waiting", "inflight": None,
            "report_sha256": hashes, "next_due": CLOCK.isoformat()})

    def step(self, runner):
        with loop.exclusive_lock(self.root):
            return loop.run_due_once(self.root, runner=runner, clock=lambda: CLOCK)

    def control(self):
        return loop.read_json(self.root / "control.json")

    def good_runner(self, stage, index):
        # The durable reservation must precede any source execution.
        control = self.control()
        self.assertEqual(control["slots_consumed"], index)
        self.assertEqual(control["inflight"]["round_index"], index)
        self.assertEqual(control["completed_rounds"], index - 1)
        append_round(stage, index, CLOCK)
        return 0

    def test_success_continues_actual_count_once_preserves_state_and_history(self):
        self.bootstrap(count=2)
        before = loop.report_hashes(self.initial)
        runner = Mock(side_effect=self.good_runner)
        self.assertEqual(self.step(runner), "waiting")
        self.assertEqual(runner.call_count, 1)
        control = self.control()
        self.assertEqual(control["completed_rounds"], 3)
        self.assertEqual(control["current_rel"], "runs/round-003")
        self.assertIsNone(control["inflight"])
        self.assertEqual(control["next_due"], (CLOCK + timedelta(seconds=14404)).isoformat())
        self.assertEqual(loop.report_hashes(self.initial), before)
        sim = loop.read_json(self.root / control["current_rel"] / loop.REPORTS / "sim-state-v1.json")
        self.assertEqual(sim["positions"]["retained"]["commission"], 0.8)
        self.assertEqual(sim["instructions"]["historical"]["t3"], BASE.isoformat())
        self.assertEqual(self.step(runner), "waiting")
        self.assertEqual(runner.call_count, 1)
        loop.validate(self.root)

    def test_limit_twelve_no_thirteenth_execution(self):
        self.bootstrap(count=11)
        runner = Mock(side_effect=self.good_runner)
        self.assertEqual(self.step(runner), "complete")
        self.assertEqual(self.step(runner), "complete")
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(self.control()["slots_consumed"], 12)
        self.assertIsNone(self.control()["next_due"])
        self.assertFalse((self.root / "runs/round-013").exists())

    def test_initial_twelve_never_runs(self):
        self.bootstrap(count=12)
        runner = Mock()
        self.assertEqual(self.step(runner), "complete")
        runner.assert_not_called()

    def test_lock_prevents_second_instance(self):
        self.bootstrap()
        with loop.exclusive_lock(self.root):
            with self.assertRaisesRegex(loop.Refuse, "single-instance"):
                with loop.exclusive_lock(self.root):
                    self.fail("second lock acquired")
        with loop.exclusive_lock(self.root):
            pass

    def test_crash_after_reservation_never_replays(self):
        self.bootstrap()
        with self.assertRaises(KeyboardInterrupt):
            self.step(Mock(side_effect=KeyboardInterrupt()))
        self.assertEqual(self.control()["slots_consumed"], 4)
        self.assertEqual(self.control()["completed_rounds"], 3)
        self.assertIsNotNone(self.control()["inflight"])
        later = Mock()
        with self.assertRaisesRegex(loop.Refuse, "automatic replay prohibited"):
            self.step(later)
        later.assert_not_called()

    def test_nonzero_exit_keeps_stage_and_prior_checkpoint(self):
        self.bootstrap()
        original = self.control()["report_sha256"]
        def partial(stage, _index):
            (stage / loop.REPORTS / "sim-state-v1.json").write_text("broken partial write")
            return 4
        with self.assertRaisesRegex(loop.Refuse, "returncode 4"):
            self.step(partial)
        self.assertEqual(self.control()["current_rel"], "checkpoints/initial")
        self.assertEqual(loop.report_hashes(self.initial), original)
        self.assertTrue((self.root / "runs/round-004").is_dir())
        self.assertEqual(self.control()["status"], "failed")

    def test_success_exit_without_bound_round_record_does_not_publish(self):
        self.bootstrap()
        def incomplete(stage, index):
            self.good_runner(stage, index)
            (stage / loop.REPORTS / "rounds" / f"round.{index:032x}.json").unlink()
            return 0
        with self.assertRaisesRegex(loop.Refuse, "record set differs"):
            self.step(incomplete)
        self.assertEqual(self.control()["current_rel"], "checkpoints/initial")

    def test_tampered_source_refused_before_reservation(self):
        self.bootstrap()
        (self.root / "bundle/scripts/dummy_1.py").write_text("changed")
        runner = Mock()
        with self.assertRaisesRegex(loop.Refuse, "hash mismatch"):
            self.step(runner)
        runner.assert_not_called()
        self.assertEqual(self.control()["slots_consumed"], 3)

    def test_rewritten_historical_t3_refuses_publication(self):
        self.bootstrap()
        def rewrite(stage, index):
            self.good_runner(stage, index)
            record = stage / loop.REPORTS / "rounds" / f"round.{1:032x}.json"
            # Harmless whitespace change still proves historical bytes were touched.
            record.write_bytes(record.read_bytes() + b"\n")
            return 0
        with self.assertRaisesRegex(loop.Refuse, "historical round record changed"):
            self.step(rewrite)
        self.assertEqual(self.control()["current_rel"], "checkpoints/initial")

    def test_stale_existing_stage_never_reused(self):
        self.bootstrap()
        (self.root / "runs/round-004").mkdir(parents=True)
        runner = Mock()
        with self.assertRaisesRegex(loop.Refuse, "already exists"):
            self.step(runner)
        runner.assert_not_called()
        self.assertEqual(self.control()["slots_consumed"], 3)

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
                loop.run_child(stage, 4)
        args, kwargs = spawn.call_args
        self.assertEqual(kwargs["env"], loop.MINIMAL_ENV)
        self.assertNotIn("FAKE_CREDENTIAL", kwargs["env"])
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(args[0][-4:], ["--round-index", "4", "--max-attempts", "1"])
        self.assertEqual(kill.call_args_list, [unittest.mock.call(12345, loop.signal.SIGTERM),
                                              unittest.mock.call(12345, 0)])

    def test_timeout_kills_remaining_group_after_leader_has_exited(self):
        child = Mock(pid=12345)
        child.poll.return_value = 0
        child.wait.return_value = 0
        with patch.object(loop.os, "killpg") as kill, \
                patch.object(loop.time, "monotonic", side_effect=[0, 1, 6]), \
                patch.object(loop.time, "sleep"):
            loop.stop_owned_group(child)
        self.assertEqual(kill.call_args_list, [unittest.mock.call(12345, loop.signal.SIGTERM),
                                              unittest.mock.call(12345, 0),
                                              unittest.mock.call(12345, loop.signal.SIGKILL)])

    def test_waiting_signal_logs_nonzero_exit_without_consuming_slot(self):
        self.bootstrap()
        with patch.object(loop.sys, "argv", ["cloud_loop.py", "--root", str(self.root)]), \
                patch.object(loop.signal, "signal"), \
                patch.object(loop, "now", return_value=BASE), \
                patch.object(loop.time, "sleep", side_effect=InterruptedError("synthetic SIGTERM")):
            self.assertEqual(loop.main(), 1)
        self.assertEqual(self.control()["slots_consumed"], 3)
        events = [json.loads(line) for line in (self.root / "events.jsonl").read_text().splitlines()]
        self.assertEqual(events[-1]["event"], "wrapper_exit")
        self.assertEqual(events[-1]["returncode"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
