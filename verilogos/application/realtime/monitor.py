"""Real-time monitor runtime for VeriLogos Layer 4."""

import asyncio
import json
import logging
import signal
import time
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime
from itertools import combinations
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple

import numpy as np
try:
    import torch
except ImportError:
    torch = None

from verilogos.application.models import (
    AlertSeverity,
    MarketRegime,
    MarketTick,
    MonitorConfig,
    StructuralAlert,
    TopologicalSnapshot,
)
from verilogos.application.engines import (
    CorrelationEngine,
    StructuralChangeDetector,
    TopologyAnalyzer,
    VietorisRipsBuilder,
)
from verilogos.core.topology.complexes.complex import SimplicialComplex

"""
SANN Real-Time Market Topology Monitor
=======================================
Monitors live market data via WebSocket, builds simplicial complexes
from price correlations, and detects structural changes (regime shifts)
by tracking Betti numbers and Euler characteristic in real-time.

Architecture:
  WebSocket Feed → Rolling Window → Correlation Matrix → Vietoris-Rips Complex
  → Betti Numbers → Structural Change Detection → Alert System

Dependencies:
    pip install websockets aiohttp numpy torch matplotlib rich

Usage:
    python real_time_topology_monitor.py
"""

import asyncio
import json
import time
import logging
import signal
import sys
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Dict, List, Optional, Tuple, Callable, Any, Set, Deque
)
from itertools import combinations
from abc import ABC, abstractmethod

import numpy as np
try:
    import torch
except ImportError:
    torch = None

# ── Optional: Rich for beautiful terminal output ────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

# ── Optional: matplotlib for live plotting ──────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ── Optional: websockets ────────────────────────────────────
try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

logger = logging.getLogger("TopologyMonitor")


# ═══════════════════════════════════════════════════════════════
#  SECTION 1: Data Models & Enums
# ═══════════════════════════════════════════════════════════════





@dataclass


@dataclass


@dataclass


@dataclass


# ═══════════════════════════════════════════════════════════════
#  SECTION 2: Vietoris-Rips Complex Builder
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
#  SECTION 3: Structural Change Detector
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
#  SECTION 4: Data Feed Providers (WebSocket + Simulation)
# ═══════════════════════════════════════════════════════════════

class DataFeedProvider(ABC):
    """Abstract base class for market data providers."""

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def receive(self) -> Optional[MarketTick]:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...


class BinanceWebSocketFeed(DataFeedProvider):
    """Real Binance WebSocket data feed."""

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.ws = None
        self._connected = False

    async def connect(self) -> None:
        if not HAS_WEBSOCKETS:
            raise ImportError(
                "websockets package required. Install: pip install websockets"
            )

        streams = "/".join(
            f"{s.lower()}@trade" for s in self.config.symbols
        )
        url = f"{self.config.ws_url}/{streams}"
        logger.info(f"Connecting to Binance WS: {url}")

        # ──────────────────────────────────────────────────
        # NUCLEAR OPTION: Kill ALL proxy sources
        # ──────────────────────────────────────────────────
        import os, urllib.request

        # 1) Clear env vars
        for k in list(os.environ.keys()):
            if "proxy" in k.lower():
                del os.environ[k]

        # 2) Monkey-patch urllib so websockets can't read Windows registry proxy
        urllib.request.getproxies = lambda: {}

        # ──────────────────────────────────────────────────
        # Strategy A: Direct connection (no proxy at all)
        # ──────────────────────────────────────────────────
        try:
            self.ws = await websockets.connect(
                url,
                ping_interval=20,
                open_timeout=15,
            )
            self._connected = True
            logger.info("✅ Connected DIRECTLY to Binance WebSocket")
            return
        except Exception as e:
            logger.warning(f"Direct connection failed: {e}")

        # ──────────────────────────────────────────────────
        # Strategy B: Manual SOCKS5 tunnel via python-socks
        # ──────────────────────────────────────────────────
        try:
            from python_socks.async_.asyncio import Proxy

            proxy = Proxy.from_url("socks5://127.0.0.1:1080")
            sock = await proxy.connect(
                dest_host="stream.binance.com",
                dest_port=9443,
            )
            self.ws = await websockets.connect(
                url,
                sock=sock,
                server_hostname="stream.binance.com",
                ping_interval=20,
                open_timeout=15,
            )
            self._connected = True
            logger.info("✅ Connected via SOCKS5 proxy")
            return
        except Exception as e:
            logger.warning(f"SOCKS5 proxy also failed: {e}")

        # ──────────────────────────────────────────────────
        # Strategy C: Raw asyncio SSL socket (last resort)
        # ──────────────────────────────────────────────────
        import ssl
        import socket

        logger.info("Trying raw socket bypass...")
        ssl_ctx = ssl.create_default_context()

        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(10)
        raw_sock.connect(("stream.binance.com", 9443))
        raw_sock.setblocking(False)

        self.ws = await websockets.connect(
            url,
            sock=raw_sock,
            server_hostname="stream.binance.com",
            ssl=ssl_ctx,
            ping_interval=20,
            open_timeout=15,
        )
        self._connected = True
        logger.info("✅ Connected via raw socket bypass")


    async def receive(self) -> Optional[MarketTick]:
        if not self._connected or self.ws is None:
            return None

        try:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=10.0)
            data = json.loads(raw)
            return MarketTick.from_binance_ws(data)
        except asyncio.TimeoutError:
            logger.warning("WebSocket receive timeout")
            return None
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            return None

    async def disconnect(self) -> None:
        if self.ws:
            await self.ws.close()
        self._connected = False


