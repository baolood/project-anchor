import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared.schemas import Event, Stage, Status, new_event_id


DB_PATH = Path("/Users/baolood/Projects/project-anchor/anchor.db")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table})")
    cols = {row[1] for row in c.fetchall()}
    if column not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            command_id TEXT,
            stage TEXT,
            status TEXT,
            timestamp REAL,
            payload TEXT
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS executed_commands (
            command_id TEXT PRIMARY KEY,
            timestamp REAL
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_dispatches (
            ticket_id TEXT PRIMARY KEY,
            command_id TEXT,
            payload TEXT,
            status TEXT,
            created_at REAL,
            updated_at REAL
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_receipts (
            ticket_id TEXT PRIMARY KEY,
            command_id TEXT,
            status TEXT,
            payload TEXT,
            created_at REAL
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduler_status (
            scheduler_name TEXT PRIMARY KEY,
            last_cycle_time REAL,
            last_cycle_summary TEXT
        )
        """
    )

    _ensure_column(conn, "pending_dispatches", "retry_count", "INTEGER DEFAULT 0")
    _ensure_column(conn, "pending_dispatches", "last_error", "TEXT DEFAULT ''")
    _ensure_column(conn, "pending_dispatches", "next_retry_at", "REAL DEFAULT 0")

    conn.commit()
    conn.close()


def append_event(
    command_id: str,
    stage: Stage,
    status: Status,
    payload: Optional[Dict[str, Any]] = None,
) -> Event:
    init_db()
    event = Event(
        event_id=new_event_id(),
        command_id=command_id,
        stage=stage,
        status=status,
        timestamp=time.time(),
        payload=payload or {},
    )

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
        (
            event.event_id,
            event.command_id,
            event.stage.value,
            event.status.value,
            event.timestamp,
            json.dumps(event.payload, ensure_ascii=True),
        ),
    )
    conn.commit()
    conn.close()
    return event


def list_events(command_id: Optional[str] = None) -> List[Event]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if command_id is None:
        c.execute(
            "SELECT event_id, command_id, stage, status, timestamp, payload FROM events ORDER BY timestamp ASC"
        )
    else:
        c.execute(
            "SELECT event_id, command_id, stage, status, timestamp, payload FROM events WHERE command_id=? ORDER BY timestamp ASC",
            (command_id,),
        )

    rows = c.fetchall()
    conn.close()

    events: List[Event] = []
    for row in rows:
        events.append(
            Event(
                event_id=row[0],
                command_id=row[1],
                stage=Stage(row[2]),
                status=Status(row[3]),
                timestamp=row[4],
                payload=json.loads(row[5]) if row[5] else {},
            )
        )
    return events


def clear_events() -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM events")
    conn.commit()
    conn.close()


def is_executed(command_id: str) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM executed_commands WHERE command_id=?",
        (command_id,),
    )
    result = c.fetchone()
    conn.close()
    return result is not None


def mark_executed(command_id: str) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO executed_commands VALUES (?, ?)",
        (command_id, time.time()),
    )
    conn.commit()
    conn.close()


def clear_executed() -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM executed_commands")
    conn.commit()
    conn.close()


def register_dispatch(ticket_id: str, command_id: str, payload: Dict[str, Any]) -> None:
    init_db()
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO pending_dispatches
        (ticket_id, command_id, payload, status, created_at, updated_at, retry_count, last_error, next_retry_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ticket_id, command_id, json.dumps(payload, ensure_ascii=True), "PENDING", now, now, 0, "", now),
    )
    conn.commit()
    conn.close()


def mark_dispatch_done(ticket_id: str) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE pending_dispatches SET status=?, updated_at=? WHERE ticket_id=?",
        ("DONE", time.time(), ticket_id),
    )
    conn.commit()
    conn.close()


def mark_dispatch_retry(ticket_id: str, error: str, delay_sec: float, max_retries: int) -> Dict[str, Any]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT retry_count FROM pending_dispatches WHERE ticket_id=?",
        (ticket_id,),
    )
    row = c.fetchone()
    current_retry = int(row[0] or 0) if row else 0
    next_retry = current_retry + 1
    now = time.time()
    if next_retry > max_retries:
        status = "DEAD"
        next_retry_at = now
    else:
        status = "PENDING"
        next_retry_at = now + delay_sec
    c.execute(
        """
        UPDATE pending_dispatches
        SET status=?, updated_at=?, retry_count=?, last_error=?, next_retry_at=?
        WHERE ticket_id=?
        """,
        (status, now, next_retry, error, next_retry_at, ticket_id),
    )
    conn.commit()
    conn.close()
    return {
        "ticket_id": ticket_id,
        "status": status,
        "retry_count": next_retry,
        "last_error": error,
        "next_retry_at": next_retry_at,
    }


def list_pending_dispatches(ready_only: bool = False) -> List[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if ready_only:
        c.execute(
            """
            SELECT ticket_id, command_id, payload, status, created_at, updated_at, retry_count, last_error, next_retry_at
            FROM pending_dispatches
            WHERE status = 'PENDING' AND next_retry_at <= ?
            ORDER BY created_at ASC
            """,
            (time.time(),),
        )
    else:
        c.execute(
            """
            SELECT ticket_id, command_id, payload, status, created_at, updated_at, retry_count, last_error, next_retry_at
            FROM pending_dispatches
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
            """
        )
    rows = c.fetchall()
    conn.close()
    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "ticket_id": row[0],
                "command_id": row[1],
                "payload": json.loads(row[2]) if row[2] else {},
                "status": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "retry_count": row[6],
                "last_error": row[7],
                "next_retry_at": row[8],
            }
        )
    return out


def list_dead_dispatches() -> List[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT ticket_id, command_id, payload, status, created_at, updated_at, retry_count, last_error, next_retry_at
        FROM pending_dispatches
        WHERE status = 'DEAD'
        ORDER BY updated_at DESC
        """
    )
    rows = c.fetchall()
    conn.close()
    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "ticket_id": row[0],
                "command_id": row[1],
                "payload": json.loads(row[2]) if row[2] else {},
                "status": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "retry_count": row[6],
                "last_error": row[7],
                "next_retry_at": row[8],
            }
        )
    return out


