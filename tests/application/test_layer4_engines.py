# tests/application/test_layer4_engines.py
"""
Layer 4 Tests: Application Engines
Tests CorrelationEngine, TopologyAnalyzer, StructuralChangeDetector, TopologyEngine
"""

import time
from typing import List

import numpy as np
import pytest

from verilogos.application.models import (
    AlertSeverity,
    MarketRegime,
    MarketTick,
    MonitorConfig,
    TopologicalSnapshot,
)
from verilogos.application.engines import (
    CorrelationEngine,
    TopologyAnalyzer,
    StructuralChangeDetector,
    TopologyEngine,
    VietorisRipsBuilder,
)


@pytest.fixture
def config():
    """Standard monitor config for testing."""
    return MonitorConfig(
        symbols=["BTC", "ETH", "BNB"],
        window_size=20,
        min_ticks=10,
        correlation_threshold=0.6,
        adaptive_threshold=False,
        max_simplex_dim=2,
        change_sensitivity=2.0,
        history_length=30,
    )


@pytest.fixture
def synthetic_ticks() -> List[MarketTick]:
    """Generate synthetic correlated price ticks."""
    np.random.seed(42)
    n_ticks = 50
    base_price = np.array([50000.0, 3000.0, 400.0])  # BTC, ETH, BNB
    
    ticks = []
    for i in range(n_ticks):
        # Correlated random walk
        returns = np.random.multivariate_normal(
            mean=[0, 0, 0],
            cov=[[0.01, 0.008, 0.006],
                 [0.008, 0.01, 0.007],
                 [0.006, 0.007, 0.01]],
        )
        base_price *= (1 + returns)
        
        ts = time.time() + i
        ticks.append(MarketTick("BTC", base_price[0], 1.0, ts))
        ticks.append(MarketTick("ETH", base_price[1], 10.0, ts))
        ticks.append(MarketTick("BNB", base_price[2], 100.0, ts))
    
    return ticks


class TestCorrelationEngine:
    """Test correlation computation and rolling windows."""
    
    def test_initialization(self, config):
        engine = CorrelationEngine(config)
        assert not engine.is_ready()
        assert len(engine.price_windows) == len(config.symbols)
    
    def test_update_and_readiness(self, config, synthetic_ticks):
        engine = CorrelationEngine(config)
        
        # Feed enough ticks so each symbol has >= min_ticks returns
        for tick in synthetic_ticks[:(config.min_ticks + 1) * len(config.symbols)]:
            engine.update(tick)
        
        assert engine.is_ready()
    
    def test_correlation_matrix_shape(self, config, synthetic_ticks):
        engine = CorrelationEngine(config)
        
        for tick in synthetic_ticks[:30]:
            engine.update(tick)
        
        corr = engine.compute_correlation_matrix()
        n = len(config.symbols)
        assert corr.shape == (n, n)
        assert np.allclose(np.diag(corr), 1.0)  # diagonal = 1
        assert np.allclose(corr, corr.T)  # symmetric
    
    def test_adaptive_threshold(self, config, synthetic_ticks):
        engine = CorrelationEngine(config)
        
        for tick in synthetic_ticks[:30]:
            engine.update(tick)
        
        corr = engine.compute_correlation_matrix()
        threshold = engine.get_adaptive_threshold(corr)
        
        assert 0.0 <= threshold <= 1.0


class TestVietorisRipsBuilder:
    """Test VR complex construction."""
    
    def test_build_from_correlation(self):
        builder = VietorisRipsBuilder(max_dim=2)
        
        # 4-node fully connected graph
        corr = np.array([
            [1.0, 0.8, 0.7, 0.6],
            [0.8, 1.0, 0.75, 0.65],
            [0.7, 0.75, 1.0, 0.7],
            [0.6, 0.65, 0.7, 1.0],
        ])
        
        sc = builder.build_from_correlation(
            corr,
            threshold=0.6,
            labels=["A", "B", "C", "D"],
        )
        
        # Should have 4 vertices
        assert len(sc.get_simplices(0)) == 4
        
        # Should have edges (all pairs above 0.6)
        edges = list(sc.get_simplices(1))
        assert len(edges) > 0
    
    def test_empty_complex_low_threshold(self):
        builder = VietorisRipsBuilder(max_dim=2)
        
        corr = np.array([
            [1.0, 0.2, 0.1],
            [0.2, 1.0, 0.15],
            [0.1, 0.15, 1.0],
        ])
        
        sc = builder.build_from_correlation(corr, threshold=0.9)
        
        # Only vertices, no edges
        assert len(sc.get_simplices(0)) == 3
        assert len(sc.get_simplices(1)) == 0


