#!/usr/bin/env python3
"""Backtest engine for VeriLogos Layer 4."""

import argparse
import asyncio
import csv
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from verilogos.application.engines import TopologyEngine
from verilogos.application.models import (
    AlertSeverity,
    MarketRegime,
    MarketTick,
    MonitorConfig,
    TopologicalSnapshot,
)
from verilogos.application.engines import (
    CorrelationEngine,
    StructuralChangeDetector,
    TopologyAnalyzer,
    VietorisRipsBuilder,
)
from verilogos.core.reasoning.persistence.persistence_engine import PersistenceEngine

HAS_TOPOLOGY = True
IMPORT_ERROR_MSG = ""

"""
Backtest Engine for Topological Market Analysis
================================================
Multi-source historical data → TopologyEngine replay → CSV reports

Fallback chain: Binance REST → CoinGecko → CryptoCompare → Local CSV

Uses CorrelationEngine + TopologyAnalyzer + StructuralChangeDetector
directly from real_time_topology_monitor.py (no TopologyEngine dependency).
"""

import asyncio
import argparse
import csv
import logging
import sys
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from collections import deque

import numpy as np

# ─── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backtest_engine")

# ─── Inline TopologyEngine (wrapper) ──────────────────────
if HAS_TOPOLOGY:
    class TopologyEngine:
        """
        Lightweight wrapper that combines:
          - CorrelationEngine  (rolling price windows → correlation matrix)
          - TopologyAnalyzer   (correlation → VR complex → Betti/Euler)
          - StructuralChangeDetector (regime classification + alerts)

        API: process_tick(tick) → (TopologicalSnapshot, Optional[StructuralAlert]) | None
        """

        def __init__(self, config: MonitorConfig):
            self.config = config
            self.symbols = config.symbols

            # ✅ All three take config: MonitorConfig
            self.correlation_engine = CorrelationEngine(config)
            self.topology_analyzer = TopologyAnalyzer(config)
            self.change_detector = StructuralChangeDetector(config)

            self._tick_count = 0
            self._last_snapshot: Optional[TopologicalSnapshot] = None

        def process_tick(self, tick: MarketTick):
            """
            Feed a tick → update correlation → build topology → detect regime change.

            Returns:
                tuple(TopologicalSnapshot, Optional[StructuralAlert])  — if ready
                None                                                    — if warming up
            """
            # 1) Update correlation rolling windows
            self.correlation_engine.update(tick)
            self._tick_count += 1

            # 2) Check readiness
            if not self.correlation_engine.is_ready():
                return None

            # 3) Compute correlation matrix
            corr = self.correlation_engine.compute_correlation_matrix()

            # 4) Build simplicial complex + extract topological invariants
            snapshot = self.topology_analyzer.analyze(
                corr_matrix=corr,
                threshold=self.config.correlation_threshold,
                timestamp=tick.timestamp,
            )

            # 5) Detect structural change (CUSUM-based)
            alert = self.change_detector.update(snapshot)

            self._last_snapshot = snapshot
            return snapshot, alert

        

# ═══════════════════════════════════════════════════════════
#  DATA SOURCES (Fallback Chain)
# ═══════════════════════════════════════════════════════════

class DataSourceStatus(Enum):
    OK = "ok"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class HistoricalBar:
    """One OHLCV bar from any source."""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str


class BaseHistoricalSource:
    """Abstract base for historical data sources."""
    name: str = "base"
    priority: int = 0

    async def fetch(
        self, symbol: str, start_ts: float, end_ts: float, interval: str = "1h"
    ) -> Tuple[List[HistoricalBar], DataSourceStatus]:
        raise NotImplementedError


