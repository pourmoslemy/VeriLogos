Layer 4: Application Layer
===========================

Market monitoring engines and real-time topological analysis.

Topology Engine
---------------

.. automodule:: verilogos.application.engines
   :members:
   :undoc-members:
   :show-inheritance:

Real-time Monitor
-----------------

.. automodule:: verilogos.application.realtime.monitor
   :members:
   :undoc-members:
   :show-inheritance:

Data Models
-----------

.. automodule:: verilogos.application.models
   :members:
   :undoc-members:
   :show-inheritance:

Data Sources
------------

.. automodule:: verilogos.application.sources.base
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: verilogos.application.sources.kucoin
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: verilogos.application.sources.nobitex
   :members:
   :undoc-members:
   :show-inheritance:

Key Components
--------------

**CorrelationEngine**
    Computes rolling correlation matrices from market tick data.

**VietorisRipsBuilder**
    Constructs simplicial complexes from correlation matrices using Vietoris-Rips filtration.

**TopologyAnalyzer**
    Computes Betti numbers and topological features from simplicial complexes.

**StructuralChangeDetector**
    Detects regime changes using CUSUM-based anomaly detection on topological features.

**TopologyEngine**
    Orchestrates the full pipeline: correlation → complex → topology → detection.

Market Regimes
--------------

The system detects four market regimes:

- ``STABLE``: Low volatility, consistent topology
- ``VOLATILE``: High volatility, rapidly changing topology
- ``CRISIS``: Extreme correlation (β₀ spike), market stress
- ``TRANSITIONING``: Regime shift in progress