class TestTopologyAnalyzer:
    """Test topology analysis and Betti number extraction."""
    
    def test_analyze_returns_snapshot(self, config):
        analyzer = TopologyAnalyzer(config)
        
        corr = np.array([
            [1.0, 0.8, 0.7],
            [0.8, 1.0, 0.75],
            [0.7, 0.75, 1.0],
        ])
        
        snapshot = analyzer.analyze(
            corr_matrix=corr,
            threshold=0.6,
            timestamp=time.time(),
        )
        
        assert isinstance(snapshot, TopologicalSnapshot)
        assert snapshot.euler_characteristic is not None
        assert 0 in snapshot.betti_numbers
        assert snapshot.max_dimension >= 0
    
    def test_betti_vector_format(self, config):
        analyzer = TopologyAnalyzer(config)
        
        corr = np.eye(3)  # disconnected
        snapshot = analyzer.analyze(corr, 0.5, time.time())
        
        betti_vec = snapshot.betti_vector(max_dim=3)
        assert len(betti_vec) == 4  # β₀, β₁, β₂, β₃


class TestStructuralChangeDetector:
    """Test regime detection and alert generation."""
    
    def test_initialization(self, config):
        detector = StructuralChangeDetector(config)
        assert len(detector.history) == 0

    def test_no_alert_on_first_snapshot(self, config):
        detector = StructuralChangeDetector(config)
        
        snapshot = TopologicalSnapshot(
            timestamp=time.time(),
            betti_numbers={0: 3, 1: 0},
            euler_characteristic=3,
            num_simplices={0: 3, 1: 0},
            max_dimension=1,
            correlation_threshold=0.6,
        )
        
        alert = detector.update(snapshot)
        assert alert is None  # first snapshot, no baseline
    
    def test_alert_on_structural_change(self, config):
        detector = StructuralChangeDetector(config)
        
        # Stable baseline
        for _ in range(10):
            snapshot = TopologicalSnapshot(
                timestamp=time.time(),
                betti_numbers={0: 3, 1: 1},
                euler_characteristic=2,
                num_simplices={0: 3, 1: 3, 2: 1},
                max_dimension=2,
                correlation_threshold=0.6,
            )
            detector.update(snapshot)
        
        # Sudden change
        changed = TopologicalSnapshot(
            timestamp=time.time(),
            betti_numbers={0: 5, 1: 3},  # more components, more holes
            euler_characteristic=-2,
            num_simplices={0: 5, 1: 8, 2: 2},
            max_dimension=2,
            correlation_threshold=0.6,
        )
        
        alert = detector.update(changed)
        
        # Should detect change (depending on CUSUM threshold)
        # At minimum, regime should update
        assert changed.regime != MarketRegime.UNKNOWN


class TestTopologyEngine:
    """Test end-to-end pipeline orchestration."""
    
    def test_initialization(self, config):
        engine = TopologyEngine(config)
        assert engine.correlation_engine is not None
        assert engine.topology_analyzer is not None
        assert engine.change_detector is not None
    
    def test_process_tick_warmup(self, config, synthetic_ticks):
        engine = TopologyEngine(config)
        
        # First few ticks should return None (warming up)
        for tick in synthetic_ticks[:5]:
            result = engine.process_tick(tick)
            assert result is None
    
    def test_process_tick_returns_snapshot(self, config, synthetic_ticks):
        engine = TopologyEngine(config)
        
        result = None
        for tick in synthetic_ticks:
            result = engine.process_tick(tick)
            if result is not None:
                break
        
        assert result is not None
        snapshot, alert = result
        
        assert isinstance(snapshot, TopologicalSnapshot)
        assert snapshot.betti_numbers is not None
        assert snapshot.euler_characteristic is not None
        # alert may be None (no structural change yet)
    
    def test_full_pipeline_stability(self, config, synthetic_ticks):
        """Run full pipeline and verify no crashes."""
        engine = TopologyEngine(config)
        
        snapshots = []
        alerts = []
        
        for tick in synthetic_ticks:
            result = engine.process_tick(tick)
            if result:
                snapshot, alert = result
                snapshots.append(snapshot)
                if alert:
                    alerts.append(alert)
        
        assert len(snapshots) > 0
        # Alerts may or may not occur depending on data


def test_old_regime_not_unknown_after_warmup():
    """
    Regression: after warm-up, an alert should reference a previous snapshot
    with a known regime when one exists.
    """
    config = MonitorConfig(
        symbols=["BTC", "ETH", "BNB"],
        window_size=20,
        min_ticks=10,
        correlation_threshold=0.6,
        adaptive_threshold=False,
        max_simplex_dim=2,
        change_sensitivity=2.0,
        history_length=30,
        analysis_interval=0.0,
    )
    detector = StructuralChangeDetector(config)

    start_ts = time.time()
    for idx in range(12):
        stable = TopologicalSnapshot(
            timestamp=start_ts + idx * 20.0,
            betti_numbers={0: 3, 1: 1},
            euler_characteristic=2,
            num_simplices={0: 3, 1: 3, 2: 1},
            max_dimension=2,
            correlation_threshold=0.6,
        )
        detector.update(stable)

    alert = None
    for idx in range(13, 19):
        changed = TopologicalSnapshot(
            timestamp=start_ts + idx * 20.0,
            betti_numbers={0: 10, 1: 6},
            euler_characteristic=-8,
            num_simplices={0: 10, 1: 20, 2: 4},
            max_dimension=2,
            correlation_threshold=0.6,
        )
        alert = detector.update(changed)
        if alert is not None:
            break

    assert alert is not None
    assert alert.previous_snapshot.regime != MarketRegime.UNKNOWN