# ─── Binance REST ──────────────────────────────────────────
class BinanceHistoricalSource(BaseHistoricalSource):
    name = "Binance"
    priority = 2

    INTERVAL_MAP = {
        "1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d",
    }

    async def fetch(self, symbol: str, start_ts: float, end_ts: float, interval="1h"):
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed, Binance source unavailable")
            return [], DataSourceStatus.ERROR

        binance_symbol = symbol.replace("/", "").upper()
        binance_interval = self.INTERVAL_MAP.get(interval, "1h")
        url = "https://api.binance.com/api/v3/klines"

        bars = []
        current_start = int(start_ts * 1000)
        end_ms = int(end_ts * 1000)

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            ) as session:
                while current_start < end_ms:
                    params = {
                        "symbol": binance_symbol,
                        "interval": binance_interval,
                        "startTime": current_start,
                        "endTime": end_ms,
                        "limit": 1000,
                    }
                    async with session.get(url, params=params) as resp:
                        if resp.status == 451:
                            logger.warning("Binance: HTTP 451 — geo-blocked")
                            return [], DataSourceStatus.BLOCKED
                        if resp.status == 429:
                            logger.warning("Binance: rate limited")
                            return [], DataSourceStatus.RATE_LIMITED
                        if resp.status != 200:
                            logger.warning(f"Binance: HTTP {resp.status}")
                            return [], DataSourceStatus.ERROR

                        data = await resp.json()
                        if not data:
                            break

                        for k in data:
                            bars.append(HistoricalBar(
                                timestamp=k[0] / 1000.0,
                                open=float(k[1]),
                                high=float(k[2]),
                                low=float(k[3]),
                                close=float(k[4]),
                                volume=float(k[5]),
                                symbol=symbol,
                            ))
                        current_start = int(data[-1][0]) + 1

            logger.info(f"Binance: fetched {len(bars)} bars for {symbol}")
            return bars, DataSourceStatus.OK

        except Exception as e:
            logger.warning(f"Binance error: {e}")
            return [], DataSourceStatus.BLOCKED


# ─── CoinGecko ─────────────────────────────────────────────
class CoinGeckoHistoricalSource(BaseHistoricalSource):
    name = "CoinGecko"
    priority = 3

    SYMBOL_TO_ID = {
        "BTC/USDT": "bitcoin", "ETH/USDT": "ethereum",
        "BNB/USDT": "binancecoin", "SOL/USDT": "solana",
        "ADA/USDT": "cardano", "XRP/USDT": "ripple",
        "DOT/USDT": "polkadot", "AVAX/USDT": "avalanche-2",
        "MATIC/USDT": "matic-network", "LINK/USDT": "chainlink",
        "DOGE/USDT": "dogecoin", "ATOM/USDT": "cosmos",
        "UNI/USDT": "uniswap", "LTC/USDT": "litecoin",
        "NEAR/USDT": "near",
    }

    async def fetch(self, symbol: str, start_ts: float, end_ts: float, interval="1h"):
        try:
            import aiohttp
        except ImportError:
            return [], DataSourceStatus.ERROR

        coin_id = self.SYMBOL_TO_ID.get(symbol)
        if not coin_id:
            logger.warning(f"CoinGecko: unknown symbol {symbol}")
            return [], DataSourceStatus.ERROR

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
        params = {
            "vs_currency": "usd",
            "from": int(start_ts),
            "to": int(end_ts),
        }

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 429:
                        logger.warning("CoinGecko: rate limited")
                        return [], DataSourceStatus.RATE_LIMITED
                    if resp.status != 200:
                        logger.warning(f"CoinGecko: HTTP {resp.status}")
                        return [], DataSourceStatus.ERROR

                    data = await resp.json()
                    prices = data.get("prices", [])
                    volumes = data.get("total_volumes", [])

                    bars = []
                    for i, (ts, price) in enumerate(prices):
                        vol = volumes[i][1] if i < len(volumes) else 0.0
                        bars.append(HistoricalBar(
                            timestamp=ts / 1000.0,
                            open=price,
                            high=price,
                            low=price,
                            close=price,
                            volume=vol,
                            symbol=symbol,
                        ))

            logger.info(f"CoinGecko: fetched {len(bars)} points for {symbol}")
            return bars, DataSourceStatus.OK

        except Exception as e:
            logger.warning(f"CoinGecko error: {e}")
            return [], DataSourceStatus.ERROR


