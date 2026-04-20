import time
from typing import List

import numpy as np
import pytest

from verilogos.application.engines import TopologyEngine
from verilogos.application.models import MarketTick, MonitorConfig


def create_synthetic_tick(symbol: str = "BTC", price: float = 100.0, t: float | None = None) -> MarketTick:
    return MarketTick(symbol=symbol, price=price, volume=1.0, timestamp=t if t is not None else time.time())


def generate_varied_ticks(symbols: List[str], n: int = 100, start_t: float | None = None) -> List[MarketTick]:
    np.random.seed(7)
    base = {s: 100.0 + i * 10.0 for i, s in enumerate(symbols)}
    ticks: List[MarketTick] = []
    t0 = start_t if start_t is not None else time.time()
    for i in range(n):
        ts = t0 + i
        shock = np.random.normal(0.0, 0.02, size=len(symbols))
        for idx, symbol in enumerate(symbols):
            base[symbol] *= max(0.5, 1.0 + shock[idx])
            ticks.append(MarketTick(symbol=symbol, price=float(base[symbol]), volume=1.0, timestamp=ts))
    return ticks


def generate_crisis_ticks(symbols: List[str], n: int = 180, start_t: float | None = None) -> List[MarketTick]:
    np.random.seed(11)
    base = {s: 100.0 + i * 20.0 for i, s in enumerate(symbols)}
    ticks: List[MarketTick] = []
    t0 = start_t if start_t is not None else time.time()
    half = n // 2
    for i in range(n):
        ts = t0 + i
        if i < half:
            noise = np.random.normal(0.0, 0.003)
            shocks = [noise for _ in symbols]
        else:
            shocks = np.random.normal(0.0, 0.06, size=len(symbols))
        for idx, symbol in enumerate(symbols):
            base[symbol] *= max(0.2, 1.0 + float(shocks[idx]))
            ticks.append(MarketTick(symbol=symbol, price=float(base[symbol]), volume=1.0, timestamp=ts))
    return ticks


class TestPersistenceIntegration:
    @pytest.fixture
    def engine(self):
        config = MonitorConfig(
            symbols=["BTC", "ETH", "SOL", "ADA", "AVAX"],
            enable_persistence=True,
            persistence_thresholds=[0.01, 0.05, 0.1],
            min_ticks=10,
            window_size=30,
            analysis_interval=0.0,
            change_sensitivity=1.0,
        )
        return TopologyEngine(config)

    def test_persistence_engine_initialized(self, engine):
        assert hasattr(engine, "persistence_engine")
        assert engine.persistence_engine is not None

    def test_process_tick_returns_persistence_data(self, engine):
        ticks = generate_varied_ticks(engine.config.symbols, n=40)
        result = None
        for tick in ticks:
            result = engine.process_tick(tick)
            if result is not None:
                break
        assert result is not None
        snapshot, _ = result
        assert hasattr(snapshot, "persistent_features")
        assert hasattr(snapshot, "persistence_score")

    def test_alert_fires_on_regime_change(self, engine):
        alerts = []
        for tick in generate_crisis_ticks(engine.config.symbols, n=220):
            result = engine.process_tick(tick)
            if result and result[1]:
                alerts.append(result[1])
        assert len(alerts) > 0, "Expected alerts on regime transition"

    def test_persistence_score_nonzero(self, engine):
        scores = []
        for tick in generate_varied_ticks(engine.config.symbols, n=120):
            result = engine.process_tick(tick)
            if result:
                snapshot, _ = result
                scores.append(getattr(snapshot, "persistence_score", 0.0))
        assert any(score > 0 for score in scores), "Expected non-zero persistence_score in snapshots"
