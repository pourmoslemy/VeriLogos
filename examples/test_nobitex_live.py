#!/usr/bin/env python3
# examples/test_nobitex_live.py
"""
Quick smoke test: fetch 3 rounds of ticks from Nobitex.

Usage:
    cd VeriLogos
    python -m examples.test_nobitex_live

    # or directly:
    python examples/test_nobitex_live.py
"""

import asyncio
import sys
import os
import logging

# Ensure project root is on sys.path when running directly
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from verilogos.application.sources.nobitex import NobitexSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────
SYMBOLS = ["BTCIRT", "ETHIRT", "USDTIRT"]
POLL_INTERVAL = 5.0
ROUNDS = 3


async def main():
    print("=" * 60)
    print("  VeriLogos — Nobitex Live Smoke Test")
    print("=" * 60)
    print(f"  Symbols : {SYMBOLS}")
    print(f"  Interval: {POLL_INTERVAL}s")
    print(f"  Rounds  : {ROUNDS}")
    print("=" * 60)

    source = NobitexSource(
        symbols=SYMBOLS,
        poll_interval=POLL_INTERVAL,
    )

    await source.start()

    try:
        for i in range(ROUNDS):
            print(f"\n── Round {i + 1}/{ROUNDS} ──")
            ticks = await source.fetch_ticks()

            if not ticks:
                print("  ⚠ No ticks received")
            else:
                for t in ticks:
                    print(
                        f"  {t.symbol:<10s}  "
                        f"price={t.price:>16,.0f} T   "
                        f"vol={t.volume:.4f}"
                    )

            if i < ROUNDS - 1:
                print(f"  ⏳ waiting {POLL_INTERVAL}s ...")
                await asyncio.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n  ⛔ Interrupted by user")
    finally:
        await source.stop()
        # Give aiohttp time to clean up transports
        await asyncio.sleep(0.25)

    print("\n✅ Done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        # Shut down async generators and close gracefully
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()
