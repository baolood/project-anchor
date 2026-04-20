from shared.schemas import ExecMode, NormalizedCommand, Stage, StageResult, Status


ALLOWED_SIDES = {"BUY", "SELL"}


def evaluate_policy(cmd: NormalizedCommand) -> StageResult:
    if cmd.side not in ALLOWED_SIDES:
        return StageResult(
            stage=Stage.POLICY,
            status=Status.REJECTED,
            reason="INVALID_SIDE",
            data={"command_id": cmd.command_id, "side": cmd.side},
        )

    if not cmd.symbol:
        return StageResult(
            stage=Stage.POLICY,
            status=Status.REJECTED,
            reason="MISSING_SYMBOL",
            data={"command_id": cmd.command_id},
        )

    if cmd.mode == ExecMode.LIVE:
        return StageResult(
            stage=Stage.POLICY,
            status=Status.REJECTED,
            reason="LIVE_DISABLED",
            data={"command_id": cmd.command_id},
        )

    return StageResult(
        stage=Stage.POLICY,
        status=Status.ACCEPTED,
        reason="ALLOW",
        data={"command_id": cmd.command_id},
    )
