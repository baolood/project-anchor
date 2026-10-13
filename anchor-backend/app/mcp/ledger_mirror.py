"""Root oneshot that copies the Official V2 ledger into a separate mirror.

The ledger StateDirectory stays mode 0700 for DynamicUser. This process is
the only reader of that directory. It opens the source read-only and writes
only under the mirror directory. It does not chmod or setfacl the source.
"""

from __future__ import annotations

import argparse
import grp
import hashlib
import json
import os
import stat
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.mcp.inventory import (
    LEDGER_MIRROR_DIR,
    OFFICIAL_LEDGER_DIR,
    OFFICIAL_LEDGER_DIR_PRIVATE,
)
from app.mcp.ledger_run_index import (
    BOUNDARY_NAME,
    EVENTS_NAME,
    RUN_DIR_RE,
    boundaries_from_commits,
    ledger_line_ids,
    parse_committed_runs,
    snapshot_matches,
)


SOURCE_RELATIVE = (
    "affl-v2-official-ledger",
    "out",
    "anchor_fake_fill_ledger_v2_official.jsonl",
)
LEDGER_BASENAME = SOURCE_RELATIVE[-1]
# Before-snapshot of one run. The flat before/<ledger> path is not this file.
BEFORE_SNAPSHOT_RELATIVE = (
    "before",
    "affl-v2-official-ledger",
    "out",
    LEDGER_BASENAME,
)
DIR_MODE = 0o750
FILE_MODE = 0o640
MIRROR_GROUP = "anchor-mcp"
PROJECT_ROOT = "/path/to/project-anchor"
STABLE_FOR_SEC = 2.0
STABLE_MAX_WAIT_SEC = 30.0
EVENTS_MAX_BYTES = 8 * 1024 * 1024
SNAPSHOT_TAIL_BYTES = 65536


class MirrorError(Exception):
    """The mirror copy did not run. The source is left untouched."""


def render_service_unit() -> str:
    """Example oneshot. Review only; this function does not install it."""
    backend = f"{PROJECT_ROOT}/anchor-backend"
    return f"""[Unit]
Description=Read-only mirror of the Official V2 ledger for anchor-mcp
Documentation=file:{backend}/docs/ANCHOR_LEDGER_READONLY_MIRROR_V1.md
After=anchor-official-ledger.service

[Service]
Type=oneshot
User=root
Group=root
WorkingDirectory={backend}
Environment=PYTHONPATH={backend}
ExecStart=/usr/bin/python3 -m app.mcp.ledger_mirror
ReadOnlyPaths={OFFICIAL_LEDGER_DIR}
ReadOnlyPaths={OFFICIAL_LEDGER_DIR_PRIVATE}
ReadWritePaths={LEDGER_MIRROR_DIR}
ProtectSystem=strict
PrivateNetwork=yes
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
UMask=0027
RestrictAddressFamilies=AF_UNIX
LockPersonality=true
RestrictSUIDSGID=true

[Install]
WantedBy=multi-user.target
"""


def render_timer_unit() -> str:
    backend = f"{PROJECT_ROOT}/anchor-backend"
    return f"""[Unit]
Description=Run the Official V2 ledger read-only mirror outside the ledger write minute
Documentation=file:{backend}/docs/ANCHOR_LEDGER_READONLY_MIRROR_V1.md
After=anchor-official-ledger.service

[Timer]
OnBootSec=2min
OnCalendar=*:00,20,30,40,50
AccuracySec=30s
Persistent=true
Unit=anchor-ledger-readonly-mirror.service

[Install]
WantedBy=timers.target
"""


def render_success_drop_in() -> str:
    """Add-on for the ledger unit. It does not change StateDirectory or mode."""
    return """[Unit]
OnSuccess=anchor-ledger-readonly-mirror.service
"""


