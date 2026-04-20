VeriLogos Documentation
=======================

VeriLogos is a topological data analysis framework for cryptocurrency market regime detection using persistent homology and simplicial complex theory.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   introduction
   THEORY
   architecture
   api/index
   developer_guide
   migration_notes

Introduction
============

VeriLogos applies algebraic topology to financial time series analysis, detecting market regime changes through topological features. The framework implements:

- **Simplicial Complex Theory**: Geometric representation of market correlations
- **Persistent Homology**: Tracking topological features across time
- **SC-Logic**: Modal logic for reasoning about topological properties
- **Real-time Monitoring**: Live market regime detection

Key Features
------------

- **5-Layer Architecture**: Strict separation of concerns with no upward dependencies
- **Type-Safe**: 100% type hint coverage across all public APIs
- **Tested**: 202 tests covering all layers
- **Documented**: Comprehensive API documentation with examples

Quick Start
-----------

Installation::

    pip install -e .

Basic Usage::

    from verilogos.application.engines import TopologyEngine
    from verilogos.application.models import MonitorConfig
    
    config = MonitorConfig(
        symbols=['BTC/USDT', 'ETH/USDT'],
        correlation_window=50,
        max_simplex_dim=2
    )
    
    engine = TopologyEngine(config)
    snapshot = engine.process_tick(market_tick)

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
