from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import time
import uuid


# =========================
# Enums
# =========================

class Stage(str, Enum):
    NORMALIZATION = "NORMALIZATION"
    RISK = "RISK"
    POLICY = "POLICY"
    EXECUTION_GATE = "EXECUTION_GATE"
    EXECUTOR = "EXECUTOR"


class ExecMode(str, Enum):
    SIMULATE = "simulate"
    TESTNET = "testnet"
    LIVE = "live"  # 禁用（第一阶段不允许）


class Status(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DONE = "DONE"
    FAILED = "FAILED"


# =========================
# Core Command
# =========================

@dataclass
class StrategyIntent:
    strategy_id: str
    version: str
    payload: Dict[str, Any]


@dataclass
class NormalizedCommand:
    command_id: str
    strategy_id: str
    strategy_version: str

    symbol: str
    side: str  # BUY / SELL
    qty: float
    price: Optional[float]

    stop_loss: float
    leverage: int

    mode: ExecMode

    timestamp: float = field(default_factory=lambda: time.time())


# =========================
# Stage Result
# =========================

@dataclass
class StageResult:
    stage: Stage
    status: Status
    reason: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# =========================
# Execution Ticket (核心安全边界)
# =========================

@dataclass
class ExecutionTicket:
    ticket_id: str
    command_id: str

    symbol: str
    side: str
    qty: float
    price: Optional[float]

    mode: ExecMode

    issued_at: float
    signature: str  # 简化版，后续可升级 HMAC


# =========================
# Execution Result
# =========================

@dataclass
class ExecutionResult:
    ticket_id: str
    status: Status
    filled_qty: float = 0.0
    avg_price: Optional[float] = None
    message: Optional[str] = None


# =========================
# Event (审计核心)
# =========================

@dataclass
class Event:
    event_id: str
    command_id: str
    stage: Stage
    status: Status
    timestamp: float
    payload: Dict[str, Any]


# =========================
# Helpers
# =========================

def new_command_id() -> str:
    return f"cmd_{uuid.uuid4().hex[:12]}"


def new_ticket_id() -> str:
    return f"tkt_{uuid.uuid4().hex[:12]}"


def new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"
