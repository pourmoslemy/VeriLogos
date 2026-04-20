#!/usr/bin/env python3
"""
VeriLogos Engine — Real Data Explorer
Feeds historical CSV data into TopologyEngine and prints
ALL outputs beyond just Betti numbers.
"""
import sys, time
import logging
import numpy as np
import pandas as pd
from pathlib import Path

# ██ VeriLogos imports ██
from verilogos.application.models import (
    MonitorConfig, MarketTick, MarketRegime, AlertSeverity,
)
from verilogos.application.engines import TopologyEngine

logger = logging.getLogger("TopologyMonitor")


# ─────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────
def load_historical_data(data_dir: str = "../historical_data") -> dict[str, pd.DataFrame]:
    """Load all *_usdt.csv files into {symbol: DataFrame}."""
    candidates = [
        Path(data_dir),
        Path("historical_data"),
        Path("../historical_data"),
        Path("../../historical_data"),
    ]
    data_path = None
    for p in candidates:
        if p.exists():
            data_path = p
            break

    if data_path is None:
        print("⚠️  Could not find historical_data directory. Tried:")
        for p in candidates:
            print(f"   - {p.resolve()}")
        sys.exit(1)

    files = sorted(data_path.glob("*_usdt.csv"))
    if not files:
        print(f"⚠️  No *_usdt.csv files found in {data_path}")
        sys.exit(1)

    data: dict[str, pd.DataFrame] = {}
    for f in files:
        symbol = f.stem.upper().replace("_", "")
        df = pd.read_csv(f)

        required = {"timestamp", "close"}
        if not required.issubset(df.columns):
            print(f"  ✖  Skipping {f.name}: missing columns {required - set(df.columns)}")
            continue

        if "volume" not in df.columns:
            df["volume"] = 0.0

        data[symbol] = df
        print(f"  ✅ {symbol:12s} — {len(df):>6,} rows")

    print(f"\n  Total symbols: {len(data)}")
    return data


def interleave_ticks(
    data: dict[str, pd.DataFrame],
    limit: int | None = None,
) -> list[MarketTick]:
    """Merge all symbols into a single time-sorted tick stream."""
    ticks: list[MarketTick] = []
    for symbol, df in data.items():
        for _, row in df.iterrows():
            ticks.append(MarketTick(
                symbol=symbol,
                timestamp=float(row["timestamp"]),
                price=float(row["close"]),
                volume=float(row.get("volume", 0.0)),
            ))

    ticks.sort(key=lambda t: t.timestamp)
    if limit:
        ticks = ticks[:limit]
    return ticks


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────
def safe_betti_vector(snapshot, dim: int = 3) -> list[int]:
    """Return betti vector; fall back if method missing."""
    if hasattr(snapshot, "betti_vector") and callable(snapshot.betti_vector):
        try:
            return snapshot.betti_vector(dim)
        except Exception:
            pass
    # manual fallback
    return [snapshot.betti_numbers.get(i, 0) for i in range(dim)]


def regime_symbol(regime: MarketRegime) -> str:
    """Emoji hint per regime."""
    return {
        MarketRegime.STABLE:        "🟢",
        MarketRegime.VOLATILE:      "🟡",
        MarketRegime.TRANSITIONING: "🟠",
        MarketRegime.CRISIS:        "🔴",
    }.get(regime, "⚪")


