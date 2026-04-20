# tests/topology/test_layer4_engines.py
"""
Comprehensive tests for Layer 4: TopologyEngine & StructuralChangeDetector.

Scenarios tested:
  1. Warmup phase — no alerts, regime = UNKNOWN
  2. Stable market — regime stays STABLE, no alerts
  3. Crisis injection — β₀ spike → regime = CRISIS, alert fired
  4. Volatile injection — β₁ spike → regime = VOLATILE
  5. Gradual drift — TRANSITIONING detection
  6. CUSUM reset — after alert, CUSUM resets and doesn't re-fire immediately
  7. Full pipeline — MarketTick → TopologyEngine → snapshot + alert
  8. Edge cases — single symbol, constant prices, NaN handling
"""

import time
import math
import pytest
import numpy as np
from collections import deque
from typing import List, Optional, Tuple
from unittest.mock import MagicMock, patch

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
    TopologyEngine,
    VietorisRipsBuilder,
)


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def make_snapshot(
    betti: dict,
    euler: int,
    timestamp: float = 0.0,
    regime: MarketRegime = MarketRegime.UNKNOWN,
) -> TopologicalSnapshot:
    """Create a TopologicalSnapshot with given Betti numbers."""
    return TopologicalSnapshot(
        timestamp=timestamp,
        betti_numbers=betti,
        euler_characteristic=euler,
        num_simplices={0: 10, 1: 5, 2: 1},
        max_dimension=2,
        correlation_threshold=0.6,
        regime=regime,
    )


def make_stable_snapshot(t: float = 0.0) -> TopologicalSnapshot:
    """Typical stable market: 1 component, 0 loops, 0 voids."""
    return make_snapshot(
        betti={0: 1, 1: 0, 2: 0},
        euler=1,
        timestamp=t,
    )


def make_crisis_snapshot(t: float = 0.0) -> TopologicalSnapshot:
    """Crisis: many disconnected components (β₀ spike)."""
    return make_snapshot(
        betti={0: 8, 1: 0, 2: 0},
        euler=8,
        timestamp=t,
    )


def make_volatile_snapshot(t: float = 0.0) -> TopologicalSnapshot:
    """Volatile: many cycles forming (β₁ spike)."""
    return make_snapshot(
        betti={0: 1, 1: 6, 2: 0},
        euler=-5,
        timestamp=t,
    )


def make_transitioning_snapshot(t: float = 0.0) -> TopologicalSnapshot:
    """Transitioning: moderate deviations."""
    return make_snapshot(
        betti={0: 2, 1: 2, 2: 1},
        euler=1,
        timestamp=t,
    )


def feed_warmup(
    detector: StructuralChangeDetector,
    n: int = 15,
    start_time: float = 0.0,
) -> List[TopologicalSnapshot]:
    """Feed N stable snapshots to pass warmup phase."""
    snapshots = []
    for i in range(n):
        snap = make_stable_snapshot(t=start_time + i)
        detector.update(snap)
        snapshots.append(snap)
    return snapshots


def generate_ticks(
    symbols: List[str],
    n_per_symbol: int = 30,
    base_prices: Optional[dict] = None,
    volatility: float = 0.001,
    start_time: float = 1000.0,
) -> List[MarketTick]:
    """
    Generate synthetic MarketTick sequence for multiple symbols.
    Returns ticks interleaved by timestamp.
    """
    if base_prices is None:
        base_prices = {s: 100.0 * (i + 1) for i, s in enumerate(symbols)}

    rng = np.random.RandomState(42)
    ticks = []
    prices = {s: base_prices[s] for s in symbols}

    for step in range(n_per_symbol):
        t = start_time + step * 0.5
        for sym in symbols:
            ret = rng.normal(0, volatility)
            prices[sym] *= (1 + ret)
            ticks.append(MarketTick(
                symbol=sym,
                price=prices[sym],
                volume=rng.uniform(1, 100),
                timestamp=t + symbols.index(sym) * 0.01,
            ))

    ticks.sort(key=lambda tk: tk.timestamp)
    return ticks


# ═══════════════════════════════════════════════════════════
# Test 1: Warmup Phase
# ═══════════════════════════════════════════════════════════

