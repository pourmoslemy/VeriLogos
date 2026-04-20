# Introduction to VeriLogos

## What is VeriLogos?

VeriLogos is a topological data analysis (TDA) framework designed for cryptocurrency market regime detection. It applies algebraic topology and persistent homology to identify structural changes in financial markets.

## Core Concepts

### Simplicial Complexes
A simplicial complex is a geometric structure built from vertices, edges, triangles, and higher-dimensional simplices. In VeriLogos, market correlations are represented as simplicial complexes where:

- **Vertices** represent individual assets (e.g., BTC, ETH)
- **Edges** connect highly correlated asset pairs
- **Triangles** represent three-way correlations
- **Higher simplices** capture multi-asset relationships

### Persistent Homology
Persistent homology tracks topological features (connected components, loops, voids) as they appear and disappear across a filtration. Features that persist for long durations are considered significant.

**Key Metrics:**
- **β₀ (Betti-0):** Number of connected components
- **β₁ (Betti-1):** Number of loops/cycles
- **β₂ (Betti-2):** Number of voids

### SC-Logic
Simplicial Complex Logic (SC-Logic) is a modal logic for reasoning about topological properties. It extends classical logic with spatial operators:

- **Negation (¬):** Complement of a subcomplex
- **Conjunction (∧):** Intersection of subcomplexes
- **Disjunction (∨):** Union of subcomplexes
- **Necessity (□):** All faces satisfy a property
- **Possibility (◇):** At least one face satisfies a property

### Temporal Semantics
VeriLogos extends SC-Logic with temporal operators to track how topological features evolve:

- **Emergence:** When a feature first appears
- **Persistence:** How long a feature survives
- **Decay:** When a feature disappears

## Market Regime Detection

VeriLogos identifies four market regimes based on topological features:

### 1. Stable Regime
- **Characteristics:** Low volatility, consistent topology
- **Topology:** Stable β₀, β₁, β₂ values
- **Interpretation:** Normal market conditions

### 2. Volatile Regime
- **Characteristics:** High volatility, rapidly changing topology
- **Topology:** Frequent changes in Betti numbers
- **Interpretation:** Increased uncertainty, rapid price movements

### 3. Crisis Regime
- **Characteristics:** Extreme correlation, market stress
- **Topology:** β₀ spike (all assets move together)
- **Interpretation:** Systemic risk, potential crash

### 4. Transitioning Regime
- **Characteristics:** Regime shift in progress
- **Topology:** Significant change in topological features
- **Interpretation:** Market structure changing

## Use Cases

### 1. Risk Management
- Early detection of market stress
- Portfolio diversification monitoring
- Systemic risk assessment

### 2. Trading Strategies
- Regime-based position sizing
- Correlation breakdown detection
- Market structure arbitrage

### 3. Research
- Market microstructure analysis
- Contagion effect studies
- Network topology evolution

## Architecture Overview

VeriLogos follows a strict 5-layer architecture:

```
Layer 4: Application (Market Monitoring)
         ↓
Layer 3: Persistence (Homology Computation)
         ↓
Layer 2: Temporal (Time-Indexed Filtrations)
         ↓
Layer 1: SC-Logic (Modal Operations)
         ↓
Layer 0: Topology (Simplicial Complexes)
```

**Key Principle:** No upward dependencies. Each layer only imports from lower layers.

## Quick Example

```python
from verilogos.application.engines import TopologyEngine
from verilogos.application.models import MonitorConfig, MarketTick

# Configure monitoring
config = MonitorConfig(
    symbols=['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
    correlation_window=50,
    max_simplex_dim=2,
    sensitivity=0.5
)

# Initialize engine
engine = TopologyEngine(config)

# Process market tick
tick = MarketTick(
    timestamp=1234567890,
    prices={'BTC/USDT': 50000, 'ETH/USDT': 3000, 'BNB/USDT': 400}
)

snapshot, alert = engine.process_tick(tick)

# Check regime
print(f"Regime: {snapshot.regime}")
print(f"Betti numbers: β₀={snapshot.betti_0}, β₁={snapshot.betti_1}")

if alert:
    print(f"Alert: {alert.alert_type} - {alert.message}")
```

## Mathematical Foundation

VeriLogos is based on rigorous mathematical theory:

1. **Algebraic Topology:** Simplicial homology, chain complexes, boundary operators
2. **Persistent Homology:** Filtrations, persistence diagrams, barcodes
3. **Modal Logic:** SC-Logic from "Truth as Geometry" (Definition 2.13)
4. **Temporal Logic:** Linear temporal logic extended to topological spaces

## Performance

- **Real-time Processing:** <100ms per tick for 10 assets
- **Scalability:** Handles up to 50 assets simultaneously
- **Memory Efficient:** Sparse matrix representations
- **Type Safe:** 100% type hint coverage

## Getting Started

See the [Developer Guide](developer_guide.md) for installation instructions and the [API Reference](api/index.rst) for detailed documentation.

## References

1. Zomorodian, A., & Carlsson, G. (2005). "Computing Persistent Homology"
2. Ghrist, R. (2014). "Elementary Applied Topology"
3. "Truth as Geometry" - SC-Logic Definition 2.13
4. Gidea, M., & Katz, Y. (2018). "Topological Data Analysis of Financial Time Series"