# ─── CryptoCompare ─────────────────────────────────────────
class CryptoCompareHistoricalSource(BaseHistoricalSource):
    name = "CryptoCompare"
    priority = 4

    async def fetch(self, symbol: str, start_ts: float, end_ts: float, interval="1h"):
        try:
            import aiohttp
        except ImportError:
            return [], DataSourceStatus.ERROR

        fsym = symbol.split("/")[0].upper()
        tsym = "USDT"

        interval_map = {"1h": "histohour", "1d": "histoday", "1m": "histominute"}
        endpoint = interval_map.get(interval, "histohour")
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}"

        total_seconds = end_ts - start_ts
        limit_map = {"histohour": 3600, "histoday": 86400, "histominute": 60}
        limit = min(2000, int(total_seconds / limit_map.get(endpoint, 3600)) + 1)

        params = {"fsym": fsym, "tsym": tsym, "limit": limit, "toTs": int(end_ts)}

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20)
            ) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return [], DataSourceStatus.ERROR
                    data = await resp.json()
                    if data.get("Response") != "Success":
                        return [], DataSourceStatus.ERROR

                    bars = []
                    for item in data.get("Data", {}).get("Data", []):
                        if item["time"] < start_ts:
                            continue
                        bars.append(HistoricalBar(
                            timestamp=float(item["time"]),
                            open=float(item["open"]),
                            high=float(item["high"]),
                            low=float(item["low"]),
                            close=float(item["close"]),
                            volume=float(item.get("volumeto", 0)),
                            symbol=symbol,
                        ))

            logger.info(f"CryptoCompare: fetched {len(bars)} bars for {symbol}")
            return bars, DataSourceStatus.OK

        except Exception as e:
            logger.warning(f"CryptoCompare error: {e}")
            return [], DataSourceStatus.ERROR


# ─── Local CSV ─────────────────────────────────────────────
class LocalCSVHistoricalSource(BaseHistoricalSource):
    name = "LocalCSV"
    priority = 0

    def __init__(self, data_dir: str = "./historical_data"):
        self.data_dir = Path(data_dir)

    async def fetch(self, symbol: str, start_ts: float, end_ts: float, interval="1h"):
        safe_name = symbol.replace("/", "_").lower()
        no_separator = symbol.replace("/", "").lower()
        with_quote_separator = re.sub(r"(usdt|busd|usd)$", r"_\1", no_separator)
        candidate_names = [safe_name, no_separator, with_quote_separator]
        candidate_paths = []
        for name in candidate_names:
            path = self.data_dir / f"{name}.csv"
            if path not in candidate_paths:
                candidate_paths.append(path)

        existing_paths = [path for path in candidate_paths if path.exists()]
        if not existing_paths:
            logger.warning(f"LocalCSV: file not found: {candidate_paths[0]}")
            return [], DataSourceStatus.ERROR

        try:
            for csv_path in existing_paths:
                bars = []
                with open(csv_path, "r") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

                total_rows = len(rows)
                first_ts = None
                last_ts = None
                if total_rows:
                    first_row = rows[0]
                    last_row = rows[-1]
                    first_raw = first_row.get("timestamp", first_row.get("time", 0))
                    last_raw = last_row.get("timestamp", last_row.get("time", 0))
                    try:
                        first_ts = float(first_raw)
                    except (TypeError, ValueError):
                        first_ts = None
                    try:
                        last_ts = float(last_raw)
                    except (TypeError, ValueError):
                        last_ts = None

                logger.info(
                    "LocalCSV debug: file=%s rows=%s first_ts=%s last_ts=%s requested_start_ts=%s requested_end_ts=%s",
                    csv_path,
                    total_rows,
                    first_ts,
                    last_ts,
                    start_ts,
                    end_ts,
                )

                for row in rows:
                    ts = float(row.get("timestamp", 0))
                    if ts > 1e11:
                        ts /= 1000.0
                    if ts < start_ts or ts > end_ts:
                        continue
                    bars.append(HistoricalBar(
                        timestamp=ts,
                        open=float(row.get("open", 0)),
                        high=float(row.get("high", 0)),
                        low=float(row.get("low", 0)),
                        close=float(row.get("close", 0)),
                        volume=float(row.get("volume", 0)),
                        symbol=symbol,
                    ))
                if bars:
                    logger.info(f"LocalCSV: loaded {len(bars)} bars for {symbol}")
                    return bars, DataSourceStatus.OK
            logger.info(f"LocalCSV: loaded 0 bars for {symbol}")
            return [], DataSourceStatus.OK
        except Exception as e:
            logger.warning(f"LocalCSV error: {e}")
            return [], DataSourceStatus.ERROR


# ═══════════════════════════════════════════════════════════
#  MULTI-SOURCE FETCHER (Fallback Chain)
# ═══════════════════════════════════════════════════════════

