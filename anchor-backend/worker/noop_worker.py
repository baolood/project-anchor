import time
import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json
WORKER_ID = os.getenv("WORKER_ID", "noop-worker-1")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

CLAIM_SQL = """
UPDATE commands_domain
SET
  status = 'PROCESSING',
  locked_by = %(worker_id)s,
  locked_at = NOW(),
  attempt = attempt + 1,
  updated_at = NOW()
WHERE id = (
  SELECT id
  FROM commands_domain
  WHERE status = 'PENDING'
  ORDER BY created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
"""

DONE_SQL = """
UPDATE commands_domain
SET
  status = 'DONE',
  result = %(result)s,
  updated_at = NOW()
WHERE id = %(id)s
  AND locked_by = %(worker_id)s;
"""

def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(CLAIM_SQL, {"worker_id": WORKER_ID})
            command = cur.fetchone()

            if not command:
                conn.rollback()
                print("[noop-worker] No PENDING command. Exit.")
                return

            print(f"[noop-worker] Claimed command {command['id']}")
            conn.commit()

        # 模拟执行
        time.sleep(1)

        with conn.cursor() as cur:
            cur.execute(
                DONE_SQL,
                {
                    "id": command["id"],
                    "worker_id": WORKER_ID,
                    "result": Json({"noop": True})
                }
            )
            conn.commit()
            print(f"[noop-worker] DONE command {command['id']}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()