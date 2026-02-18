import os
import sys
import asyncio
from sqlalchemy import text
from app.workers.command_worker import engine

async def run_strict_check():
    if os.getenv("SYSTEM_MODE_STRICT_CHECK", "1") != "1":
        return

    async with engine.begin() as conn:

        # 1. commands 表不应存在
        result = await conn.execute(
            text("SELECT to_regclass('public.commands')")
        )
        if result.scalar():
            print("FATAL: legacy 'commands' table exists.")
            sys.exit(1)

        # 2. commands_domain 必须存在
        result = await conn.execute(
            text("SELECT to_regclass('public.commands_domain')")
        )
        if not result.scalar():
            print("FATAL: commands_domain table missing.")
            sys.exit(1)

        # 3. trades 必须存在
        result = await conn.execute(
            text("SELECT to_regclass('public.trades')")
        )
        if not result.scalar():
            print("FATAL: trades table missing.")
            sys.exit(1)

    exec_mode = os.getenv("EXEC_MODE", "")
    next_mode = os.getenv("NEXT_PUBLIC_EXEC_MODE", "")

    if exec_mode and next_mode and exec_mode != next_mode:
        print("FATAL: EXEC_MODE mismatch.")
        sys.exit(1)
