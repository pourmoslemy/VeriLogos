"""Persistence reasoning module - topological persistence computations."""

from .persistence_engine import PersistenceEngine, PersistenceInterval
from verilogos.core.topology.persistence.persistence_pairs import (
    PersistencePair,
    PersistenceResult,
)

__all__ = [
    'PersistenceEngine',
    'PersistenceInterval',  # Legacy compatibility
    'PersistencePair',
    'PersistenceResult'
]