class SimulatedMarketFeed(DataFeedProvider):
    """
    Simulated market feed for testing without real WebSocket.
    Generates synthetic price data with regime changes.
    """

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(seed=42)
        self._prices: Dict[str, float] = {}
        self._tick_count = 0
        self._regime_change_at = [200, 500, 800, 1200]
        self._current_volatility = 0.001

        # Initialize base prices
        base_prices = {
            "BTCUSDT": 67000.0, "ETHUSDT": 3400.0, "BNBUSDT": 580.0,
            "SOLUSDT": 145.0, "ADAUSDT": 0.45, "XRPUSDT": 0.52,
            "DOTUSDT": 7.2, "AVAXUSDT": 35.0, "MATICUSDT": 0.70,
            "LINKUSDT": 14.5,
        }
        for symbol in config.symbols:
            self._prices[symbol] = base_prices.get(symbol, 100.0)

        # Correlation structure between assets
        n = len(config.symbols)
        self._corr_matrix = self._generate_correlation_structure(n)

    def _generate_correlation_structure(self, n: int) -> np.ndarray:
        """Generate a realistic correlation structure."""
        # Start with moderate positive correlations (crypto-typical)
        base = np.full((n, n), 0.3)
        np.fill_diagonal(base, 1.0)
        # BTC-ETH highly correlated
        base[0, 1] = base[1, 0] = 0.85
        # Group correlations
        for i in range(2, min(5, n)):
            base[0, i] = base[i, 0] = 0.6
            base[1, i] = base[i, 1] = 0.55
        return base

    async def connect(self) -> None:
        logger.info("Simulated market feed started")

    async def receive(self) -> Optional[MarketTick]:
        await asyncio.sleep(0.05 / self.config.simulation_speed)
        self._tick_count += 1

        # Regime changes: increase volatility and break correlations
        if self._tick_count in self._regime_change_at:
            self._current_volatility = self.rng.uniform(0.005, 0.02)
            logger.info(
                f"[SIM] Regime change at tick {self._tick_count}, "
                f"volatility → {self._current_volatility:.4f}"
            )
            # Randomly perturb correlation structure
            n = len(self.config.symbols)
            perturbation = self.rng.normal(0, 0.3, (n, n))
            perturbation = (perturbation + perturbation.T) / 2
            np.fill_diagonal(perturbation, 0)
            self._corr_matrix = np.clip(
                self._corr_matrix + perturbation, -1.0, 1.0
            )
            np.fill_diagonal(self._corr_matrix, 1.0)
        elif self._tick_count % 100 == 0:
            # Gradually return to normal
            self._current_volatility *= 0.95
            self._current_volatility = max(self._current_volatility, 0.001)

        # Generate correlated returns
        n = len(self.config.symbols)
        try:
            L = np.linalg.cholesky(
                np.clip(self._corr_matrix, -0.99, 0.99)
                * (1 - 1e-6 * np.eye(n))
                + 1e-6 * np.eye(n)
            )
        except np.linalg.LinAlgError:
            L = np.eye(n)

        independent_returns = self.rng.normal(0, self._current_volatility, n)
        correlated_returns = L @ independent_returns

        # Pick a random symbol for this tick
        idx = self._tick_count % n
        symbol = self.config.symbols[idx]

        self._prices[symbol] *= (1.0 + correlated_returns[idx])

        return MarketTick(
            symbol=symbol,
            price=self._prices[symbol],
            volume=self.rng.uniform(0.1, 10.0),
            timestamp=time.time(),
        )

    async def disconnect(self) -> None:
        logger.info("Simulated market feed stopped")


