from shared.schemas import StrategyIntent
from local_box.runner import run_intent
import local_box.normalize.command_normalizer as normalizer


def build_intent():
    return StrategyIntent(
        strategy_id="test",
        version="v1",
        payload={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "qty": 0.01,
            "price": 100,
            "stop_loss": 90,
            "leverage": 2,
            "mode": "simulate",
        },
    )


print("\n=== TEST 1: 正常执行 ===")
normalizer.new_command_id = lambda: "cmd_ack_test_001"
intent = build_intent()
r1 = run_intent(intent)
print(r1["status"], r1["stage"])

print("\n=== TEST 2: 重复执行（应拦截）===")
r2 = run_intent(intent)
print(r2["status"], r2["stage"], r2.get("reason"))

print("\n=== TEST 3: 模拟中断恢复 ===")
# 手动改 runner，在 send_ticket 后 raise Exception 测一次
print("👉 请手动插入 CRASH 再测试")
