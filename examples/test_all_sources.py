#!/usr/bin/env python3
# examples/test_all_sources.py
"""Smoke test: fetch ticks from Nobitex, Wallex, and KuCoin."""

import asyncio
import sys
import os
import logging

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from verilogos.application.sources.nobitex import NobitexSource
from verilogos.application.sources.wallex import WallexSource
from verilogos.application.sources.kucoin import KuCoinSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def test_source(source, rounds=2, delay=3.0):
    """Test a single source."""
    print(f"\n{'─' * 50}")
    print(f"  Testing: {source.name}")
    print(f"{'─' * 50}")

    await source.start()
    try:
        for i in range(rounds):
            ticks = await source.fetch_ticks()
            if not ticks:
                print(f"  Round {i+1}: ⚠ No ticks")
            else:
                print(f"  Round {i+1}: {len(ticks)} ticks")
                for t in ticks[:5]:  # show max 5
                    print(f"    {t.symbol:<12s} price={t.price:>16,.2f}  vol={t.volume:.4f}")
                if len(ticks) > 5:
                    print(f"    ... and {len(ticks) - 5} more")
            if i < rounds - 1:
                await asyncio.sleep(delay)
    finally:
        await source.stop()
        await asyncio.sleep(0.25)


async def main():
    print("=" * 60)
    print("  VeriLogos — All Sources Smoke Test")
    print("=" * 60)

    # Nobitex (IRT pairs)
    await test_source(
        NobitexSource(
            symbols=["BTCIRT", "ETHIRT", "USDTIRT"],
            poll_interval=3.0,
        )
    )

    # Wallex (IRT pairs)
    await test_source(
        WallexSource(
            symbols=["BTCIRT", "ETHIRT", "USDTIRT"],
            poll_interval=3.0,
        )
    )

    # KuCoin (USDT pairs)
    await test_source(
        KuCoinSource(
            symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            poll_interval=3.0,
        )
    )

    print(f"\n{'=' * 60}")
    print("  ✅ All sources tested.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()