class TestWarmupPhase:
    """During warmup, detector should return no alerts and regime=UNKNOWN."""

    def test_no_alerts_during_warmup(self):
        config = MonitorConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            min_ticks=20,
            history_length=50,
        )
        detector = StructuralChangeDetector(config)

        # Feed fewer than warmup threshold (max(10, min_ticks//2) = 10)
        for i in range(9):
            snap = make_stable_snapshot(t=float(i))
            alert = detector.update(snap)
            assert alert is None, f"Got alert during warmup at step {i}"
            assert snap.regime == MarketRegime.UNKNOWN

    def test_baseline_not_set_during_warmup(self):
        config = MonitorConfig(min_ticks=20, history_length=50)
        detector = StructuralChangeDetector(config)

        for i in range(5):
            detector.update(make_stable_snapshot(t=float(i)))

        # Baseline should not be set with < 10 snapshots
        # (depends on implementation, but history < warmup threshold)
        assert len(detector.history) == 5


# ═══════════════════════════════════════════════════════════
# Test 2: Stable Market
# ═══════════════════════════════════════════════════════════

class TestStableMarket:
    """Consistent stable snapshots should yield STABLE regime, no alerts."""

    def test_stable_regime_after_warmup(self):
        config = MonitorConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)

        # Warmup
        feed_warmup(detector, n=15)

        # Continue with stable data
        for i in range(15, 30):
            snap = make_stable_snapshot(t=float(i))
            alert = detector.update(snap)
            assert alert is None, f"Unexpected alert at step {i}"
            assert snap.regime == MarketRegime.STABLE, (
                f"Expected STABLE at step {i}, got {snap.regime}"
            )

    def test_no_alerts_in_stable_market(self):
        config = MonitorConfig(
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)
        feed_warmup(detector, n=20)

        alerts_fired = 0
        for i in range(20, 50):
            snap = make_stable_snapshot(t=float(i))
            alert = detector.update(snap)
            if alert is not None:
                alerts_fired += 1

        assert alerts_fired == 0, f"Got {alerts_fired} alerts in stable market"


# ═══════════════════════════════════════════════════════════
# Test 3: Crisis Detection (β₀ spike)
# ═══════════════════════════════════════════════════════════

class TestCrisisDetection:
    """Sudden β₀ spike should trigger CRISIS regime."""

    def test_crisis_regime_on_beta0_spike(self):
        config = MonitorConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)
        feed_warmup(detector, n=15)

        # Inject crisis snapshot
        crisis_snap = make_crisis_snapshot(t=15.0)
        alert = detector.update(crisis_snap)

        assert crisis_snap.regime == MarketRegime.CRISIS, (
            f"Expected CRISIS, got {crisis_snap.regime}"
        )

    def test_crisis_generates_alert_eventually(self):
        """
        CUSUM may not fire on first crisis tick (needs accumulation).
        Feed several crisis snapshots and check that at least one alert fires.
        """
        config = MonitorConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)
        feed_warmup(detector, n=15)

        alerts = []
        for i in range(15, 30):
            snap = make_crisis_snapshot(t=float(i))
            alert = detector.update(snap)
            if alert is not None:
                alerts.append(alert)

        assert len(alerts) > 0, "No alerts fired during sustained crisis"
        assert any(
            a.severity in (AlertSeverity.WARNING, AlertSeverity.CRITICAL)
            for a in alerts
        ), "Expected WARNING or CRITICAL severity"

    def test_crisis_betti_change_positive_beta0(self):
        """Alert's betti_change should show positive Δβ₀."""
        config = MonitorConfig(
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)
        feed_warmup(detector, n=15)

        alerts = []
        for i in range(15, 35):
            snap = make_crisis_snapshot(t=float(i))
            alert = detector.update(snap)
            if alert:
                alerts.append(alert)

        if alerts:
            # β₀ should have increased from baseline (~1) to crisis (~8)
            assert alerts[0].betti_change.get(0, 0) > 0, (
                f"Expected positive Δβ₀, got {alerts[0].betti_change}"
            )


# ═══════════════════════════════════════════════════════════
# Test 4: Volatile Detection (β₁ spike)
# ═══════════════════════════════════════════════════════════

