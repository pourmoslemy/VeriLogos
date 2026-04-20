"""
VeriLogos Core - Unified Public API

This module provides a unified public API for VeriLogos, aggregating all layers
of the architecture into a single importable namespace.

Architecture Layers
-------------------
Layer 0 - Topology Foundation:
    Simplicial complexes, temporal filtrations, persistent homology

Layer 1 - SC-Logic Operations (FROZEN API):
    Modal logic operations on simplicial complexes

Layer 2 - Temporal Semantics:
    Time-indexed filtrations and temporal valuations

Layer 3 - Persistence Engine & Modal Semantics:
    Persistent homology computation and modal entailment evaluation

Quick Start
-----------
>>> from verilogos.core import (
...     SimplicialComplex,
...     Filtration,
...     PersistenceEngine,
...     ModalStatus,
...     SCLogicOperations
... )
>>> 
>>> # Create a simplicial complex
>>> K = SimplicialComplex()
>>> K.add_simplex((0, 1))
>>> K.add_simplex((1, 2))
>>> K.add_simplex((0, 2))
>>> 
>>> # Create a filtration
>>> filt = Filtration()
>>> filt.add_level(0, [(0, 1)])
>>> filt.add_level(1, [(1, 2), (0, 2)])
>>> 
>>> # Compute persistence
>>> engine = PersistenceEngine()
>>> barcodes = engine.compute_barcodes(filt)

Layer-Specific Imports
----------------------
For more granular control, import from specific layers:

>>> from verilogos.core.topology import SimplicialComplex, PersistentHomology
>>> from verilogos.core.logic import ModalStatus, PersistenceEntailmentEvaluator
>>> from verilogos.core.operators import SCLogicOperations
>>> from verilogos.core.reasoning import PersistenceEngine, ReasoningAPI
"""

# Layer 0: Topology Foundation
from verilogos.core.topology import (
    # Complexes
    SimplicialComplex,
    Subcomplex,
    ChainComplex,
    Filtration,
    TemporalValuation,
    TemporalState,
    # Persistence
    PersistentHomology,
    PersistenceInterval,
    Barcode,
)

# Layer 1: SC-Logic Operations (FROZEN API)
from verilogos.core.operators import SCLogicOperations

# Layer 3: Modal Semantics & Persistence Engine
from verilogos.core.logic import (
    ModalStatus,
    EntailmentResult,
    PersistenceEntailmentEvaluator,
)

from verilogos.core.reasoning import (
    PersistenceEngine,
    ReasoningAPI,
)

__all__ = [
    # Layer 0: Topology
    "SimplicialComplex",
    "Subcomplex",
    "ChainComplex",
    "Filtration",
    "TemporalValuation",
    "TemporalState",
    "PersistentHomology",
    "PersistenceInterval",
    "Barcode",
    # Layer 1: SC-Logic (FROZEN)
    "SCLogicOperations",
    # Layer 3: Modal Semantics
    "ModalStatus",
    "EntailmentResult",
    "PersistenceEntailmentEvaluator",
    # Layer 3: Persistence Engine
    "PersistenceEngine",
    "ReasoningAPI",
]

# Version info
__version__ = "0.1.0"
__author__ = "Alireza Pourmoslemi"