# ─────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────
def run_exploration(tick_limit: int | None = None):
    data = load_historical_data()
    if not data:
        print("⚠️  No data loaded. Exiting.")
        sys.exit(1)

    symbols = list(data.keys())

    config = MonitorConfig(
        symbols=symbols,
        min_ticks=30,
        history_length=20,
        adaptive_threshold=True,
        threshold_percentile=75.0,
        correlation_threshold=0.5,
        change_sensitivity=1.5,
    )

    engine = TopologyEngine(config)
    ticks = interleave_ticks(data, limit=tick_limit)

    print(f"\n  Ticks to process : {len(ticks):,}")
    print(f"{'=' * 70}\n")

    snapshot_count = 0
    alert_count    = 0
    regimes_seen: set[MarketRegime] = set()
    betti_history:  list[dict]  = []
    euler_history:  list[int]   = []
    regime_changes: list[tuple] = []   # (tick#, old, new)

    t0 = time.perf_counter()

    for i, tick in enumerate(ticks):
        try:
            result = engine.process_tick(tick)
        except Exception as e:
            logger.error(f"[PERSIST] FAILED: {e}", exc_info=True)
            continue
        if result is None:
            continue

        snapshot, alert = result
        snapshot_count += 1
        regimes_seen.add(snapshot.regime)
        betti_history.append(snapshot.betti_numbers.copy())
        euler_history.append(snapshot.euler_characteristic)

        # ── Print every 50th snapshot (+ first 3) ──
        if snapshot_count % 50 == 1 or snapshot_count <= 3:
            rs = regime_symbol(snapshot.regime)
            print(f"██ Snapshot #{snapshot_count:<5}  tick #{i:<6} ██")
            print(f"   timestamp      : {snapshot.timestamp}")
            print(f"   regime         : {rs} {snapshot.regime.value}")
            print(f"   betti_numbers  : {snapshot.betti_numbers}")
            print(f"   betti_vec(3)   : {safe_betti_vector(snapshot, 3)}")
            print(f"   euler χ        : {snapshot.euler_characteristic}")
            print(f"   num_simplices  : {snapshot.num_simplices}")
            print(f"   max_dimension  : {snapshot.max_dimension}")
            if hasattr(snapshot, "correlation_threshold"):
                print(f"   corr_threshold : {snapshot.correlation_threshold:.4f}")
            print()

        # ── Print ALL alerts ──
        if alert is not None:
            alert_count += 1
            regime_changes.append((i, alert.old_regime, alert.new_regime))

            old_s = regime_symbol(alert.old_regime)
            new_s = regime_symbol(alert.new_regime)
            print(f"  ⚡ ALERT #{alert_count}")
            print(f"     severity     : {alert.severity.value}")
            print(f"     message      : {alert.message}")
            print(f"     regime shift : {old_s} {alert.old_regime.value}"
                  f"  →  {new_s} {alert.new_regime.value}")
            print(f"     Δ betti      : {alert.betti_change}")
            print(f"     Δ euler (Δχ) : {alert.euler_change}")
            print()

    elapsed = time.perf_counter() - t0

    # ── Summary ──
    print(f"{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Ticks processed   : {len(ticks):,}")
    print(f"  Snapshots created : {snapshot_count:,}")
    print(f"  Alerts fired      : {alert_count}")
    print(f"  Regimes observed  : {sorted(r.value for r in regimes_seen)}")
    print(f"  Time elapsed      : {elapsed:.2f}s")
    if elapsed > 0:
        print(f"  Throughput        : {len(ticks) / elapsed:,.0f} ticks/sec")

    # ── Euler stats ──
    if euler_history:
        arr = np.array(euler_history)
        print(f"\n  Euler χ stats:")
        print(f"    mean={arr.mean():.2f}  std={arr.std():.2f}  "
              f"min={arr.min()}  max={arr.max()}")

    # ── Betti stats ──
    if betti_history:
        b0 = [b.get(0, 0) for b in betti_history]
        b1 = [b.get(1, 0) for b in betti_history]
        b2 = [b.get(2, 0) for b in betti_history]
        print(f"\n  β₀ (components) : mean={np.mean(b0):.2f}  std={np.std(b0):.2f}  "
              f"min={min(b0)}  max={max(b0)}")
        print(f"  β₁ (loops)      : mean={np.mean(b1):.2f}  std={np.std(b1):.2f}  "
              f"min={min(b1)}  max={max(b1)}")
        print(f"  β₂ (voids)      : mean={np.mean(b2):.2f}  std={np.std(b2):.2f}  "
              f"min={min(b2)}  max={max(b2)}")

    # ── Regime transition log ──
    if regime_changes:
        print(f"\n  Regime transitions ({len(regime_changes)}):")
        for tick_num, old_r, new_r in regime_changes:
            print(f"    tick {tick_num:>6}  "
                  f"{regime_symbol(old_r)} {old_r.value:14s} → "
                  f"{regime_symbol(new_r)} {new_r.value}")

    print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(name)s|%(message)s")
    # Optional: limit ticks for faster first run
    # run_exploration(tick_limit=1000)
    run_exploration()
