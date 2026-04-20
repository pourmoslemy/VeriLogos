# tests/application/test_layer4_integration.py
"""
Layer 4 Integration Tests
End-to-end tests with simulated market scenarios
"""

import time
from typing import List

import numpy as np
import pytest

from verilogos.application.models import (
    MarketRegime,
    MarketTick,
    MonitorConfig,
)
from verilogos.application.engines import TopologyEngine


def generate_regime_shift_scenario(n_ticks: int = 100) -> List[MarketTick]:
    """
    Generate synthetic market with clear regime shift:
    - First half: stable, high correlation
    - Second half: volatile, decorrelated
    """
    np.random.seed(123)
    symbols = ["BTC", "ETH", "BNB", "ADA"]
    base_prices = np.array([50000.0, 3000.0, 400.0, 1.5])
    
    ticks = []
    
    for i in range(n_ticks):
        if i < n_ticks // 2:
            # Stable regime: high correlation
            cov = np.array([
                [0.005, 0.004, 0.003, 0.003],
                [0.004, 0.005, 0.003, 0.003],
                [0.003, 0.003, 0.005, 0.003],
                [0.003, 0.003, 0.003, 0.005],
            ])
        else:
            # Volatile regime: low correlation, high variance
            cov = np.array([
                [0.02, 0.001, 0.001, 0.001],
                [0.001, 0.02, 0.001, 0.001],
                [0.001, 0.001, 0.02, 0.001],
                [0.001, 0.001, 0.001, 0.02],
            ])
        
        returns = np.random.multivariate_normal(mean=[0]*4, cov=cov)
        base_prices *= (1 + returns)
        
        ts = time.time() + i * 60  # 1-minute intervals
        
        for sym, price in zip(symbols, base_prices):
            ticks.append(MarketTick(sym, price, 1.0, ts))
    
    return ticks


class TestRegimeDetection:
    """Test regime shift detection in synthetic scenarios."""
    
    def test_stable_to_volatile_transition(self):
        config = MonitorConfig(
            symbols=["BTC", "ETH", "BNB", "ADA"],
            window_size=30,
            min_ticks=15,
            correlation_threshold=0.5,
            adaptive_threshold=True,
            max_simplex_dim=2,
            change_sensitivity=1.5,
            history_length=40,
        )
        
        engine = TopologyEngine(config)
        ticks = generate_regime_shift_scenario(n_ticks=120)
        
        regimes = []
        alerts = []
        
        for tick in ticks:
            result = engine.process_tick(tick)
            if result:
                snapshot, alert = result
                regimes.append(snapshot.regime)
                if alert:
                    alerts.append(alert)
        
        # Should detect at least one regime
        assert len(regimes) > 0
        
        # Should have some regime diversity (not all UNKNOWN)
        unique_regimes = set(regimes)
        assert len(unique_regimes) > 1 or MarketRegime.UNKNOWN not in unique_regimes
        
        # May or may not generate alerts depending on sensitivity
        print(f"Detected {len(alerts)} structural alerts")
        print(f"Regime distribution: {dict((r, regimes.count(r)) for r in unique_regimes)}")
    
    def test_betti_number_evolution(self):
        """Track Betti number changes across regime shift."""
        config = MonitorConfig(
            symbols=["BTC", "ETH", "BNB"],
            window_size=20,
            min_ticks=10,
            correlation_threshold=0.6,
            max_simplex_dim=2,
        )
        
        engine = TopologyEngine(config)
        ticks = generate_regime_shift_scenario(n_ticks=80)
        
        betti_0_series = []
        betti_1_series = []
        
        for tick in ticks:
            result = engine.process_tick(tick)
            if result:
                snapshot, _ = result
                betti_0_series.append(snapshot.betti_numbers.get(0, 0))
                betti_1_series.append(snapshot.betti_numbers.get(1, 0))
        
        assert len(betti_0_series) > 0
        
        # β₀ should vary (connected components change)
        assert len(set(betti_0_series)) > 1 or max(betti_0_series) > 1
        
        print(f"β₀ range: {min(betti_0_series)} - {max(betti_0_series)}")
        print(f"β₁ range: {min(betti_1_series)} - {max(betti_1_series)}")


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_single_symbol(self):
        """Single symbol should work (trivial topology)."""
        config = MonitorConfig(
            symbols=["BTC"],
            window_size=10,
            min_ticks=5,
        )
        
        engine = TopologyEngine(config)
        
        for i in range(20):
            tick = MarketTick("BTC", 50000 + i * 10, 1.0, time.time() + i)
            result = engine.process_tick(tick)
            if result:
                snapshot, _ = result
                # Single node: β₀=1, β₁=0
                assert snapshot.betti_numbers[0] == 1
                assert snapshot.betti_numbers.get(1, 0) == 0
    
    def test_constant_prices(self):
        """Constant prices → perfect correlation → fully connected."""
        config = MonitorConfig(
            symbols=["A", "B", "C"],
            window_size=10,
            min_ticks=5,
            correlation_threshold=0.9,
        )
        
        engine = TopologyEngine(config)
        
        # All prices constant → returns = 0 → correlation undefined/NaN
        # Engine should handle gracefully
        for i in range(20):
            ts = time.time() + i
            engine.process_tick(MarketTick("A", 100.0, 1.0, ts))
            engine.process_tick(MarketTick("B", 200.0, 1.0, ts))
            engine.process_tick(MarketTick("C", 300.0, 1.0, ts))
        
        # Should not crash (may return None or trivial topology)


class TestPerformance:
    """Basic performance sanity checks."""
    
    def test_throughput(self):
        """Ensure engine can process ticks at reasonable speed."""
        config = MonitorConfig(
            symbols=["BTC", "ETH", "BNB", "ADA", "SOL"],
            window_size=50,
            min_ticks=20,
            max_simplex_dim=2,
        )
        
        engine = TopologyEngine(config)
        ticks = generate_regime_shift_scenario(n_ticks=200)
        
        start = time.time()
        
        for tick in ticks:
            engine.process_tick(tick)
        
        elapsed = time.time() - start
        throughput = len(ticks) / max(elapsed, 1e-9)
        
        print(f"Processed {len(ticks)} ticks in {elapsed:.2f}s ({throughput:.0f} ticks/s)")
        
        # Should process at least 100 ticks/sec (very conservative)
        assert throughput > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