# ═══════════════════════════════════════════════════════════════
#  SECTION 5: Correlation Engine
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
#  SECTION 6: Topology Analyzer (Core Engine)
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
#  SECTION 7: Visualization Engine
# ═══════════════════════════════════════════════════════════════
class TopologyVisualizer:
    """Generates real-time plots of topological features."""

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.output_dir = config.output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.history: List[TopologicalSnapshot] = []
        self._plot_counter = 0
        self._plot_interval = 5  # Update plot every N snapshots

    def update(self, snapshot: TopologicalSnapshot) -> None:
        """Add new snapshot and regenerate plots periodically."""
        self.history.append(snapshot)

        # Keep a bounded history to avoid memory bloat
        if len(self.history) > 500:
            self.history = self.history[-500:]

        self._plot_counter += 1

        if HAS_MATPLOTLIB and self._plot_counter % self._plot_interval == 0:
            self._plot_betti_timeseries()
            self._plot_euler_timeseries()
            self._plot_regime_timeline()
            self._plot_persistence_diagram()
            self._plot_persistence_barcode()

    # ── Betti Numbers Time Series ───────────────────────────
    def _plot_betti_timeseries(self) -> None:
        """Plot β₀, β₁, β₂ over time."""
        if len(self.history) < 2:
            return

        timestamps = [
            datetime.fromtimestamp(s.timestamp) for s in self.history
        ]
        betti0 = [s.betti_numbers.get(0, 0) for s in self.history]
        betti1 = [s.betti_numbers.get(1, 0) for s in self.history]
        betti2 = [s.betti_numbers.get(2, 0) for s in self.history]

        fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

        axes[0].plot(timestamps, betti0, color="#2196F3", linewidth=1.5)
        axes[0].fill_between(timestamps, betti0, alpha=0.2, color="#2196F3")
        axes[0].set_ylabel("β₀ (components)")
        axes[0].set_title("Topological Features — Real-Time Monitor")
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(timestamps, betti1, color="#FF5722", linewidth=1.5)
        axes[1].fill_between(timestamps, betti1, alpha=0.2, color="#FF5722")
        axes[1].set_ylabel("β₁ (loops)")
        axes[1].grid(True, alpha=0.3)

        axes[2].plot(timestamps, betti2, color="#4CAF50", linewidth=1.5)
        axes[2].fill_between(timestamps, betti2, alpha=0.2, color="#4CAF50")
        axes[2].set_ylabel("β₂ (voids)")
        axes[2].set_xlabel("Time")
        axes[2].grid(True, alpha=0.3)

        fig.autofmt_xdate()
        plt.tight_layout()

        path = os.path.join(self.output_dir, "betti_timeseries.png")
        plt.savefig(path, dpi=120)
        plt.close(fig)
        logger.debug(f"Saved Betti plot to {path}")

    # ── Euler Characteristic Time Series ────────────────────
    def _plot_euler_timeseries(self) -> None:
        """Plot Euler characteristic χ over time."""
        if len(self.history) < 2:
            return

        timestamps = [
            datetime.fromtimestamp(s.timestamp) for s in self.history
        ]
        euler = [s.euler_characteristic for s in self.history]

        fig, ax = plt.subplots(figsize=(12, 4))

        ax.plot(timestamps, euler, color="#9C27B0", linewidth=1.5)
        ax.fill_between(timestamps, euler, alpha=0.15, color="#9C27B0")
        ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
        ax.set_ylabel("χ (Euler characteristic)")
        ax.set_xlabel("Time")
        ax.set_title("Euler Characteristic — Structural Complexity")
        ax.grid(True, alpha=0.3)

        fig.autofmt_xdate()
        plt.tight_layout()

        path = os.path.join(self.output_dir, "euler_timeseries.png")
        plt.savefig(path, dpi=120)
        plt.close(fig)
        logger.debug(f"Saved Euler plot to {path}")

    # ── Regime Timeline ─────────────────────────────────────
    def _plot_regime_timeline(self) -> None:
        """Plot detected market regimes as colored bands."""
        if len(self.history) < 2:
            return

        regime_colors = {
            MarketRegime.STABLE: "#4CAF50",
            MarketRegime.TRANSITIONING: "#FFC107",
            MarketRegime.VOLATILE: "#FF9800",
            MarketRegime.CRISIS: "#F44336",
            MarketRegime.UNKNOWN: "#9E9E9E",
        }

        timestamps = [
            datetime.fromtimestamp(s.timestamp) for s in self.history
        ]

        fig, ax = plt.subplots(figsize=(12, 2))

        for i in range(len(self.history) - 1):
            color = regime_colors.get(
                self.history[i].regime, "#9E9E9E"
            )
            ax.axvspan(
                timestamps[i],
                timestamps[i + 1],
                facecolor=color,
                alpha=0.6,
            )

        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=c, label=r.value)
            for r, c in regime_colors.items()
        ]
        ax.legend(
            handles=legend_elements,
            loc="upper right",
            fontsize=8,
            ncol=5,
        )

        ax.set_yticks([])
        ax.set_xlabel("Time")
        ax.set_title("Detected Market Regime")

        fig.autofmt_xdate()
        plt.tight_layout()

        path = os.path.join(self.output_dir, "regime_timeline.png")
        plt.savefig(path, dpi=120)
        plt.close(fig)
        logger.debug(f"Saved regime plot to {path}")

    # ── Persistence Diagram ─────────────────────────────────
    def _plot_persistence_diagram(self) -> None:
        """Plot persistence diagram (birth vs death) from latest snapshot."""
        if not self.history:
            return
        snap = self.history[-1]
        if not snap.persistence_diagrams:
            return

        colors = {0: "#2196F3", 1: "#FF5722", 2: "#4CAF50"}
        fig, ax = plt.subplots(figsize=(8, 8))
        max_val = 0

        for dim, pairs in snap.persistence_diagrams.items():
            if not pairs:
                continue
            births = [b for b, d in pairs if d != float('inf')]
            deaths = [d for b, d in pairs if d != float('inf')]
            if births:
                ax.scatter(births, deaths, c=colors.get(dim, "#999"),
                           label=f"H{dim}", alpha=0.7, s=40)
                max_val = max(max_val, max(deaths) if deaths else 0)

        if max_val > 0:
            ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.3, label="diagonal")

        ax.set_xlabel("Birth")
        ax.set_ylabel("Death")
        ax.set_title("Persistence Diagram")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        path = os.path.join(self.output_dir, "persistence_diagram.png")
        plt.savefig(path, dpi=120)
        plt.close(fig)
        logger.debug(f"Saved persistence diagram to {path}")

    # ── Persistence Barcode ─────────────────────────────────
    def _plot_persistence_barcode(self) -> None:
        """Plot persistence barcode from latest snapshot."""
        if not self.history:
            return
        snap = self.history[-1]
        if not snap.persistence_diagrams:
            return

        colors = {0: "#2196F3", 1: "#FF5722", 2: "#4CAF50"}
        fig, ax = plt.subplots(figsize=(12, 6))
        y_pos = 0
        yticks = []
        ytick_labels = []

        for dim in sorted(snap.persistence_diagrams.keys()):
            pairs = snap.persistence_diagrams[dim]
            finite_pairs = [(b, d) for b, d in pairs if d != float('inf')]
            for b, d in sorted(finite_pairs, key=lambda x: x[1] - x[0], reverse=True):
                ax.barh(y_pos, d - b, left=b, height=0.6,
                        color=colors.get(dim, "#999"), alpha=0.7)
                yticks.append(y_pos)
                ytick_labels.append(f"H{dim}")
                y_pos += 1

        ax.set_yticks(yticks[:20])
        ax.set_yticklabels(ytick_labels[:20])
        ax.set_xlabel("Filtration Parameter")
        ax.set_title("Persistence Barcode")
        ax.grid(True, alpha=0.3, axis='x')
        plt.tight_layout()

        path = os.path.join(self.output_dir, "persistence_barcode.png")
        plt.savefig(path, dpi=120)
        plt.close(fig)
        logger.debug(f"Saved persistence barcode to {path}")

