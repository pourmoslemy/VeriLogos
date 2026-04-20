#!/usr/bin/env python3
"""
Backtest runner for VeriLogos topology analysis.
Reads historical OHLCV data from historical_data/*.csv and runs full pipeline.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path (examples/ → VeriLogos/)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from verilogos.backtest.engine import BacktestRunner


async def main():
    # 1. Setup paths
    data_dir = project_root / "historical_data"
    output_dir = project_root / "backtest_results"
    output_dir.mkdir(exist_ok=True)

    # 2. Find all CSV files
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        print(f"❌ No CSV files found in {data_dir}")
        return 1

    print(f"📂 Found {len(csv_files)} CSV files:")
    for f in csv_files:
        print(f"   • {f.name}")

    # 3. Extract symbols from filenames (btc_usdt.csv → BTCUSDT)
    symbols = []
    for f in csv_files:
        base = f.stem.replace("_", "").upper()
        symbols.append(base)

    print(f"\n🎯 Symbols: {', '.join(symbols)}")

    # 4. Configure and run backtest
    print(f"\n🚀 Starting backtest...")
    print(f"   Date range: 2025-01-01 to 2026-04-15")
    print(f"   Interval: 1h")
    print(f"   Window: 50 ticks")
    print(f"   Correlation threshold: 0.6")
    print(f"   Output: {output_dir}/")
    print()

    runner = BacktestRunner(
        symbols=symbols,
        start_date="2025-01-01",
        end_date="2026-04-15",
        interval="1h",
        window_size=50,
        correlation_threshold=0.6,
        output_dir=str(output_dir)
    )

    try:
        results = await runner.run()

        if results and "error" not in results:
            print(f"\n✅ Backtest complete!")
            print(f"\n📊 Results saved to:")
            print(f"   • {output_dir}/snapshots.csv")
            print(f"   • {output_dir}/alerts.csv")
            print(f"   • {output_dir}/regime_history.csv")
            print(f"   • {output_dir}/summary.txt")
        else:
            print(f"\n❌ Backtest failed: {results.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"\n❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
