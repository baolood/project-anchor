# small utility to be run inside container for quick manual inspect/set
import asyncio, sys, json
from app.system.risk_state import get_risk_state, set_risk_state

async def main():
    cmd = sys.argv[1]
    if cmd == "get":
        key = sys.argv[2]
        v = await get_risk_state(key)
        print(json.dumps(v, ensure_ascii=False, indent=2))
    elif cmd == "set":
        key = sys.argv[2]; val = json.loads(sys.argv[3])
        await set_risk_state(key, val, actor="cli")
        print("OK")
    else:
        print("usage: python -m app.system.risk_state_cli get <key> | set <key> '<json>'")

if __name__ == "__main__":
    asyncio.run(main())
