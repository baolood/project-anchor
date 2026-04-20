from shared.schemas import NormalizedCommand, Stage, StageResult, Status


MAX_LEVERAGE = 20
REQUIRE_STOP_LOSS = True


def evaluate_risk(cmd: NormalizedCommand) -> StageResult:
    if REQUIRE_STOP_LOSS and not cmd.stop_loss:
        return StageResult(
            stage=Stage.RISK,
            status=Status.REJECTED,
            reason="STOP_LOSS_REQUIRED",
            data={"command_id": cmd.command_id, "symbol": cmd.symbol},
        )

    if cmd.qty <= 0:
        return StageResult(
            stage=Stage.RISK,
            status=Status.REJECTED,
            reason="INVALID_QTY",
            data={"command_id": cmd.command_id, "qty": cmd.qty},
        )

    if cmd.leverage > MAX_LEVERAGE:
        return StageResult(
            stage=Stage.RISK,
            status=Status.REJECTED,
            reason="LEVERAGE_TOO_HIGH",
            data={"command_id": cmd.command_id, "leverage": cmd.leverage, "limit": MAX_LEVERAGE},
        )

    return StageResult(
        stage=Stage.RISK,
        status=Status.ACCEPTED,
        reason="ALLOW",
        data={"command_id": cmd.command_id},
    )
