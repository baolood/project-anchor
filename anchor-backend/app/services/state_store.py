from dataclasses import dataclass
from datetime import datetime
import redis
from app.settings import settings
from app.core.enums import EngineStatus, RiskReason

r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def _k(user_id: str, key: str) -> str:
    return f"anchor:{user_id}:{key}"

@dataclass
class EngineState:
    status: EngineStatus
    last_reason: RiskReason
    cooldown_until: datetime | None
    manual_24h_count: int

class StateStore:
    def get_state(self, user_id: str) -> EngineState:
        status = r.get(_k(user_id, "engine_status")) or EngineStatus.STOPPED.value
        reason = r.get(_k(user_id, "last_risk_reason")) or RiskReason.NONE.value
        cooldown_raw = r.get(_k(user_id, "cooldown_until"))
        manual = r.get(_k(user_id, "manual_24h_count")) or "0"

        cooldown_until = None
        if cooldown_raw:
            cooldown_until = datetime.fromisoformat(cooldown_raw)

        return EngineState(
            status=EngineStatus(status),
            last_reason=RiskReason(reason),
            cooldown_until=cooldown_until,
            manual_24h_count=int(manual),
        )

    def set_status(self, user_id: str, status: EngineStatus, reason: RiskReason = RiskReason.NONE):
        r.set(_k(user_id, "engine_status"), status.value)
        r.set(_k(user_id, "last_risk_reason"), reason.value)