# ═══════════════════════════════════════════════════════════════
#  SECTION 8: Terminal Dashboard
# ═══════════════════════════════════════════════════════════════

class ConsoleDashboard:

    def __init__(self) -> None:
        self.last_snapshot: Optional[TopologicalSnapshot] = None
        self.last_alert: Optional[StructuralAlert] = None

    def update(
        self,
        snapshot: TopologicalSnapshot,
        alert: Optional[StructuralAlert],
    ) -> None:

        self.last_snapshot = snapshot
        if alert:
            self.last_alert = alert

        if not HAS_RICH:
            print(
                f"{datetime.fromtimestamp(snapshot.timestamp)} "
                f"Betti={snapshot.betti_numbers} "
                f"χ={snapshot.euler_characteristic} "
                f"Regime={snapshot.regime.value}"
            )
            if alert:
                print("ALERT:", alert.message)
            return

        table = Table(title="Market Topology Monitor")

        table.add_column("Metric")
        table.add_column("Value")

        table.add_row("Betti 0", str(snapshot.betti_numbers.get(0, 0)))
        table.add_row("Betti 1", str(snapshot.betti_numbers.get(1, 0)))
        table.add_row("Betti 2", str(snapshot.betti_numbers.get(2, 0)))

        table.add_row("Euler χ", str(snapshot.euler_characteristic))
        table.add_row("Regime", snapshot.regime.value)

        console.clear()
        console.print(table)

        if self.last_alert:
            console.print(
                Panel(
                    self.last_alert.message,
                    title=f"ALERT ({self.last_alert.severity.value})",
                )
            )


