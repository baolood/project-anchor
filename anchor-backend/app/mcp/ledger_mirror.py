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
from datetime import datetime, timezone
from pathlib import Path

from app.mcp.inventory import (
    LEDGER_MIRROR_DIR,
    OFFICIAL_LEDGER_DIR,
    OFFICIAL_LEDGER_DIR_PRIVATE,
)


SOURCE_RELATIVE = (
    "affl-v2-official-ledger",
    "out",
    "anchor_fake_fill_ledger_v2_official.jsonl",
)
LEDGER_BASENAME = SOURCE_RELATIVE[-1]
DIR_MODE = 0o750
FILE_MODE = 0o640
MIRROR_GROUP = "anchor-mcp"
PROJECT_ROOT = "/path/to/project-anchor"


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
Description=Run the Official V2 ledger read-only mirror every 10 minutes
Documentation=file:{backend}/docs/ANCHOR_LEDGER_READONLY_MIRROR_V1.md
After=anchor-official-ledger.service

[Timer]
OnBootSec=2min
OnCalendar=*:0/10
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


def mirror_ledger(source_root: str | Path, dest: str | Path, group: str = MIRROR_GROUP) -> None:
    """Copy the one live ledger file. Raises MirrorError without writing the source."""
    source_real = _resolve_dir(source_root)
    dest_real = _prepare_dest(dest, source_real, group)
    source_file = _resolve_source_file(source_real)
    blob, source_stat = _read_source(source_file)
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
    _fsync_dir(dest_real)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Official V2 ledger mirror")
    parser.add_argument("--source-root", default=OFFICIAL_LEDGER_DIR)
    parser.add_argument("--dest", default=LEDGER_MIRROR_DIR)
    parser.add_argument("--group", default=MIRROR_GROUP)
    args = parser.parse_args(argv)
    try:
        mirror_ledger(args.source_root, args.dest, args.group)
    except MirrorError as exc:
        print(f"ledger mirror failed: {exc}", file=sys.stderr)
        return 1
    return 0


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


def _read_source(path: Path) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise MirrorError("live ledger file unreadable") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise MirrorError("live ledger file is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
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
