"""
VeriLogos Reasoning Layer (Layer 3 - Persistence Engine)

This module provides persistent homology computation and reasoning capabilities
for topological analysis of temporal data.

Core Components
---------------
Persistence Engine:
    - PersistenceEngine: Main engine for computing persistence barcodes
    - PersistenceInterval: Birth-death interval representation

Reasoning API:
    - ReasoningAPI: High-level API for topological reasoning

Example
-------
>>> from verilogos.core.reasoning import PersistenceEngine
>>> from verilogos.core.topology import Filtration
>>> 
>>> # Create a filtration
>>> filt = Filtration()
>>> filt.add_level(0, [(0, 1)])
>>> filt.add_level(1, [(1, 2), (0, 2)])
>>> 
>>> # Compute persistence barcodes
>>> engine = PersistenceEngine()
>>> barcodes = engine.compute_barcodes(filt)
"""

from verilogos.core.reasoning.persistence.persistence_engine import (
    PersistenceEngine,
    PersistenceInterval,
)
from verilogos.core.reasoning.reasoning_api import ReasoningAPI

__all__ = [
    "PersistenceEngine",
    "PersistenceInterval",
    "ReasoningAPI",
]