def mirror_ledger(
    source_root: str | Path,
    dest: str | Path,
    group: str = MIRROR_GROUP,
    *,
    stable_for: float = STABLE_FOR_SEC,
    max_wait: float = STABLE_MAX_WAIT_SEC,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    stat_source: Callable[[Path], os.stat_result] | None = None,
) -> str:
    """Copy the one live ledger file. Raises MirrorError without writing the source.

    Returns ``copied`` or ``skipped``. A skip happens when the source size or
    mtime is still changing. The source is not modified in either case.
    """
    source_real = _resolve_dir(source_root)
    dest_real = _prepare_dest(dest, source_real, group)
    source_file = _resolve_source_file(source_real)
    index_paths = _index_paths(source_real)
    watched = [source_file, *index_paths]
    stat_fn = os.stat if stat_source is None else stat_source
    sample = _wait_until_all_stable(
        watched,
        stable_for=stable_for,
        max_wait=max_wait,
        sleep=sleep,
        monotonic=monotonic,
        stat_source=stat_fn,
    )
    if sample is None:
        return "skipped"
    blob, source_stat = _read_source(source_file)
    if stable_for > 0 and (source_stat.st_size, source_stat.st_mtime_ns) != sample[source_file]:
        return "skipped"
    index_blobs: dict[Path, bytes] = {}
    for path in index_paths:
        # Run 1's before snapshot is counted in full. Later snapshots only need a last id.
        limit = None if path.name == EVENTS_NAME or _is_run1_before(path) else SNAPSHOT_TAIL_BYTES
        index_blob, index_stat = _read_source(path, limit=limit)
        if stable_for > 0 and (index_stat.st_size, index_stat.st_mtime_ns) != sample[path]:
            return "skipped"
        if path.name == EVENTS_NAME and index_stat.st_size > EVENTS_MAX_BYTES:
            continue
        index_blobs[path] = index_blob
    digest = hashlib.sha256(blob).hexdigest()
    copied_at = _utc_now()
    source_mtime = datetime.fromtimestamp(source_stat.st_mtime, timezone.utc).replace(microsecond=0)
    meta = {
        "source_mtime": _iso(source_mtime),
        "source_size": source_stat.st_size,
        "copied_at": copied_at,
    }
    _atomic_write(dest_real, LEDGER_BASENAME, blob, group)
    _atomic_write(dest_real, f"{LEDGER_BASENAME}.sha256", f"{digest}  {LEDGER_BASENAME}\n".encode("ascii"), group)
    _atomic_write(
        dest_real,
        f"{LEDGER_BASENAME}.meta.json",
        (json.dumps(meta, sort_keys=True) + "\n").encode("utf-8"),
        group,
    )
    _publish_run_index(dest_real, source_real, index_blobs, blob, group)
    _fsync_dir(dest_real)
    return "copied"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Official V2 ledger mirror")
    parser.add_argument("--source-root", default=OFFICIAL_LEDGER_DIR)
    parser.add_argument("--dest", default=LEDGER_MIRROR_DIR)
    parser.add_argument("--group", default=MIRROR_GROUP)
    args = parser.parse_args(argv)
    try:
        outcome = mirror_ledger(args.source_root, args.dest, args.group)
    except MirrorError as exc:
        print(f"ledger mirror failed: {exc}", file=sys.stderr)
        return 1
    if outcome == "skipped":
        print("ledger mirror skipped: source size or mtime still changing", file=sys.stderr)
    return 0


def _index_paths(root: Path) -> list[Path]:
    """Regular files the run index is read from. Snapshots are not copied."""
    paths: list[Path] = []
    events = _regular_inside(root, (EVENTS_NAME,))
    if events is not None:
        paths.append(events)
    runs = root / "runs"
    try:
        info = os.lstat(runs)
    except OSError:
        return paths
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        return paths
    try:
        names = sorted(os.listdir(runs))
    except OSError:
        return paths
    for name in names:
        if RUN_DIR_RE.fullmatch(name) is None:
            continue
        before = _regular_inside(root, ("runs", name, *BEFORE_SNAPSHOT_RELATIVE))
        if before is not None:
            paths.append(before)
    return paths


