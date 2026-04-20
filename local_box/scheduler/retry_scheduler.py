import os
import time

from local_box.audit.event_store import (
    count_dead_dispatches,
    count_pending_dispatches,
    get_scheduler_status as get_scheduler_status_from_db,
    save_scheduler_status,
)
from local_box.runner import recover_pending_dispatches


RETRY_SCHEDULER_INTERVAL_SEC = float(os.getenv("RETRY_SCHEDULER_INTERVAL_SEC", "2"))
RETRY_SCHEDULER_RUN_ONCE = os.getenv("RETRY_SCHEDULER_RUN_ONCE", "0") == "1"
SCHEDULER_NAME = "retry_scheduler"


def run_retry_cycle() -> dict:
    before_pending = count_pending_dispatches()
    before_dead = count_dead_dispatches()
    recovered = recover_pending_dispatches()
    after_pending = count_pending_dispatches()
    after_dead = count_dead_dispatches()

    summary = {
        "before_pending": before_pending,
        "before_dead": before_dead,
        "recovered": recovered,
        "after_pending": after_pending,
        "after_dead": after_dead,
    }
    save_scheduler_status(
        scheduler_name=SCHEDULER_NAME,
        last_cycle_time=time.time(),
        last_cycle_summary=summary,
    )

    return summary


def get_scheduler_status() -> dict:
    return get_scheduler_status_from_db(SCHEDULER_NAME)


def main() -> None:
    while True:
        summary = run_retry_cycle()
        print(f"[retry-scheduler] {summary}", flush=True)

        if RETRY_SCHEDULER_RUN_ONCE:
            return

        time.sleep(RETRY_SCHEDULER_INTERVAL_SEC)


if __name__ == "__main__":
    main()