class MultiSourceFetcher:
    """Tries sources in priority order until one succeeds."""

    def __init__(self, sources: Optional[List[BaseHistoricalSource]] = None):
        if sources is None:
            sources = [
                BinanceHistoricalSource(),
                CoinGeckoHistoricalSource(),
                CryptoCompareHistoricalSource(),
                LocalCSVHistoricalSource(),
            ]
        self.sources = sorted(sources, key=lambda s: s.priority)
        self.source_status: Dict[str, DataSourceStatus] = {}

    async def fetch_symbol(
        self, symbol: str, start_ts: float, end_ts: float, interval: str = "1h"
    ) -> Tuple[List[HistoricalBar], str]:
        """Try each source in order. Return (bars, source_name)."""
        for source in self.sources:
            if self.source_status.get(source.name) == DataSourceStatus.BLOCKED:
                logger.info(f"  Skipping {source.name} (previously blocked)")
                continue

            logger.info(f"  Trying {source.name} for {symbol}...")
            bars, status = await source.fetch(symbol, start_ts, end_ts, interval)
            self.source_status[source.name] = status

            if status == DataSourceStatus.OK and len(bars) > 0:
                return bars, source.name

            if status == DataSourceStatus.RATE_LIMITED:
                logger.info(f"  {source.name} rate limited, waiting 5s...")
                await asyncio.sleep(5)
                bars, status = await source.fetch(symbol, start_ts, end_ts, interval)
                if status == DataSourceStatus.OK and len(bars) > 0:
                    return bars, source.name

        logger.error(f"  All sources failed for {symbol}")
        return [], "none"

    async def fetch_all(
        self,
        symbols: List[str],
        start_ts: float,
        end_ts: float,
        interval: str = "1h",
        delay_between: float = 1.5,
    ) -> Dict[str, List[HistoricalBar]]:
        """Fetch historical data for all symbols."""
        all_data: Dict[str, List[HistoricalBar]] = {}

        for i, symbol in enumerate(symbols):
            logger.info(f"[{i+1}/{len(symbols)}] Fetching {symbol}...")
            bars, source = await self.fetch_symbol(symbol, start_ts, end_ts, interval)
            all_data[symbol] = bars
            logger.info(f"  → {len(bars)} bars from {source}")

            if i < len(symbols) - 1 and delay_between > 0:
                await asyncio.sleep(delay_between)

        return all_data


# ═══════════════════════════════════════════════════════════
#  HISTORICAL BACKTEST FEED (DataFeedProvider compatible)
# ═══════════════════════════════════════════════════════════

class HistoricalBacktestFeed:
    """
    Replays historical bars as MarketTick objects in chronological order.
    Compatible with the DataFeedProvider interface pattern.
    """

    def __init__(self, all_bars: Dict[str, List[HistoricalBar]]):
        # Merge all bars and sort by timestamp
        self._ticks: List[MarketTick] = []
        for symbol, bars in all_bars.items():
            for bar in bars:
                self._ticks.append(MarketTick(
                    symbol=symbol,
                    price=bar.close,
                    volume=bar.volume,
                    timestamp=bar.timestamp,
                ))
        self._ticks.sort(key=lambda t: t.timestamp)
        self._index = 0
        logger.info(f"BacktestFeed: {len(self._ticks)} ticks ready for replay")

    async def connect(self):
        self._index = 0

    async def receive(self) -> Optional[MarketTick]:
        if self._index >= len(self._ticks):
            return None
        tick = self._ticks[self._index]
        self._index += 1
        return tick

    async def disconnect(self):
        pass

    @property
    def total_ticks(self) -> int:
        return len(self._ticks)

    @property
    def progress(self) -> float:
        if len(self._ticks) == 0:
            return 1.0
        return self._index / len(self._ticks)


# ═══════════════════════════════════════════════════════════
#  BACKTEST RUNNER
# ═══════════════════════════════════════════════════════════

