#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insert a sample pending ``order`` row into Postgres ``commands``.

Requires psycopg. Credentials come from environment; **nothing is shipped as hard-coded secrets.**

``ANCHOR_DB_PASSWORD`` is required. Optional (with localhost-friendly defaults):

- ``ANCHOR_DB_HOST`` (default ``localhost``)
- ``ANCHOR_DB_PORT`` (default ``5432``)
- ``ANCHOR_DB_NAME`` (default ``anchor``)
- ``ANCHOR_DB_USER`` (default ``anchor``)

Example:

    export ANCHOR_DB_PASSWORD='…'
    python3 anchor-backend/scripts/insert_order_command.py
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import psycopg


def env_password() -> str:
    v = os.environ.get("ANCHOR_DB_PASSWORD")
    if not v:
        raise SystemExit(
            "ANCHOR_DB_PASSWORD is required (export it in your shell; do not commit it)."
        )
    return v


def connect():
    host = os.environ.get("ANCHOR_DB_HOST", "localhost")
    port = int(os.environ.get("ANCHOR_DB_PORT", "5432"))
    dbname = os.environ.get("ANCHOR_DB_NAME", "anchor")
    user = os.environ.get("ANCHOR_DB_USER", "anchor")
    return psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=env_password(),
    )


payload = {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "notional": 100,
}

sql_insert = """
INSERT INTO commands (id, type, payload, status, created_at)
VALUES (%s, %s, %s, %s, %s);
"""


def main() -> None:
    conn = connect()
    try:
        cmd_id = str(uuid.uuid4())
        cur = conn.cursor()
        cur.execute(
            sql_insert,
            (
                cmd_id,
                "order",
                json.dumps(payload),
                "pending",
                datetime.now(timezone.utc),
            ),
        )
        conn.commit()
        cur.close()
        print(f"[OK] Inserted order command with id={cmd_id}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