def replay_dead_dispatch(ticket_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        UPDATE pending_dispatches
        SET status='PENDING', updated_at=?, retry_count=0, next_retry_at=?
        WHERE ticket_id=? AND status='DEAD'
        """,
        (now, now, ticket_id),
    )
    changed = c.rowcount
    conn.commit()
    conn.close()
    if changed <= 0:
        return None

    for row in list_pending_dispatches():
        if row["ticket_id"] == ticket_id:
            return row
    return None


def clear_pending_dispatches() -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM pending_dispatches")
    conn.commit()
    conn.close()


def save_execution_receipt(
    ticket_id: str,
    command_id: str,
    status: str,
    payload: Dict[str, Any],
) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO execution_receipts
        (ticket_id, command_id, status, payload, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ticket_id, command_id, status, json.dumps(payload, ensure_ascii=True), time.time()),
    )
    conn.commit()
    conn.close()


def get_execution_receipt(ticket_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT ticket_id, command_id, status, payload, created_at
        FROM execution_receipts
        WHERE ticket_id=?
        """,
        (ticket_id,),
    )
    row = c.fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "ticket_id": row[0],
        "command_id": row[1],
        "status": row[2],
        "payload": json.loads(row[3]) if row[3] else {},
        "created_at": row[4],
    }


def clear_execution_receipts() -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM execution_receipts")
    conn.commit()
    conn.close()


def save_scheduler_status(
    scheduler_name: str,
    last_cycle_time: float,
    last_cycle_summary: Dict[str, Any],
) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO scheduler_status
        (scheduler_name, last_cycle_time, last_cycle_summary)
        VALUES (?, ?, ?)
        """,
        (
            scheduler_name,
            last_cycle_time,
            json.dumps(last_cycle_summary, ensure_ascii=True),
        ),
    )
    conn.commit()
    conn.close()


def get_scheduler_status(scheduler_name: str) -> Dict[str, Any]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT last_cycle_time, last_cycle_summary
        FROM scheduler_status
        WHERE scheduler_name=?
        """,
        (scheduler_name,),
    )
    row = c.fetchone()
    conn.close()
    if row is None:
        return {
            "last_cycle_time": None,
            "last_cycle_summary": None,
        }
    return {
        "last_cycle_time": row[0],
        "last_cycle_summary": json.loads(row[1]) if row[1] else None,
    }


def count_events() -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM events")
    row = c.fetchone()
    conn.close()
    return int(row[0] or 0)


def count_executed() -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM executed_commands")
    row = c.fetchone()
    conn.close()
    return int(row[0] or 0)


def count_pending_dispatches() -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM pending_dispatches WHERE status = 'PENDING'")
    row = c.fetchone()
    conn.close()
    return int(row[0] or 0)


def count_dead_dispatches() -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM pending_dispatches WHERE status = 'DEAD'")
    row = c.fetchone()
    conn.close()
    return int(row[0] or 0)