# ═══════════════════════════════════════════════════════════════
#  SECTION 9: Main Monitor Orchestrator
# ═══════════════════════════════════════════════════════════════

class RealTimeTopologyMonitor:

    def __init__(self, config: MonitorConfig) -> None:

        self.config = config

        if config.simulation_mode:
            self.feed = SimulatedMarketFeed(config)
        else:
            self.feed = BinanceWebSocketFeed(config)

        self.corr_engine = CorrelationEngine(config)
        self.analyzer = TopologyAnalyzer(config)
        self.detector = StructuralChangeDetector(config)
        self.visualizer = TopologyVisualizer(config)
        self.dashboard = ConsoleDashboard()

        self.running = True

    async def run(self) -> None:

        await self.feed.connect()

        last_analysis = time.time()

        while self.running:

            tick = await self.feed.receive()

            if tick is None:
                continue

            self.corr_engine.update(tick)

            now = time.time()

            if (
                now - last_analysis >= self.config.analysis_interval
                and self.corr_engine.is_ready()
            ):

                corr = self.corr_engine.compute_correlation_matrix()

                threshold = self.corr_engine.get_adaptive_threshold(corr)

                snapshot = self.analyzer.analyze(
                    corr,
                    threshold,
                    now,
                )

                alert = self.detector.update(snapshot)

                self.visualizer.update(snapshot)

                self.dashboard.update(snapshot, alert)

                last_analysis = now

        await self.feed.disconnect()

    def stop(self) -> None:
        self.running = False


# ═══════════════════════════════════════════════════════════════
#  SECTION 10: Entry Point
# ═══════════════════════════════════════════════════════════════

async def main() -> None:
    """Entry point — parse args, build config, run monitor."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Real-Time Topology Monitor for Market Microstructure"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"],
        help="Trading pair symbols",
    )
    parser.add_argument(
        "--window", type=int, default=50, help="Rolling window size"
    )
    parser.add_argument(
        "--interval", type=float, default=2.0, help="Analysis interval (sec)"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.7, help="Initial correlation threshold"
    )
    parser.add_argument(
        "--simulate", action="store_true", help="Use simulated market data"
    )
    parser.add_argument(
        "--output", type=str, default="topology_output", help="Output directory"
    )

    args = parser.parse_args()

    config = MonitorConfig(
        symbols=args.symbols,
        window_size=args.window,
        analysis_interval=args.interval,
        correlation_threshold=args.threshold,
        simulation_mode=args.simulate,
        output_dir=args.output,
    )

    monitor = RealTimeTopologyMonitor(config)

    # ─── Windows-safe signal handling ───────────────────────
    import platform

    loop = asyncio.get_running_loop()

    if platform.system() != "Windows":
        # Unix: graceful shutdown via SIGINT/SIGTERM
        import signal as _signal
        for sig in (_signal.SIGINT, _signal.SIGTERM):
            loop.add_signal_handler(sig, monitor.stop)
    # On Windows: KeyboardInterrupt is caught below instead

    try:
        await monitor.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received — shutting down …")
        monitor.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[✓] Monitor stopped by user.")