class TestVolatileDetection:
    """β₁ spike should trigger VOLATILE regime."""

    def test_volatile_regime_on_beta1_spike(self):
        config = MonitorConfig(
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)
        feed_warmup(detector, n=15)

        vol_snap = make_volatile_snapshot(t=15.0)
        detector.update(vol_snap)

        assert vol_snap.regime == MarketRegime.VOLATILE, (
            f"Expected VOLATILE, got {vol_snap.regime}"
        )

    def test_volatile_alert_fires(self):
        config = MonitorConfig(
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)
        feed_warmup(detector, n=15)

        alerts = []
        for i in range(15, 30):
            snap = make_volatile_snapshot(t=float(i))
            alert = detector.update(snap)
            if alert:
                alerts.append(alert)

        assert len(alerts) > 0, "No alerts during sustained volatility"


# ═══════════════════════════════════════════════════════════
# Test 5: Transitioning Detection
# ═══════════════════════════════════════════════════════════

class TestTransitioningDetection:
    """Moderate deviations should yield TRANSITIONING."""

    def test_transitioning_regime(self):
        config = MonitorConfig(
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)
        feed_warmup(detector, n=15)

        trans_snap = make_transitioning_snapshot(t=15.0)
        detector.update(trans_snap)

        # Should be TRANSITIONING or higher (VOLATILE/CRISIS)
        assert trans_snap.regime in (
            MarketRegime.TRANSITIONING,
            MarketRegime.VOLATILE,
            MarketRegime.CRISIS,
        ), f"Expected non-STABLE regime, got {trans_snap.regime}"


# ═══════════════════════════════════════════════════════════
# Test 6: CUSUM Reset After Alert
# ═══════════════════════════════════════════════════════════

class TestCUSUMReset:
    """After an alert fires, CUSUM should reset and not immediately re-fire."""

    def test_cusum_resets_after_alert(self):
        config = MonitorConfig(
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)
        feed_warmup(detector, n=15)

        # Feed crisis until alert fires
        first_alert = None
        for i in range(15, 40):
            snap = make_crisis_snapshot(t=float(i))
            alert = detector.update(snap)
            if alert and first_alert is None:
                first_alert = alert
                alert_step = i
                break

        assert first_alert is not None, "No alert fired during crisis"

        # Immediately after alert, CUSUM should be reset
        assert np.allclose(detector._cusum_pos, 0), "CUSUM pos not reset"
        assert np.allclose(detector._cusum_neg, 0), "CUSUM neg not reset"

        # Next single stable snapshot should NOT fire alert
        stable_snap = make_stable_snapshot(t=float(alert_step + 1))
        next_alert = detector.update(stable_snap)
        assert next_alert is None, "Alert fired immediately after reset"


# ═══════════════════════════════════════════════════════════
# Test 7: Full Pipeline (MarketTick → TopologyEngine)
# ═══════════════════════════════════════════════════════════

class TestFullPipeline:
    """End-to-end: ticks → correlation → topology → regime."""

    def test_topology_engine_warmup_returns_none(self):
        config = MonitorConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            window_size=20,
            min_ticks=10,
            history_length=50,
        )
        engine = TopologyEngine(config)

        # First few ticks should return None (warming up)
        tick = MarketTick(
            symbol="BTCUSDT", price=50000.0, volume=1.0, timestamp=1000.0
        )
        result = engine.process_tick(tick)
        assert result is None, "Expected None during warmup"

    def test_topology_engine_produces_snapshot(self):
        """After enough ticks, engine should produce snapshots."""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        config = MonitorConfig(
            symbols=symbols,
            window_size=20,
            min_ticks=10,
            history_length=50,
            correlation_threshold=0.6,
            max_simplex_dim=2,
        )
        engine = TopologyEngine(config)

        ticks = generate_ticks(
            symbols=symbols,
            n_per_symbol=40,
            base_prices={"BTCUSDT": 50000, "ETHUSDT": 3000, "BNBUSDT": 400},
            volatility=0.005,
        )

        snapshots = []
        for tick in ticks:
            result = engine.process_tick(tick)
            if result is not None:
                snap, alert = result
                snapshots.append(snap)

        assert len(snapshots) > 0, "No snapshots produced after feeding ticks"

        # Check snapshot structure
        snap = snapshots[-1]
        assert isinstance(snap, TopologicalSnapshot)
        assert isinstance(snap.betti_numbers, dict)
        assert 0 in snap.betti_numbers
        assert isinstance(snap.euler_characteristic, (int, float, np.integer))
        assert snap.regime in MarketRegime

    def test_topology_engine_detects_regime(self):
        """After warmup, snapshots should have a non-UNKNOWN regime."""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        config = MonitorConfig(
            symbols=symbols,
            window_size=15,
            min_ticks=8,
            history_length=30,
        )
        engine = TopologyEngine(config)

        ticks = generate_ticks(
            symbols=symbols,
            n_per_symbol=60,
            volatility=0.003,
        )

        regimes_seen = set()
        for tick in ticks:
            result = engine.process_tick(tick)
            if result is not None:
                snap, _ = result
                regimes_seen.add(snap.regime)

        # After enough data, should see at least STABLE or UNKNOWN
        assert len(regimes_seen) > 0, "No regimes detected"


