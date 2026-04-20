"""Live integration test for TopologyEngine with Nobitex + Wallex sources."""

import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from verilogos.application.engines import TopologyEngine
from verilogos.application.models import MarketTick, MonitorConfig
from verilogos.application.sources import NobitexSource, SourceManager, WallexSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    config = MonitorConfig(
        symbols=["BTCIRT", "ETHIRT", "USDTIRT", "XRPIRT", "ADAIRT", "SOLIRT"],
        window_size=20,
        min_ticks=5,
        analysis_interval=0.3,
        adaptive_threshold=True,
        change_sensitivity=1.5,
        history_length=200,
    )

    engine = TopologyEngine(config)
    symbols = getattr(config, "symbols", [])

    nobitex = NobitexSource(symbols=symbols, poll_interval=0.8)
    wallex = WallexSource(symbols=symbols, poll_interval=0.8)

    tick_count = 0
    snapshot_seen = 0
    target_ticks = 200
    report_every = 20

    async def feed(tick: MarketTick):
        nonlocal tick_count, snapshot_seen

        tick_count += 1
        process_tick = getattr(engine, "process_tick", None)
        snapshot = process_tick(tick) if callable(process_tick) else None

        latest_snapshot = getattr(engine, "latest_snapshot", None)
        snapshots = getattr(engine, "snapshots", [])
        current_count = len(snapshots) if isinstance(snapshots, list) else 0

        if latest_snapshot is not None and current_count > snapshot_seen:
            snapshot_seen = current_count
            betti_numbers = getattr(latest_snapshot, "betti_numbers", {})
            euler_characteristic = getattr(latest_snapshot, "euler_characteristic", "?")
            regime = getattr(latest_snapshot, "regime", None)
            regime_value = getattr(regime, "value", "?")

            print(
                f"  SNAP #{current_count:>3d} | Betti={betti_numbers} | "
                f"Euler={euler_characteristic} | Regime={regime_value}"
            )

        if snapshot is not None:
            alerts = getattr(engine, "alerts", [])
            if isinstance(alerts, list) and alerts:
                last_alert = alerts[-1]
                alert_message = getattr(last_alert, "message", "")
                alert_severity = getattr(getattr(last_alert, "severity", None), "value", "?")
                print(f"  ALERT [{alert_severity}] {alert_message}")

        if tick_count % report_every == 0:
            summary_fn = getattr(engine, "summary", None)
            status = summary_fn() if callable(summary_fn) else {}
            print(
                f"\n  STATUS @{tick_count} ticks | "
                f"snapshots={status.get('total_snapshots', '?')} | "
                f"alerts={status.get('total_alerts', '?')} | "
                f"regime={status.get('current_regime', '?')} | "
                f"corr_ready={status.get('correlation_ready', '?')}\n"
            )

    manager = SourceManager(sources=[nobitex, wallex], callback=feed)

    print("=" * 72)
    print("VeriLogos Live Engine Test")
    print(f"Collecting ~{target_ticks} ticks from Nobitex + Wallex")
    print("=" * 72)

    started = False
    started_at = time.time()
    timeout = 240

    try:
        await manager.start()
        started = True
        print("SourceManager started; waiting for live ticks...\n")

        while tick_count < target_ticks and (time.time() - started_at) < timeout:
            await asyncio.sleep(0.5)

    finally:
        if started:
            await manager.stop()
        await asyncio.sleep(0.2)

        elapsed = time.time() - started_at
        summary_fn = getattr(engine, "summary", None)
        status = summary_fn() if callable(summary_fn) else {}
        latest_snapshot = getattr(engine, "latest_snapshot", None)
        alerts = getattr(engine, "alerts", [])

        print("\n" + "=" * 72)
        print("FINAL SUMMARY")
        print(f"Ticks received: {tick_count}")
        print(f"Elapsed: {elapsed:.1f}s")
        print(f"Total snapshots: {status.get('total_snapshots', '?')}")
        print(f"Total alerts: {status.get('total_alerts', '?')}")
        print(f"Current regime: {status.get('current_regime', '?')}")
        print(f"Correlation ready: {status.get('correlation_ready', '?')}")

        if latest_snapshot is not None:
            print(f"Last Betti: {getattr(latest_snapshot, 'betti_numbers', {})}")
            print(f"Last Euler: {getattr(latest_snapshot, 'euler_characteristic', '?')}")
            last_regime = getattr(getattr(latest_snapshot, 'regime', None), 'value', '?')
            print(f"Last regime: {last_regime}")

        if isinstance(alerts, list) and alerts:
            print("\nRecent alerts:")
            for alert in alerts[-10:]:
                sev = getattr(getattr(alert, "severity", None), "value", "?")
                msg = getattr(alert, "message", "")
                print(f"  [{sev}] {msg}")
        print("=" * 72)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting cleanly.")
