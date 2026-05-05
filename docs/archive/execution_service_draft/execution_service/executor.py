from shared.schemas import ExecutionTicket, ExecutionResult, Status
import random


def execute_simulate(ticket: ExecutionTicket) -> ExecutionResult:
    # 模拟成交
    fill_price = ticket.price or random.uniform(100, 110)

    return ExecutionResult(
        ticket_id=ticket.ticket_id,
        status=Status.DONE,
        filled_qty=ticket.qty,
        avg_price=fill_price,
        message="SIMULATED"
    )


def execute_testnet(ticket: ExecutionTicket) -> ExecutionResult:
    # 第一阶段不接交易所，直接模拟
    return ExecutionResult(
        ticket_id=ticket.ticket_id,
        status=Status.DONE,
        filled_qty=ticket.qty,
        avg_price=ticket.price,
        message="TESTNET-MOCK"
    )