def _regular_inside(root: Path, parts: tuple[str, ...]) -> Path | None:
    current = root
    for index, part in enumerate(parts):
        nxt = current / part
        try:
            info = os.lstat(nxt)
        except OSError:
            return None
        if stat.S_ISLNK(info.st_mode):
            return None
        last = index == len(parts) - 1
        if last and not stat.S_ISREG(info.st_mode):
            return None
        if not last and not stat.S_ISDIR(info.st_mode):
            return None
        current = nxt
    try:
        resolved = Path(os.path.realpath(current))
        rel = resolved.relative_to(root)
    except (OSError, ValueError):
        return None
    if rel.parts != parts:
        return None
    return resolved


def _publish_run_index(
    dest: Path,
    source: Path,
    blobs: dict[Path, bytes],
    live_blob: bytes,
    group: str,
) -> None:
    """Copy ``events.jsonl`` and publish line spans. Snapshots are not copied.

    Spans come from cumulative ``ledger_events``. Run 1's start is the row
    count of its nested before snapshot, and that snapshot's last id must
    match the live row at that index. Later snapshots are a last-id
    cross-check. A mismatch, or a ``run_seq`` that does not start at 1 and
    stay contiguous, removes any previously published boundaries.
    """
    events_path = _regular_inside(source, (EVENTS_NAME,))
    if events_path is None or events_path not in blobs:
        _remove_published(dest, BOUNDARY_NAME)
        _remove_published(dest, f"{BOUNDARY_NAME}.sha256")
        return
    events_blob = blobs[events_path]
    _atomic_write(dest, EVENTS_NAME, events_blob, group)
    _atomic_write(dest, f"{EVENTS_NAME}.sha256", _sha_line(events_blob, EVENTS_NAME), group)
    commits = parse_committed_runs(events_blob.decode("utf-8", errors="replace"))
    provisional = boundaries_from_commits(commits)
    if not provisional:
        boundaries = provisional
    else:
        offset = _run1_before_offset(source, blobs, live_blob, provisional[0]["ledger_events"])
        boundaries = None if offset is None else boundaries_from_commits(commits, pre_index_rows=offset)
    if boundaries and not _snapshots_agree(source, blobs, live_blob, boundaries):
        boundaries = None
    if not boundaries:
        _remove_published(dest, BOUNDARY_NAME)
        _remove_published(dest, f"{BOUNDARY_NAME}.sha256")
        return
    lines = [json.dumps(boundary, sort_keys=True) for boundary in boundaries]
    boundary_blob = ("\n".join(lines) + "\n").encode("utf-8")
    _atomic_write(dest, BOUNDARY_NAME, boundary_blob, group)
    _atomic_write(dest, f"{BOUNDARY_NAME}.sha256", _sha_line(boundary_blob, BOUNDARY_NAME), group)


def _is_run1_before(path: Path) -> bool:
    tail = ("run-000001", *BEFORE_SNAPSHOT_RELATIVE)
    return path.parts[-len(tail) :] == tail


def _run1_before_offset(
    source: Path,
    blobs: dict[Path, bytes],
    live_blob: bytes,
    run1_ledger_events: int,
) -> int | None:
    """Row count of run 1's before snapshot, after the last id matches the live row.

    A missing or empty snapshot is offset 0. A snapshot whose last
    ``ledger_event_id`` is not the live row at that count is ``None``.
    """
    path = _regular_inside(source, ("runs", "run-000001", *BEFORE_SNAPSHOT_RELATIVE))
    if path is None or path not in blobs:
        return 0
    snapshot_ids = ledger_line_ids(blobs[path])
    if snapshot_ids is None:
        return None
    offset = len(snapshot_ids)
    if offset == 0:
        return 0
    if offset > run1_ledger_events:
        return None
    last = snapshot_ids[-1]
    if not isinstance(last, str):
        return None
    live_ids = ledger_line_ids(live_blob)
    if live_ids is None or len(live_ids) < offset or live_ids[offset - 1] != last:
        return None
    return offset


