"""
VeriLogos Topology Layer (Layer 0)

This module provides the foundational topology data structures for VeriLogos,
implementing simplicial complexes, temporal filtrations, and persistent homology.

Core Components
---------------
Simplicial Complexes:
    - SimplicialComplex: Main complex data structure
    - Subcomplex: Subcomplex representation
    - ChainComplex: Chain complex for homology computation

Temporal Structures:
    - Filtration: Time-indexed sequence of complexes
    - TemporalValuation: Proposition valuations over time
    - TemporalState: State representation at specific time

Persistence:
    - PersistentHomology: Persistent homology computation
    - PersistenceInterval: Birth-death interval representation
    - Barcode: Barcode diagram representation

Example
-------
>>> from verilogos.core.topology import SimplicialComplex, Filtration
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
"""

# Layer 0: Topology Foundation
# Complexes
from verilogos.core.topology.complexes.complex import SimplicialComplex
from verilogos.core.topology.complexes.subcomplex import Subcomplex
from verilogos.core.topology.complexes.chain_complex import ChainComplex
from verilogos.core.topology.complexes.temporal_filtration import (
    Filtration,
    TemporalValuation,
)
from verilogos.core.topology.complexes.temporal_state import TemporalState

# Persistence
from verilogos.core.topology.persistence.persistent_homology import (
    PersistentHomology,
    PersistenceInterval,
)
from verilogos.core.topology.persistence.barcode import Barcode

__all__ = [
    # Complexes
    "SimplicialComplex",
    "Subcomplex",
    "ChainComplex",
    "Filtration",
    "TemporalValuation",
    "TemporalState",
    # Persistence
    "PersistentHomology",
    "PersistenceInterval",
    "Barcode",
]
