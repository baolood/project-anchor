from shared.schemas import StrategyIntent, NormalizedCommand, ExecMode, new_command_id


def normalize_intent(intent: StrategyIntent) -> NormalizedCommand:
    payload = intent.payload or {}

    symbol = str(payload.get("symbol") or "").strip().upper()
    side = str(payload.get("side") or "").strip().upper()
    qty = float(payload.get("qty") or 0.0)

    price = payload.get("price")
    if price is not None:
        price = float(price)

    stop_loss = float(payload.get("stop_loss") or 0.0)
    leverage = int(payload.get("leverage") or 1)

    mode_raw = str(payload.get("mode") or ExecMode.SIMULATE.value).strip().lower()
    mode = ExecMode(mode_raw)

    return NormalizedCommand(
        command_id=new_command_id(),
        strategy_id=intent.strategy_id,
        strategy_version=intent.version,
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
        stop_loss=stop_loss,
        leverage=leverage,
        mode=mode,
    )