def _snapshots_agree(
    source: Path,
    blobs: dict[Path, bytes],
    live_blob: bytes,
    boundaries: list[dict[str, Any]],
) -> bool:
    ids = ledger_line_ids(live_blob)
    if ids is None or boundaries[-1]["ledger_events"] > len(ids):
        return False
    for boundary in boundaries:
        before = _regular_inside(source, ("runs", str(boundary["run"]), *BEFORE_SNAPSHOT_RELATIVE))
        if before is None:
            continue
        if before not in blobs:
            return False
        before_count = boundary["ledger_events_before"]
        if before_count == 0:
            expected = None
        else:
            expected = ids[before_count - 1]
            if not isinstance(expected, str):
                return False
        if not snapshot_matches(expected, blobs[before]):
            return False
    return True


def _remove_published(directory: Path, name: str) -> None:
    path = directory / name
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise MirrorError("mirror cleanup failed") from exc
    if stat.S_ISDIR(info.st_mode):
        raise MirrorError("mirror cleanup failed")
    try:
        os.unlink(path)
    except OSError as exc:
        raise MirrorError("mirror cleanup failed") from exc


def _sha_line(blob: bytes, name: str) -> bytes:
    digest = hashlib.sha256(blob).hexdigest()
    return f"{digest}  {name}\n".encode("ascii")


def _wait_until_all_stable(
    paths: list[Path],
    *,
    stable_for: float,
    max_wait: float,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    stat_source: Callable[[Path], os.stat_result],
) -> dict[Path, tuple[int, int]] | None:
    """Return size and mtime_ns for every path once the whole set is unchanged."""

    def sample() -> dict[Path, tuple[int, int]]:
        return {path: (info.st_size, info.st_mtime_ns) for path in paths for info in (stat_source(path),)}

    if stable_for <= 0:
        return sample()
    deadline = monotonic() + max_wait
    last = sample()
    stable_since = monotonic()
    while True:
        now = monotonic()
        current = sample()
        if current != last:
            last = current
            stable_since = now
        elif now - stable_since >= stable_for:
            return last
        if now >= deadline:
            return None
        remaining = min(0.2, stable_for - (now - stable_since), deadline - now)
        if remaining > 0:
            sleep(remaining)


def _wait_until_stable(
    path: Path,
    *,
    stable_for: float,
    max_wait: float,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    stat_source: Callable[[Path], os.stat_result],
) -> tuple[int, int] | None:
    """Return ``(size, mtime_ns)`` once both have stayed the same for ``stable_for`` seconds."""
    if stable_for <= 0:
        info = stat_source(path)
        return (info.st_size, info.st_mtime_ns)
    deadline = monotonic() + max_wait

    def sample() -> tuple[int, int]:
        info = stat_source(path)
        return (info.st_size, info.st_mtime_ns)

    last = sample()
    stable_since = monotonic()
    while True:
        now = monotonic()
        current = sample()
        if current != last:
            last = current
            stable_since = now
        elif now - stable_since >= stable_for:
            return last
        if now >= deadline:
            return None
        remaining = min(0.2, stable_for - (now - stable_since), deadline - now)
        if remaining > 0:
            sleep(remaining)