class BacktestRunner:
    """Orchestrates the full backtest pipeline."""

    def __init__(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        interval: str = "1h",
        window_size: int = 50,
        correlation_threshold: float = 0.5,
        output_dir: str = "./backtest_results",
    ):
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.interval = interval
        self.window_size = window_size
        self.correlation_threshold = correlation_threshold
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Parse dates
        self.start_ts = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
        self.end_ts = datetime.strptime(end_date, "%Y-%m-%d").timestamp()

        # Results storage
        self.snapshots: List[Dict] = []
        self.alerts: List[Dict] = []
        self.regime_history: List[Dict] = []
        self.barcodes: List[Dict] = []
        self.persistence_diagrams: List[Dict] = []
        self.persistence_engine = PersistenceEngine()

    async def run(self) -> Dict[str, Any]:
        """Execute the full backtest."""
        if not HAS_TOPOLOGY:
            logger.error(
                f"Cannot run backtest: topology components not available.\n"
                f"Import error: {IMPORT_ERROR_MSG}\n"
                f"Make sure real_time_topology_monitor.py is in the current directory "
                f"and all its dependencies (SANN, torch, etc.) are installed."
            )
            return {"error": IMPORT_ERROR_MSG}

        logger.info("=" * 60)
        logger.info("TOPOLOGICAL BACKTEST ENGINE")
        logger.info("=" * 60)
        logger.info(f"Symbols: {self.symbols}")
        logger.info(f"Period: {self.start_date} → {self.end_date}")
        logger.info(f"Interval: {self.interval}")
        logger.info(f"Window: {self.window_size} | Threshold: {self.correlation_threshold}")
        logger.info("=" * 60)

        # ── Step 1: Fetch historical data ──
        logger.info("\n📡 Step 1: Fetching historical data...")
        fetcher = MultiSourceFetcher()
        all_bars = await fetcher.fetch_all(
            self.symbols, self.start_ts, self.end_ts, self.interval
        )

        total_bars = sum(len(v) for v in all_bars.values())
        if total_bars == 0:
            logger.error("No data fetched from any source!")
            return {"error": "no_data"}

        logger.info(f"\n✅ Total bars fetched: {total_bars}")
        for sym, bars in all_bars.items():
            logger.info(f"  {sym}: {len(bars)} bars")

        # ── Step 2: Create feed and engine ──
                # ═══════════════════════════════════════════════════════════
        #  Step 2: Initialize Topology Engine
         # ═══════════════════════════════════════════════════════════
        logger.info("\n⚙️  Step 2: Initializing topology engine...")

        # --- فیلتر نمادهای بدون داده ---
        active_symbols = [
            s
            for s in self.symbols
            if len(all_bars.get(s, [])) > 0
        ]

        if len(active_symbols) < 2:
            logger.error("Need at least 2 symbols with data for correlation!")
            return {"error": "insufficient_symbols"}

        logger.info(f"  Active symbols: {len(active_symbols)}/{len(self.symbols)} → {active_symbols}")

        # --- فقط بارهای نمادهای فعال رو بفرست به feed ---
        filtered_bars = {s: bars for s, bars in all_bars.items() if len(bars) > 0}
        feed = HistoricalBacktestFeed(filtered_bars)

        config = MonitorConfig(
            symbols=active_symbols,
            window_size=self.window_size,
            min_ticks=5,
            correlation_threshold=self.correlation_threshold,
            adaptive_threshold=True,
            threshold_percentile=75.0,
            max_simplex_dim=3,
            change_sensitivity=2.0,
            history_length=50,
            analysis_interval=0.0,
            simulation_mode=True,
            simulation_speed=100.0,
            output_dir=str(self.output_dir / "topology_plots"),
            enable_persistence=True,
        )

        engine = TopologyEngine(config)
        feed = HistoricalBacktestFeed(all_bars)
        
    # ── Step 3: Replay ticks ──
        logger.info(f"\n🔄 Step 3: Replaying {feed.total_ticks} ticks...")
        await feed.connect()

        processed = 0
        warmup_count = 0
        last_log = 0
        start_time = time.time()
        elapsed = 0.0
        while True:
            tick = await feed.receive()
            if tick is None:
                break

            processed += 1

            # ✅ process_tick is now SYNC (not async)
            result = engine.process_tick(tick)

            if result is None:
                # Still warming up — correlation engine doesn't have enough data yet
                warmup_count += 1
                if warmup_count % 50 == 0:
                    logger.info(f"  Warming up... {warmup_count} ticks processed")
                continue

            # Unpack only when we have a real result
            snapshot, alert = result

            snap_dict = {
                "timestamp": snapshot.timestamp,
                "datetime": datetime.fromtimestamp(snapshot.timestamp).isoformat(),
                "betti_0": snapshot.betti_numbers.get(0, 0),
                "betti_1": snapshot.betti_numbers.get(1, 0),
                "betti_2": snapshot.betti_numbers.get(2, 0),
                "euler": snapshot.euler_characteristic,
                "num_simplices": snapshot.num_simplices,
                "max_dimension": snapshot.max_dimension,
                "threshold": snapshot.correlation_threshold,
                "regime": snapshot.regime.value if hasattr(snapshot.regime, 'value') else str(snapshot.regime),
            }
            self.snapshots.append(snap_dict)

            self.regime_history.append({
                "timestamp": snapshot.timestamp,
                "datetime": datetime.fromtimestamp(snapshot.timestamp).isoformat(),
                "regime": snap_dict["regime"],
            })

            if getattr(snapshot, "complex", None) is not None:
                try:
                    diagram = self.persistence_engine.compute_diagram(snapshot.complex)
                    barcode_map = self.persistence_engine.compute_barcodes(snapshot.complex)

                    diagram_lookup: Dict[Tuple[int, float, Optional[float]], Any] = {}
                    for interval in diagram:
                        key = (interval.dimension, interval.birth, interval.death)
                        diagram_lookup[key] = interval
                        self.persistence_diagrams.append({
                            "timestamp": snapshot.timestamp,
                            "datetime": datetime.fromtimestamp(snapshot.timestamp).isoformat(),
                            "dimension": interval.dimension,
                            "birth": interval.birth,
                            "death": interval.death,
                            "lifetime": interval.lifetime,
                        })

                    for dim, intervals in barcode_map.items():
                        for birth, death in intervals:
                            key = (dim, birth, death)
                            matched = diagram_lookup.get(key)
                            generator = None
                            persistence = None
                            if matched is not None:
                                persistence = matched.persistence
                                generator = matched.birth_simplex
                            self.barcodes.append({
                                "timestamp": snapshot.timestamp,
                                "datetime": datetime.fromtimestamp(snapshot.timestamp).isoformat(),
                                "dimension": dim,
                                "birth": birth,
                                "death": death,
                                "persistence": persistence,
                                "generator": str(generator) if generator is not None else "",
                            })
                except Exception as exc:
                    logger.debug(f"Persistence capture skipped at {snapshot.timestamp}: {exc}")

            if alert is not None:
                alert_dict = {
                    "timestamp": tick.timestamp,
                    "datetime": datetime.fromtimestamp(tick.timestamp).isoformat(),
                    "severity": alert.severity.value if hasattr(alert, 'severity') else str(alert),
                    "message": str(alert.message) if hasattr(alert, 'message') else str(alert),
                }
                self.alerts.append(alert_dict)

            # Progress logging every 10%
            pct = int(feed.progress * 100)
            if pct >= last_log + 10:
                elapsed = time.time() - start_time
                logger.info(
                    f"  Progress: {pct}% ({processed}/{feed.total_ticks}) "
                    f"| Snapshots: {len(self.snapshots)} | Alerts: {len(self.alerts)} "
                    f"| Warmup: {warmup_count} | Time: {elapsed:.1f}s"
                )
                last_log = pct

        await feed.disconnect()
        elapsed = time.time() - start_time  # ← اضافه کن اینجا (بعد خط 680)



        # ── Step 4: Save results ──
        logger.info(f"\n💾 Step 4: Saving results...")
        self._save_csv("snapshots.csv", self.snapshots)
        self._save_csv("regime_history.csv", self.regime_history)
        self._save_csv("alerts.csv", self.alerts)
        self._save_csv("barcodes.csv", self.barcodes)
        self._save_csv("persistence_diagram.csv", self.persistence_diagrams)
        self._save_summary(elapsed, total_bars, fetcher.source_status)

        # ── Summary ──
        logger.info("\n" + "=" * 60)
        logger.info("BACKTEST COMPLETE")
        logger.info("=" * 60)
        logger.info(f"  Duration: {elapsed:.1f}s")
        logger.info(f"  Ticks processed: {processed}")
        logger.info(f"  Snapshots: {len(self.snapshots)}")
        logger.info(f"  Alerts: {len(self.alerts)}")
        logger.info(f"  Regimes detected: {len(set(r['regime'] for r in self.regime_history))}")
        logger.info(f"  Output: {self.output_dir.absolute()}")
        logger.info("=" * 60)

        return {
            "ticks_processed": processed,
            "snapshots": len(self.snapshots),
            "alerts": len(self.alerts),
            "elapsed_seconds": elapsed,
            "output_dir": str(self.output_dir.absolute()),
        }

    def _save_csv(self, filename: str, data: List[Dict]):
        """Save a list of dicts to CSV."""
        if not data:
            logger.info(f"  {filename}: empty, skipped")
            return

        filepath = self.output_dir / filename
        keys = data[0].keys()
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"  {filename}: {len(data)} rows saved")

    def _save_summary(self, elapsed: float, total_bars: int, source_status: Dict):
        """Save a human-readable summary text file."""
        filepath = self.output_dir / "summary.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("TOPOLOGICAL BACKTEST SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Date generated: {datetime.now().isoformat()}\n")
            f.write(f"Period: {self.start_date} → {self.end_date}\n")
            f.write(f"Interval: {self.interval}\n")
            f.write(f"Symbols: {', '.join(self.symbols)}\n")
            f.write(f"Window size: {self.window_size}\n")
            f.write(f"Correlation threshold: {self.correlation_threshold}\n\n")

            f.write("DATA SOURCES\n")
            f.write("-" * 30 + "\n")
            for src, status in source_status.items():
                f.write(f"  {src}: {status.value}\n")
            f.write(f"\nTotal bars fetched: {total_bars}\n\n")

            f.write("RESULTS\n")
            f.write("-" * 30 + "\n")
            f.write(f"  Ticks processed: {sum(len(v) for v in [self.snapshots])}\n")
            f.write(f"  Snapshots: {len(self.snapshots)}\n")
            f.write(f"  Alerts: {len(self.alerts)}\n")
            f.write(f"  Elapsed: {elapsed:.1f}s\n\n")

            # Regime distribution
            if self.regime_history:
                f.write("REGIME DISTRIBUTION\n")
                f.write("-" * 30 + "\n")
                regime_counts: Dict[str, int] = {}
                for r in self.regime_history:
                    reg = r["regime"]
                    regime_counts[reg] = regime_counts.get(reg, 0) + 1
                total = len(self.regime_history)
                for reg, count in sorted(regime_counts.items(), key=lambda x: -x[1]):
                    pct = count / total * 100
                    f.write(f"  {reg}: {count} ({pct:.1f}%)\n")
                f.write("\n")

            # Betti number statistics
            if self.snapshots:
                f.write("BETTI NUMBER STATISTICS\n")
                f.write("-" * 30 + "\n")
                for key in ["betti_0", "betti_1", "betti_2", "euler"]:
                    vals = [s[key] for s in self.snapshots if key in s]
                    if vals:
                        f.write(
                            f"  {key}: min={min(vals)}, max={max(vals)}, "
                            f"mean={np.mean(vals):.2f}, std={np.std(vals):.2f}\n"
                        )
                f.write("\n")

            # Alert summary
            if self.alerts:
                f.write("ALERTS\n")
                f.write("-" * 30 + "\n")
                severity_counts: Dict[str, int] = {}
                for a in self.alerts:
                    sev = a.get("severity", "unknown")
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
                for sev, count in sorted(severity_counts.items(), key=lambda x: -x[1]):
                    f.write(f"  {sev}: {count}\n")

        logger.info(f"  summary.txt saved")


