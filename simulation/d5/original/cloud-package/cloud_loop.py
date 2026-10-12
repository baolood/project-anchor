#!/usr/bin/env python3
"""Bounded, single-instance continuation of the unchanged public dry-run scripts.

control.json is the sole commit pointer. A reserved slot is never replayed,
including after an interrupted process. Failed staging generations are retained.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_TOTAL_ROUNDS = 12
INTERVAL_SECONDS = 14400
CHILD_TIMEOUT_SECONDS = 180
REPORTS = Path("reports/kraken_prop")
LOG = REPORTS / "dry-run-v1.jsonl"
MINIMAL_ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
               "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}


class Refuse(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise Refuse("timestamp lacks timezone")
    return parsed.astimezone(timezone.utc)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path, data):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fsync_directory(path.parent)


def event(root, kind, **fields):
    item = {"at": now().isoformat(), "event": kind, **fields}
    with (root / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(root)


@contextmanager
def exclusive_lock(root):
    with (root / "loop.lock").open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refuse("another wrapper holds the single-instance lock") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def safe_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise Refuse("unsafe relative path")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise Refuse("symlink not allowed in job data")
    return current


def report_hashes(generation):
    directory = safe_path(generation, str(REPORTS))
    if not directory.is_dir():
        raise Refuse("missing reports directory")
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise Refuse("symlink in reports")
        if path.is_file():
            result[str(path.relative_to(generation))] = sha256(path)
    return result


def verify_code(root, manifest, directory=None):
    code = manifest.get("code_sha256", {})
    if len(code) != 6 or "run_forward_round_v1.py" not in code:
        raise Refuse("expected exactly six original Python source files")
    directory = directory or safe_path(root, "bundle/scripts")
    if set(p.name for p in directory.iterdir()) != set(code):
        raise Refuse("source file whitelist differs")
    for name, digest in code.items():
        if not re.fullmatch(r"[A-Za-z0-9_]+\.py", name):
            raise Refuse("invalid source filename")
        path = safe_path(directory, name)
        if not path.is_file() or sha256(path) != digest:
            raise Refuse("source hash mismatch: " + name)


def read_rounds(generation):
    content = safe_path(generation, str(LOG)).read_bytes()
    if content and not content.endswith(b"\n"):
        raise Refuse("incomplete log line")
    entries = [json.loads(line) for line in content.splitlines()]
    ids = []
    for index, item in enumerate(entries, 1):
        rid = item.get("round_id", "")
        if not re.fullmatch(r"[0-9a-f]{32}", rid) or rid in ids:
            raise Refuse("duplicate or invalid round id")
        if item.get("round_index") != index or item.get("returncode") != 0:
            raise Refuse("round log is not contiguous successful history")
        if item.get("attempt") != 1:
            raise Refuse("historical retry requires explicit reconciliation")
        if timestamp(item["started_at"]) > timestamp(item["finished_at"]):
            raise Refuse("invalid round interval")
        ids.append(rid)
    sim = read_json(safe_path(generation, str(REPORTS / "sim-state-v1.json")))
    if set(sim["applied_rounds"]) != set(ids):
        raise Refuse("sim applied rounds do not match successful log")
    records_dir = safe_path(generation, str(REPORTS / "rounds"))
    if {p.name for p in records_dir.iterdir()} != {f"round.{rid}.json" for rid in ids}:
        raise Refuse("round record set differs from log")
    records = {}
    for rid, item in zip(ids, entries):
        rec = read_json(safe_path(records_dir, f"round.{rid}.json"))
        block = rec.get("simulation_v1", {})
        if (rec.get("round_id") != rid or rec.get("round_status") not in
                {"SUCCESS_WITH_SIGNAL", "SUCCESS_NO_SIGNAL"} or
                block.get("b_write_status") != "OK" or block.get("advance_applied") is not True):
            raise Refuse("round record is not bound to a successful simulation")
        if not (timestamp(item["started_at"]) <= timestamp(rec["computation_completed_at"])
                <= timestamp(rec["published_at"]) <= timestamp(block["b_published_at"])
                <= timestamp(item["finished_at"])):
            raise Refuse("round publication timestamps are inconsistent")
        records[rid] = rec
    if ids:
        a = read_json(safe_path(generation, str(REPORTS / "forward-observation-latest.json")))
        b = read_json(safe_path(generation, str(REPORTS / "sim-availability-v1-latest.json")))
        if a.get("round_id") != ids[-1] or b.get("round_id") != ids[-1]:
            raise Refuse("latest artifacts do not match final round")
        if b.get("source_round_t3") != records[ids[-1]]["published_at"]:
            raise Refuse("latest B does not reference recorded T3")
    return content, entries, ids


def validate(root):
    manifest = read_json(safe_path(root, "manifest.json"))
    control = read_json(safe_path(root, "control.json"))
    if manifest.get("schema") != 1 or control.get("schema") != 1:
        raise Refuse("unsupported schema")
    verify_code(root, manifest)
    initial = safe_path(root, "checkpoints/initial")
    if report_hashes(initial) != manifest["initial_report_sha256"]:
        raise Refuse("initial snapshot hash mismatch")
    _, _, initial_ids = read_rounds(initial)
    if initial_ids != manifest["initial_round_ids"]:
        raise Refuse("manifest initial round ids differ")
    if control.get("inflight") is not None:
        raise Refuse("reserved round exists; automatic replay prohibited")
    if control.get("status") not in {"waiting", "complete"}:
        raise Refuse("control status is not runnable")
    count = control.get("slots_consumed")
    if type(count) is not int or not len(initial_ids) <= count <= MAX_TOTAL_ROUNDS:
        raise Refuse("invalid consumed-slot count")
    if control.get("completed_rounds") != count:
        raise Refuse("committed and consumed count differ")
    if control["status"] == "complete" and count != MAX_TOTAL_ROUNDS:
        raise Refuse("complete status before total-round limit")
    relative = control.get("current_rel", "")
    expected = "checkpoints/initial" if count == len(initial_ids) else f"runs/round-{count:03d}"
    if relative != expected:
        raise Refuse("current generation does not match count")
    generation = safe_path(root, relative)
    if report_hashes(generation) != control["report_sha256"]:
        raise Refuse("current generation hash mismatch")
    _, entries, ids = read_rounds(generation)
    if len(ids) != count or ids[:len(initial_ids)] != initial_ids:
        raise Refuse("current history does not extend initial history")
    if count < MAX_TOTAL_ROUNDS:
        due = timestamp(control["next_due"])
        if entries and due < timestamp(entries[-1]["finished_at"]) + timedelta(seconds=INTERVAL_SECONDS):
            raise Refuse("next due would shorten four-hour cadence")
    return manifest, control


def fsync_tree(directory):
    directories = [directory]
    for path in directory.rglob("*"):
        if path.is_file():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        elif path.is_dir():
            directories.append(path)
    for path in reversed(directories):
        fsync_directory(path)
    fsync_directory(directory.parent)


def stop_owned_group(child):
    """Reap the leader and stop descendants in its newly-created session group."""
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        child.wait(timeout=5)
        return
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        child.poll()  # Reap a dead leader so its zombie does not keep the group alive.
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    child.wait(timeout=5)


def run_child(stage, index):
    command = [sys.executable, str(stage / "scripts/run_forward_round_v1.py"),
               "--round-index", str(index), "--max-attempts", "1"]
    with (stage / "child.stdout.log").open("wb") as out, (stage / "child.stderr.log").open("wb") as err:
        child = subprocess.Popen(command, cwd=stage, env=MINIMAL_ENV,
                                 stdout=out, stderr=err, start_new_session=True)
        try:
            returncode = child.wait(timeout=CHILD_TIMEOUT_SECONDS)
        except BaseException:
            # A dead leader does not prove its same-group descendants have exited.
            stop_owned_group(child)
            raise
        else:
            if returncode != 0:
                stop_owned_group(child)
            return returncode
        finally:
            out.flush()
            err.flush()
            os.fsync(out.fileno())
            os.fsync(err.fileno())


def run_due_once(root, runner=run_child, clock=now):
    """Caller must hold exclusive_lock. No public market call before reservation."""
    manifest, control = validate(root)
    count = control["slots_consumed"]
    if count == MAX_TOTAL_ROUNDS:
        if control["status"] != "complete":
            control.update(status="complete", next_due=None)
            atomic_json(root / "control.json", control)
        event(root, "limit_reached", slots_consumed=count)
        return "complete"
    if clock() < timestamp(control["next_due"]):
        return "waiting"
    index = count + 1
    previous = safe_path(root, control["current_rel"])
    old_bytes, _, old_ids = read_rounds(previous)
    stage_rel = f"runs/round-{index:03d}"
    stage = safe_path(root, stage_rel)
    if stage.exists():
        raise Refuse("staging generation already exists; do not replay")
    reserved_at = clock().isoformat()
    control.update(slots_consumed=index, status="running",
                   inflight={"round_index": index, "stage_rel": stage_rel, "reserved_at": reserved_at})
    atomic_json(root / "control.json", control)
    try:
        event(root, "reserved", round_index=index, stage_rel=stage_rel)
        stage.mkdir(parents=True)
        shutil.copytree(previous / "reports", stage / "reports")
        shutil.copytree(root / "bundle/scripts", stage / "scripts")
        for path in (stage / "scripts").iterdir():
            path.chmod(0o444)
        verify_code(root, manifest, stage / "scripts")
        if report_hashes(stage) != control["report_sha256"]:
            raise Refuse("staging copy differs before execution")
        returncode = runner(stage, index)
        event(root, "child_exit", round_index=index, returncode=returncode)
        if returncode != 0:
            raise Refuse(f"child failed with returncode {returncode}; stage retained")
        verify_code(root, manifest, stage / "scripts")
        new_bytes, entries, ids = read_rounds(stage)
        if (not new_bytes.startswith(old_bytes) or len(entries) != count + 1
                or ids[:-1] != old_ids or entries[-1]["round_index"] != index):
            raise Refuse("expected exactly one appended successful round")
        if timestamp(entries[-1]["started_at"]) < timestamp(reserved_at):
            raise Refuse("new round predates reservation")
        # Preserve every historical T3 record byte-for-byte, not just its id.
        for rid in old_ids:
            relative = REPORTS / "rounds" / f"round.{rid}.json"
            if sha256(stage / relative) != sha256(previous / relative):
                raise Refuse("historical round record changed")
        fsync_tree(stage)
        finished = timestamp(entries[-1]["finished_at"])
        control.update(current_rel=stage_rel, completed_rounds=index,
                       report_sha256=report_hashes(stage), inflight=None,
                       status="complete" if index == MAX_TOTAL_ROUNDS else "waiting",
                       next_due=None if index == MAX_TOTAL_ROUNDS else
                       (finished + timedelta(seconds=INTERVAL_SECONDS)).isoformat())
        atomic_json(root / "control.json", control)
        event(root, "committed", round_index=index, round_id=ids[-1],
              next_due=control["next_due"], status=control["status"])
        return control["status"]
    except BaseException as exc:
        # Never erase a reservation, or roll back a possibly completed publication.
        actual = read_json(root / "control.json")
        if actual.get("inflight") is not None:
            actual.update(status="failed", failure={"type": type(exc).__name__, "message": str(exc)})
            atomic_json(root / "control.json", actual)
        event(root, "stopped_after_error", round_index=index,
              error_type=type(exc).__name__, error=str(exc))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--once", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    def stop(signum, _frame):
        raise InterruptedError(f"received signal {signum}")
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        with exclusive_lock(root):
            try:
                _, control = validate(root)
                if args.validate_only:
                    print(json.dumps({"validated": True, "completed_rounds": control["completed_rounds"],
                                      "next_due": control["next_due"]}))
                    return 0
                event(root, "wrapper_started", pid=os.getpid())
                while True:
                    status = run_due_once(root)
                    if args.once or status == "complete":
                        event(root, "wrapper_exit", status=status, returncode=0)
                        return 0
                    control = read_json(root / "control.json")
                    remaining = (timestamp(control["next_due"]) - now()).total_seconds()
                    time.sleep(max(0.1, min(remaining, 60)))
            except Exception as exc:
                if not args.validate_only:
                    event(root, "wrapper_exit", status="error", returncode=1,
                          error_type=type(exc).__name__, error=str(exc))
                raise
    except Exception as exc:
        print(f"STOPPED: {type(exc).__name__}: {exc}", file=sys.stderr)
        # Lock refusal must not append to the live owner's event stream.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