def _resolve_dir(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise MirrorError("path must be absolute")
    try:
        resolved = Path(os.path.realpath(candidate))
    except OSError as exc:
        raise MirrorError("path unreadable") from exc
    if not resolved.is_dir():
        raise MirrorError("directory missing")
    return resolved


def _prepare_dest(dest: str | Path, source_real: Path, group: str) -> Path:
    """Create the mirror directory only after proving it does not overlap the source."""
    candidate = Path(dest)
    if not candidate.is_absolute():
        raise MirrorError("dest must be absolute")
    intended = _intended_real(candidate)
    _refuse_overlap(intended, source_real)
    try:
        candidate.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
    except OSError as exc:
        raise MirrorError("dest unwritable") from exc
    dest_real = Path(os.path.realpath(candidate))
    _refuse_overlap(dest_real, source_real)
    if dest_real != intended:
        raise MirrorError("dest path changed during create")
    os.chmod(dest_real, DIR_MODE)
    _chown_if_root(dest_real, group)
    return dest_real


def _intended_real(path: Path) -> Path:
    """Resolve an existing path, or an existing parent plus not-yet-created names."""
    cursor = path
    tail: list[str] = []
    while not cursor.exists() and not cursor.is_symlink():
        if cursor.parent == cursor:
            break
        tail.append(cursor.name)
        cursor = cursor.parent
    resolved = Path(os.path.realpath(cursor))
    for name in reversed(tail):
        resolved = resolved / name
    return resolved


def _refuse_overlap(dest_real: Path, source_real: Path) -> None:
    if _contains(dest_real, source_real) or _contains(source_real, dest_real):
        raise MirrorError("refusing overlapping source and dest")


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolve_source_file(root_real: Path) -> Path:
    current = root_real
    walked: list[str] = []
    for part in SOURCE_RELATIVE:
        walked.append(part)
        nxt = current / part
        try:
            info = os.lstat(nxt)
        except FileNotFoundError as exc:
            raise MirrorError("live ledger file missing") from exc
        except OSError as exc:
            raise MirrorError("live ledger file unreadable") from exc
        is_last = tuple(walked) == SOURCE_RELATIVE
        if is_last:
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise MirrorError("live ledger file is not a regular file")
            try:
                nxt_real = Path(os.path.realpath(nxt))
            except OSError as exc:
                raise MirrorError("live ledger file unreadable") from exc
            try:
                rel = nxt_real.relative_to(root_real)
            except ValueError as exc:
                raise MirrorError("live ledger file escaped the source root") from exc
            if rel.parts != SOURCE_RELATIVE:
                raise MirrorError("live ledger file escaped the source root")
            return nxt_real
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)):
            raise MirrorError("live ledger path is not a directory")
        try:
            nxt_real = Path(os.path.realpath(nxt))
        except OSError as exc:
            raise MirrorError("live ledger path unreadable") from exc
        if not nxt_real.is_dir():
            raise MirrorError("live ledger path is not a directory")
        try:
            rel = nxt_real.relative_to(root_real)
        except ValueError as exc:
            raise MirrorError("live ledger path escaped the source root") from exc
        if rel.parts != tuple(walked):
            raise MirrorError("live ledger path escaped the source root")
        current = nxt_real
    raise MirrorError("live ledger file missing")


def _read_source(path: Path, *, limit: int | None = None) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise MirrorError("source file unreadable") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise MirrorError("source file is not a regular file")
        if limit is not None and info.st_size > limit:
            os.lseek(fd, info.st_size - limit, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = limit
        while remaining is None or remaining > 0:
            chunk = os.read(fd, 65536 if remaining is None else min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            if remaining is not None:
                remaining -= len(chunk)
        return b"".join(chunks), info
    finally:
        os.close(fd)


def _atomic_write(directory: Path, name: str, data: bytes, group: str) -> None:
    tmp_name = f".{name}.{os.getpid()}.tmp"
    tmp = directory / tmp_name
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        fd = os.open(tmp, flags, FILE_MODE)
    except OSError as exc:
        raise MirrorError("mirror temp file failed") from exc
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    except Exception:
        os.close(fd)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    os.close(fd)
    final = directory / name
    try:
        os.chmod(tmp, FILE_MODE)
        os.replace(tmp, final)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _chown_if_root(final, group)


def _fsync_dir(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(directory, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _chown_if_root(path: Path, group: str) -> None:
    if os.geteuid() != 0:
        return
    try:
        gid = grp.getgrnam(group).gr_gid
    except KeyError as exc:
        raise MirrorError(f"group {group} missing") from exc
    os.chown(path, 0, gid)


def _utc_now() -> str:
    return _iso(datetime.now(timezone.utc).replace(microsecond=0))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