# ═══════════════════════════════════════════════════════════
#  QUICK ANALYSIS HELPERS
# ═══════════════════════════════════════════════════════════

def print_regime_timeline(regime_history: List[Dict]):
    """Print a visual timeline of regime changes."""
    if not regime_history:
        print("No regime data.")
        return

    REGIME_ICONS = {
        "normal": "🟢",
        "stressed": "🟡",
        "critical": "🔴",
        "transitional": "🟠",
        "decoupled": "⚪",
    }

    print("\n📊 REGIME TIMELINE")
    print("=" * 60)

    prev_regime = None
    for entry in regime_history:
        regime = entry["regime"]
        if regime != prev_regime:
            icon = REGIME_ICONS.get(regime, "⚫")
            dt = entry["datetime"]
            print(f"  {dt}  {icon} {regime.upper()}")
            prev_regime = regime

    print("=" * 60)


def analyze_results(output_dir: str = "./backtest_results"):
    """Load and analyze saved backtest results."""
    output_path = Path(output_dir)

    # Load snapshots
    snapshots_file = output_path / "snapshots.csv"
    if not snapshots_file.exists():
        print(f"No results found in {output_dir}")
        return

    snapshots = []
    with open(snapshots_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            snapshots.append(row)

    print(f"\n📈 BACKTEST ANALYSIS ({len(snapshots)} snapshots)")
    print("=" * 60)

    # Betti stats
    for key in ["betti_0", "betti_1", "betti_2", "euler"]:
        vals = [float(s[key]) for s in snapshots if key in s]
        if vals:
            print(f"  {key}: min={min(vals):.0f}, max={max(vals):.0f}, "
                  f"mean={np.mean(vals):.2f}, std={np.std(vals):.2f}")

    # Regime distribution
    regimes = [s.get("regime", "unknown") for s in snapshots]
    unique = set(regimes)
    print(f"\n  Regimes: {len(unique)} types")
    for r in sorted(unique):
        count = regimes.count(r)
        pct = count / len(regimes) * 100
        print(f"    {r}: {count} ({pct:.1f}%)")

    # Load alerts
    alerts_file = output_path / "alerts.csv"
    if alerts_file.exists():
        alerts = []
        with open(alerts_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                alerts.append(row)
        print(f"\n  Alerts: {len(alerts)}")
        for a in alerts[:10]:
            print(f"    [{a.get('severity', '?')}] {a.get('datetime', '?')}: {a.get('message', '?')}")
        if len(alerts) > 10:
            print(f"    ... and {len(alerts) - 10} more")

    # Load regime history for timeline
    regime_file = output_path / "regime_history.csv"
    if regime_file.exists():
        regime_history = []
        with open(regime_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                regime_history.append(row)
        print_regime_timeline(regime_history)


# ═══════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════

DEFAULT_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT",
    "XRP/USDT", "DOT/USDT", "AVAX/USDT", "LINK/USDT", "DOGE/USDT",
]


def main():
    parser = argparse.ArgumentParser(
        description="Topological Market Backtest Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 7-day backtest with default symbols
  python backtest_engine.py --days 7

  # 30-day backtest with custom symbols
  python backtest_engine.py --start 2026-03-01 --end 2026-03-31 --symbols BTC/USDT ETH/USDT SOL/USDT

  # Analyze previous results
  python backtest_engine.py --analyze

  # Force specific source
  python backtest_engine.py --days 7 --source coingecko
        """,
    )

    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=7, help="Lookback days from today (default: 7)")
    parser.add_argument(
        "--symbols", nargs="+", default=DEFAULT_SYMBOLS,
        help="Symbols to backtest (default: top 10)",
    )
    parser.add_argument("--interval", type=str, default="1h", help="Bar interval (default: 1h)")
    parser.add_argument("--window", type=int, default=50, help="Correlation window size (default: 50)")
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Correlation threshold for VR complex (default: 0.5)",
    )
    parser.add_argument("--output", type=str, default="./backtest_results", help="Output directory")
    parser.add_argument(
        "--source", type=str, default=None,
        choices=["binance", "coingecko", "cryptocompare", "csv"],
        help="Force a specific data source (skip fallback chain)",
    )
    parser.add_argument("--analyze", action="store_true", help="Analyze previous results")

    args = parser.parse_args()

    # ── Analyze mode ──
    if args.analyze:
        analyze_results(args.output)
        return

    # ── Determine date range ──
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=args.days)
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")

    # ── Build runner ──
    runner = BacktestRunner(
        symbols=args.symbols,
        start_date=start_date,
        end_date=end_date,
        interval=args.interval,
        window_size=args.window,
        correlation_threshold=args.threshold,
        output_dir=args.output,
    )

    # ── Override source if specified ──
    if args.source:
        source_map = {
            "binance": BinanceHistoricalSource,
            "coingecko": CoinGeckoHistoricalSource,
            "cryptocompare": CryptoCompareHistoricalSource,
            "csv": LocalCSVHistoricalSource,
        }
        cls = source_map[args.source]
        # Monkey-patch the fetcher in run() — cleaner approach:
        original_run = runner.run

        async def patched_run():
            runner._forced_source = cls
            return await original_run()

        # Override MultiSourceFetcher creation inside run
        original_init = MultiSourceFetcher.__init__

        def patched_init(self_fetcher, sources=None):
            forced = [cls()]
            original_init(self_fetcher, sources=forced)

        MultiSourceFetcher.__init__ = patched_init
        try:
            result = asyncio.run(runner.run())
        finally:
            MultiSourceFetcher.__init__ = original_init
    else:
        result = asyncio.run(runner.run())

    # ── Print quick analysis ──
    if result and "error" not in result:
        print("\n✅ Backtest finished successfully!")
        print(f"   Results saved to: {result['output_dir']}")
        analyze_results(args.output)
    else:
        print("\n❌ Backtest failed.")
        if result:
            print(f"   Error: {result.get('error', 'unknown')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
