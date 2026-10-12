"""Root oneshot copies one Official V2 ledger file and does not touch the source."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import unittest
from datetime import datetime, timezone

from app.mcp.official_ledger import LEDGER_DIR_ENV, read_official_ledger
from pathlib import Path
from unittest import mock

from app.mcp.inventory import LEDGER_MIRROR_DIR, OFFICIAL_LEDGER_DIR, OFFICIAL_LEDGER_DIR_PRIVATE
from app.mcp.ledger_mirror import (
    DIR_MODE,
    FILE_MODE,
    LEDGER_BASENAME,
    SOURCE_RELATIVE,
    MirrorError,
    _wait_until_stable,
    mirror_ledger,
    render_service_unit,
    render_success_drop_in,
    render_timer_unit,
)
from app.mcp.ledger_run_index import BOUNDARY_NAME, EVENTS_NAME


DOCS = Path(__file__).resolve().parents[1] / "docs" / "systemd"
READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC


def _live(root: Path) -> Path:
    return root.joinpath(*SOURCE_RELATIVE)


def _plant(root: Path, payload: bytes) -> Path:
    live = _live(root)
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_bytes(payload)
    os.utime(live, (1700000000, 1700000000))
    (root / "baseline").mkdir(exist_ok=True)
    (root / "baseline" / LEDGER_BASENAME).write_bytes(b"baseline-snapshot\n")
    before = root / "runs" / "sample-run" / "before"
    before.mkdir(parents=True, exist_ok=True)
    (before / LEDGER_BASENAME).write_bytes(b"before-snapshot\n")
    (root / LEDGER_BASENAME).write_bytes(b"top-level-snapshot\n")
    os.chmod(root, 0o700)
    return live


class LedgerMirrorTests(unittest.TestCase):
    def test_copies_only_the_live_file_and_leaves_the_source_unchanged(self) -> None:
        payload = b'{"ledger_event_id":"evt-1"}\n'
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            dest = base / "mirror"
            live = _plant(source, payload)
            source_mode = source.stat().st_mode
            source_mtime = source.stat().st_mtime_ns
            file_mode = live.stat().st_mode
            file_mtime = live.stat().st_mtime_ns
            listing = sorted(path.relative_to(source).as_posix() for path in source.rglob("*"))
            chmod_paths: list[str] = []
            real_chmod = os.chmod

            def spy_chmod(path: str | os.PathLike[str], mode: int) -> None:
                chmod_paths.append(os.fspath(path))
                real_chmod(path, mode)

            with mock.patch("app.mcp.ledger_mirror.os.chmod", side_effect=spy_chmod):
                mirror_ledger(source, dest, stable_for=0)
            self.assertEqual(live.read_bytes(), payload)
            self.assertEqual(live.stat().st_mode, file_mode)
            self.assertEqual(live.stat().st_mtime_ns, file_mtime)
            self.assertEqual(source.stat().st_mode, source_mode)
            self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o700)
            self.assertEqual(source.stat().st_mtime_ns, source_mtime)
            self.assertEqual(
                sorted(path.relative_to(source).as_posix() for path in source.rglob("*")),
                listing,
            )
            for path in chmod_paths:
                self.assertFalse(path.startswith(str(source)))
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), DIR_MODE)
            names = sorted(path.name for path in dest.iterdir())
            self.assertEqual(
                names,
                [
                    LEDGER_BASENAME,
                    f"{LEDGER_BASENAME}.meta.json",
                    f"{LEDGER_BASENAME}.sha256",
                ],
            )
            copied = dest / LEDGER_BASENAME
            self.assertEqual(copied.read_bytes(), payload)
            self.assertNotIn(b"baseline-snapshot", copied.read_bytes())
            self.assertNotIn(b"before-snapshot", copied.read_bytes())
            self.assertNotIn(b"top-level-snapshot", copied.read_bytes())
            for path in dest.iterdir():
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), FILE_MODE)
            digest = hashlib.sha256(payload).hexdigest()
            self.assertEqual((dest / f"{LEDGER_BASENAME}.sha256").read_text(encoding="ascii"), f"{digest}  {LEDGER_BASENAME}\n")
            meta = json.loads((dest / f"{LEDGER_BASENAME}.meta.json").read_text(encoding="utf-8"))
            expected_mtime = (
                datetime.fromtimestamp(1700000000, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            )
            self.assertEqual(meta["source_mtime"], expected_mtime)
            self.assertEqual(meta["source_size"], len(payload))
            self.assertRegex(meta["copied_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_source_open_is_read_only_and_publish_is_atomic(self) -> None:
        payload = b"live-bytes\n"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            dest = base / "mirror"
            live = _plant(source, payload)
            real_open = os.open
            real_fsync = os.fsync
            real_replace = os.replace
            opens: list[tuple[str, int]] = []
            fsyncs: list[int] = []
            replaces: list[tuple[str, str]] = []

            def spy_open(path: str | os.PathLike[str], flags: int, *args: int, **kwargs: int) -> int:
                opens.append((os.fspath(path), flags))
                return real_open(path, flags, *args, **kwargs)

            def spy_fsync(fd: int) -> None:
                fsyncs.append(fd)
                real_fsync(fd)

            def spy_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
                replaces.append((os.fspath(src), os.fspath(dst)))
                real_replace(src, dst)

            with (
                mock.patch("app.mcp.ledger_mirror.os.open", side_effect=spy_open),
                mock.patch("app.mcp.ledger_mirror.os.fsync", side_effect=spy_fsync),
                mock.patch("app.mcp.ledger_mirror.os.replace", side_effect=spy_replace),
            ):
                mirror_ledger(source, dest, stable_for=0)
            source_opens = [flags for path, flags in opens if path == str(live)]
            self.assertEqual(source_opens, [READ_FLAGS])
            write_bits = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            for path, flags in opens:
                if path.startswith(str(source)):
                    self.assertEqual(flags & write_bits, 0)
            self.assertGreaterEqual(len(fsyncs), 4)
            self.assertEqual(len(replaces), 3)
            for src, dst in replaces:
                self.assertTrue(src.startswith(str(dest)))
                self.assertTrue(os.path.basename(src).startswith("."))
                self.assertTrue(src.endswith(".tmp"))
                self.assertTrue(dst.startswith(str(dest)))
                self.assertFalse(os.path.exists(src))

    def test_symlink_source_file_is_not_published(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            dest = base / "mirror"
            outside = base / "outside.jsonl"
            outside.write_bytes(b"outside-secret\n")
            live = _live(source)
            live.parent.mkdir(parents=True)
            live.symlink_to(outside)
            os.chmod(source, 0o700)
            before = outside.read_bytes()
            with self.assertRaises(MirrorError):
                mirror_ledger(source, dest)
            self.assertEqual(outside.read_bytes(), before)
            self.assertFalse(dest.exists() and any(dest.iterdir()))

    def test_out_symlink_outside_the_root_is_not_published(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            dest = base / "mirror"
            outside = base / "outside"
            outside.mkdir()
            (outside / LEDGER_BASENAME).write_bytes(b"escaped-ledger\n")
            link_parent = source / "affl-v2-official-ledger"
            link_parent.mkdir(parents=True)
            (link_parent / "out").symlink_to(outside, target_is_directory=True)
            os.chmod(source, 0o700)
            with self.assertRaises(MirrorError):
                mirror_ledger(source, dest)
            self.assertFalse((dest / LEDGER_BASENAME).exists() if dest.exists() else False)

    def test_dest_inside_the_source_tree_is_refused(self) -> None:
        payload = b"live\n"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            live = _plant(source, payload)
            nested = source / "nested-mirror"
            mode = source.stat().st_mode
            mtime = live.stat().st_mtime_ns
            with self.assertRaises(MirrorError) as raised:
                mirror_ledger(source, nested)
            self.assertIn("overlapping", str(raised.exception))
            self.assertFalse(nested.exists())
            self.assertEqual(source.stat().st_mode, mode)
            self.assertEqual(live.stat().st_mtime_ns, mtime)
            self.assertEqual(live.read_bytes(), payload)
            parent_mode = base.stat().st_mode
            with self.assertRaises(MirrorError):
                mirror_ledger(source, base)
            self.assertEqual(base.stat().st_mode, parent_mode)
            with self.assertRaises(MirrorError):
                mirror_ledger(source, source)
            self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o700)

    def test_root_chowns_dest_to_the_mirror_group(self) -> None:
        payload = b"live\n"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            dest = base / "mirror"
            _plant(source, payload)
            chowns: list[tuple[str, int, int]] = []

            def spy_chown(path: str | os.PathLike[str], uid: int, gid: int) -> None:
                chowns.append((os.fspath(path), uid, gid))

            group = mock.Mock(gr_gid=42)
            with (
                mock.patch("app.mcp.ledger_mirror.os.geteuid", return_value=0),
                mock.patch("app.mcp.ledger_mirror.grp.getgrnam", return_value=group) as getgrnam,
                mock.patch("app.mcp.ledger_mirror.os.chown", side_effect=spy_chown),
            ):
                mirror_ledger(source, dest, group="anchor-mcp", stable_for=0)
            getgrnam.assert_called_with("anchor-mcp")
            self.assertGreaterEqual(len(chowns), 4)
            for path, uid, gid in chowns:
                self.assertEqual((uid, gid), (0, 42))
                self.assertTrue(path.startswith(str(dest)))
                self.assertFalse(path.startswith(str(source)))

    def test_skips_while_source_size_or_mtime_is_changing(self) -> None:
        payload = b"live-bytes\n"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            dest = base / "mirror"
            live = _plant(source, payload)
            before_mode = live.stat().st_mode
            before_mtime = live.stat().st_mtime_ns
            clock = {"t": 0.0}
            calls = {"n": 0}

            def monotonic() -> float:
                return clock["t"]

            def sleep(seconds: float) -> None:
                clock["t"] += seconds

            def stat_source(path: Path):
                calls["n"] += 1
                return mock.Mock(st_size=calls["n"], st_mtime_ns=calls["n"])

            outcome = mirror_ledger(
                source,
                dest,
                stable_for=2,
                max_wait=1,
                sleep=sleep,
                monotonic=monotonic,
                stat_source=stat_source,
            )
            self.assertEqual(outcome, "skipped")
            self.assertFalse((dest / LEDGER_BASENAME).exists())
            self.assertEqual(live.read_bytes(), payload)
            self.assertEqual(live.stat().st_mode, before_mode)
            self.assertEqual(live.stat().st_mtime_ns, before_mtime)

    def test_copies_after_size_and_mtime_are_stable_for_two_seconds(self) -> None:
        payload = b"stable-live\n"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            dest = base / "mirror"
            _plant(source, payload)
            clock = {"t": 0.0}

            def monotonic() -> float:
                return clock["t"]

            def sleep(seconds: float) -> None:
                clock["t"] += seconds

            outcome = mirror_ledger(source, dest, stable_for=2, max_wait=5, sleep=sleep, monotonic=monotonic)
            self.assertEqual(outcome, "copied")
            self.assertGreaterEqual(clock["t"], 2)
            self.assertEqual((dest / LEDGER_BASENAME).read_bytes(), payload)

    def test_stability_window_resets_when_mtime_changes(self) -> None:
        clock = {"t": 0.0}
        mtime = {"n": 5}

        def monotonic() -> float:
            return clock["t"]

        def sleep(seconds: float) -> None:
            clock["t"] += seconds

        def stat_source(path: Path):
            if clock["t"] >= 1:
                mtime["n"] = 9
            return mock.Mock(st_size=10, st_mtime_ns=mtime["n"])

        sample = _wait_until_stable(
            Path("/tmp/ledger-source"),
            stable_for=2,
            max_wait=10,
            sleep=sleep,
            monotonic=monotonic,
            stat_source=stat_source,
        )
        self.assertEqual(sample, (10, 9))
        self.assertGreaterEqual(clock["t"], 3)

    def test_units_are_hardened_and_match_the_examples(self) -> None:
        service = render_service_unit()
        timer = render_timer_unit()
        drop_in = render_success_drop_in()
        self.assertEqual((DOCS / "anchor-ledger-readonly-mirror.service.example").read_text(encoding="utf-8"), service)
        self.assertEqual((DOCS / "anchor-ledger-readonly-mirror.timer.example").read_text(encoding="utf-8"), timer)
        self.assertEqual(
            (DOCS / "anchor-official-ledger.service.d" / "readonly-mirror.conf.example").read_text(encoding="utf-8"),
            drop_in,
        )
        combined = service + timer + drop_in
        self.assertIn("After=anchor-official-ledger.service", service)
        self.assertIn("After=anchor-official-ledger.service", timer)
        self.assertIn(f"ReadOnlyPaths={OFFICIAL_LEDGER_DIR}", service)
        self.assertIn(f"ReadOnlyPaths={OFFICIAL_LEDGER_DIR_PRIVATE}", service)
        self.assertIn(f"ReadWritePaths={LEDGER_MIRROR_DIR}", service)
        self.assertIn("PrivateNetwork=yes", service)
        self.assertIn("User=root", service)
        self.assertIn("ProtectSystem=strict", service)
        self.assertIn("RestrictAddressFamilies=AF_UNIX", service)
        self.assertIn("OnCalendar=*:00,20,30,40,50", timer)
        self.assertNotIn("*:0/10", timer)
        calendar = next(line for line in timer.splitlines() if line.startswith("OnCalendar="))
        self.assertNotIn("10", calendar.split("=", 1)[1])
        self.assertEqual(drop_in, "[Unit]\nOnSuccess=anchor-ledger-readonly-mirror.service\n")
        for forbidden in ("setfacl", "chmod", "AF_INET", "StateDirectory=", "DynamicUser="):
            self.assertNotIn(forbidden, combined)

    def test_copies_the_run_index_and_not_the_before_snapshot(self) -> None:
        marker = b"SNAPSHOT-MARKER-NOT-COPIED"
        blocked = b"BLOCKED-MARKER-NOT-COPIED"
        first = (
            json.dumps(
                {
                    "event_type": "PENDING_NEXT_BAR",
                    "ledger_event_id": "le-0001",
                    "observation_id": "obs-1",
                    "row_hash": "a" * 64,
                    "signal_available_at": "2026-10-12T10:05:00Z",
                    "signal_candle_open_utc": "2026-10-12T10:00:00Z",
                },
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        second = (
            json.dumps(
                {
                    "event_type": "OPEN",
                    "fill_time_utc": "2026-10-12T11:00:00Z",
                    "ledger_event_id": "le-0002",
                    "observation_id": "obs-1",
                    "row_hash": "b" * 64,
                    "signal_available_at": "2026-10-12T10:05:00Z",
                    "signal_candle_open_utc": "2026-10-12T10:00:00Z",
                },
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        live = first + second
        committed = "\n".join(
            [
                json.dumps(
                    {
                        "at": "2026-10-12T10:10:01.250000+00:00",
                        "event": "committed",
                        "next_due": None,
                        "round_id": "ab" * 16,
                        "round_index": 1,
                        "status": "waiting",
                    },
                    sort_keys=True,
                ),
                json.dumps(
                    {
                        "at": "2026-10-12T12:10:01+00:00",
                        "event": "committed",
                        "next_due": None,
                        "round_id": "cd" * 16,
                        "round_index": 2,
                        "status": "waiting",
                    },
                    sort_keys=True,
                ),
            ]
        ) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            dest = base / "mirror"
            live_path = _plant(source, live)
            (source / EVENTS_NAME).write_text(committed, encoding="utf-8")
            (source / "BLOCKED.json").write_bytes(blocked)
            empty = source / "runs" / "run-000001" / "before"
            empty.mkdir(parents=True)
            (empty / LEDGER_BASENAME).write_bytes(b"")
            before = source / "runs" / "run-000002" / "before"
            before.mkdir(parents=True)
            snapshot = before / LEDGER_BASENAME
            snapshot.write_bytes(marker + b"\n" + first)
            source_bytes = snapshot.read_bytes()
            mirror_ledger(source, dest, stable_for=0)
            self.assertEqual(snapshot.read_bytes(), source_bytes)
            self.assertEqual(live_path.read_bytes(), live)
            copied_events = (dest / EVENTS_NAME).read_text(encoding="utf-8")
            self.assertEqual(copied_events, committed)
            boundaries = [
                json.loads(line)
                for line in (dest / BOUNDARY_NAME).read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                boundaries,
                [
                    {
                        "committed_at": "2026-10-12T10:10:01.250000+00:00",
                        "last_ledger_event_id_before": None,
                        "run": "run-000001",
                        "run_index": 1,
                    },
                    {
                        "committed_at": "2026-10-12T12:10:01+00:00",
                        "last_ledger_event_id_before": "le-0001",
                        "run": "run-000002",
                        "run_index": 2,
                    },
                ],
            )
            published = b"".join(path.read_bytes() for path in dest.rglob("*") if path.is_file())
            self.assertNotIn(marker, published)
            self.assertNotIn(blocked, published)
            summary = read_official_ledger(
                {LEDGER_DIR_ENV: str(dest)},
                allowlist=(str(dest),),
                now=datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(summary["pending_observations"]["BAR_NOT_YET_CLOSED"], 1)
            self.assertEqual(summary["pending_observations"]["DATA_GAP"], 0)
            self.assertEqual(summary["counts"]["by_type"]["PENDING_NEXT_BAR"], 1)
            self.assertNotIn("obs-1", json.dumps(summary))

    def test_skips_while_events_jsonl_is_still_changing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "ledger-root"
            dest = base / "mirror"
            _plant(source, b'{"ledger_event_id":"le-0001"}\n')
            events = source / EVENTS_NAME
            events.write_text("{}\n", encoding="utf-8")
            clock = {"t": 0.0}
            ticks = {"n": 0}

            def monotonic() -> float:
                return clock["t"]

            def sleep(seconds: float) -> None:
                clock["t"] += seconds

            def stat_source(path: Path):
                size = 10
                if path.name == EVENTS_NAME:
                    ticks["n"] += 1
                    size = ticks["n"]
                return mock.Mock(st_size=size, st_mtime_ns=1)

            outcome = mirror_ledger(
                source,
                dest,
                stable_for=2,
                max_wait=1,
                sleep=sleep,
                monotonic=monotonic,
                stat_source=stat_source,
            )
            self.assertEqual(outcome, "skipped")
            self.assertFalse((dest / LEDGER_BASENAME).exists())
            self.assertEqual(events.read_text(encoding="utf-8"), "{}\n")


if __name__ == "__main__":
    unittest.main()