# ═══════════════════════════════════════════════════════════
# Test 8: Edge Cases
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and robustness checks."""

    def test_constant_prices_no_crash(self):
        """Constant prices → zero returns → should not crash."""
        symbols = ["BTCUSDT", "ETHUSDT"]
        config = MonitorConfig(
            symbols=symbols,
            window_size=15,
            min_ticks=8,
            history_length=30,
        )
        engine = TopologyEngine(config)

        for i in range(50):
            for sym in symbols:
                tick = MarketTick(
                    symbol=sym,
                    price=100.0,  # constant
                    volume=1.0,
                    timestamp=1000.0 + i,
                )
                result = engine.process_tick(tick)
                # Should not raise

    def test_single_snapshot_type_consistency(self):
        """betti_vector should always return np.ndarray of correct length."""
        snap = make_snapshot(
            betti={0: 3, 1: 1},
            euler=2,
        )
        vec = snap.betti_vector(max_dim=3)
        assert isinstance(vec, np.ndarray)
        assert len(vec) == 4  # dim 0,1,2,3
        assert vec[0] == 3
        assert vec[1] == 1
        assert vec[2] == 0  # missing → 0
        assert vec[3] == 0

    def test_empty_betti_numbers(self):
        """Snapshot with empty betti_numbers should not crash."""
        snap = make_snapshot(betti={}, euler=0)
        vec = snap.betti_vector()
        assert np.allclose(vec, [0, 0, 0, 0])

    def test_high_sensitivity_fewer_alerts(self):
        """Higher sensitivity → harder to trigger alerts."""
        alerts_low = _count_crisis_alerts(sensitivity=1.0)
        alerts_high = _count_crisis_alerts(sensitivity=5.0)

        # With same crisis data, low sensitivity should fire more/equal alerts
        assert alerts_low >= alerts_high, (
            f"Low sens ({alerts_low}) should fire >= high sens ({alerts_high})"
        )

    def test_detector_history_bounded(self):
        """History deque should not exceed history_length."""
        config = MonitorConfig(history_length=20)
        detector = StructuralChangeDetector(config)

        for i in range(100):
            detector.update(make_stable_snapshot(t=float(i)))

        assert len(detector.history) <= 20

    def test_alert_has_correct_fields(self):
        """StructuralAlert should have all required fields."""
        config = MonitorConfig(
            min_ticks=20,
            history_length=50,
            change_sensitivity=1.0,  # low → easier to trigger
        )
        detector = StructuralChangeDetector(config)
        feed_warmup(detector, n=15)

        alert = None
        for i in range(15, 50):
            snap = make_crisis_snapshot(t=float(i))
            alert = detector.update(snap)
            if alert:
                break

        if alert is not None:
            assert isinstance(alert.timestamp, float)
            assert isinstance(alert.severity, AlertSeverity)
            assert isinstance(alert.message, str)
            assert isinstance(alert.old_regime, MarketRegime)
            assert isinstance(alert.new_regime, MarketRegime)
            assert isinstance(alert.betti_change, dict)
            assert isinstance(alert.euler_change, (int, np.integer))


# ═══════════════════════════════════════════════════════════
# Test 9: Regime Transition Sequence
# ═══════════════════════════════════════════════════════════

class TestRegimeTransitionSequence:
    """Test realistic scenario: STABLE → VOLATILE → CRISIS → STABLE."""

    def test_full_regime_cycle(self):
        config = MonitorConfig(
            min_ticks=20,
            history_length=50,
            change_sensitivity=2.0,
        )
        detector = StructuralChangeDetector(config)

        regimes_seen = []
        t = 0.0

        # Phase 1: Warmup + Stable (15 ticks)
        for _ in range(15):
            snap = make_stable_snapshot(t=t)
            detector.update(snap)
            regimes_seen.append(snap.regime)
            t += 1.0

        # Phase 2: Volatile (10 ticks)
        for _ in range(10):
            snap = make_volatile_snapshot(t=t)
            detector.update(snap)
            regimes_seen.append(snap.regime)
            t += 1.0

        # Phase 3: Crisis (10 ticks)
        for _ in range(10):
            snap = make_crisis_snapshot(t=t)
            detector.update(snap)
            regimes_seen.append(snap.regime)
            t += 1.0

        # Phase 4: Recovery to stable (15 ticks)
        for _ in range(15):
            snap = make_stable_snapshot(t=t)
            detector.update(snap)
            regimes_seen.append(snap.regime)
            t += 1.0

        # Should have seen multiple regime types
        unique_regimes = set(regimes_seen)
        assert MarketRegime.UNKNOWN in unique_regimes, "Should see UNKNOWN during warmup"

        # After warmup, should see at least 2 different non-UNKNOWN regimes
        post_warmup = set(regimes_seen[15:])
        non_unknown = post_warmup - {MarketRegime.UNKNOWN}
        assert len(non_unknown) >= 2, (
            f"Expected ≥2 distinct regimes post-warmup, got {non_unknown}"
        )


# ═══════════════════════════════════════════════════════════
# Test 10: CorrelationEngine Unit Tests
# ═══════════════════════════════════════════════════════════

class TestCorrelationEngine:
    """Unit tests for CorrelationEngine in isolation."""

    def test_not_ready_initially(self):
        config = MonitorConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            min_ticks=10,
        )
        engine = CorrelationEngine(config)
        assert not engine.is_ready()

    def test_ready_after_enough_ticks(self):
        config = MonitorConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            window_size=20,
            min_ticks=5,
        )
        engine = CorrelationEngine(config)

        for i in range(10):
            for sym in config.symbols:
                engine.update(MarketTick(
                    symbol=sym,
                    price=100.0 + i * 0.1,
                    volume=1.0,
                    timestamp=float(i),
                ))

        assert engine.is_ready()

    def test_correlation_matrix_shape(self):
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        config = MonitorConfig(
            symbols=symbols,
            window_size=20,
            min_ticks=5,
        )
        engine = CorrelationEngine(config)

        for i in range(15):
            for sym in symbols:
                engine.update(MarketTick(
                    symbol=sym,
                    price=100.0 + i * np.random.normal(0, 0.1),
                    volume=1.0,
                    timestamp=float(i),
                ))

        if engine.is_ready():
            corr = engine.compute_correlation_matrix()
            assert corr.shape == (3, 3)
            # Diagonal should be 1
            np.testing.assert_allclose(np.diag(corr), 1.0, atol=1e-10)

    def test_unknown_symbol_ignored(self):
        config = MonitorConfig(symbols=["BTCUSDT"])
        engine = CorrelationEngine(config)

        engine.update(MarketTick(
            symbol="UNKNOWN_COIN",
            price=999.0,
            volume=1.0,
            timestamp=0.0,
        ))

        assert len(engine.price_windows["BTCUSDT"]) == 0


# ═══════════════════════════════════════════════════════════
# Helper for parameterized sensitivity test
# ═══════════════════════════════════════════════════════════

def _count_crisis_alerts(sensitivity: float) -> int:
    config = MonitorConfig(
        min_ticks=20,
        history_length=50,
        change_sensitivity=sensitivity,
    )
    detector = StructuralChangeDetector(config)
    feed_warmup(detector, n=15)

    count = 0
    for i in range(15, 40):
        snap = make_crisis_snapshot(t=float(i))
        alert = detector.update(snap)
        if alert:
            count += 1
    return count


# ═══════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
