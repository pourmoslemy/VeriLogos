"""
VeriLogos Operators Layer (Layer 1 - SC-Logic)

This module provides modal logic operations on simplicial complexes,
implementing SC-Logic (Simplicial Complex Logic) operations.

Core Components
---------------
SC-Logic Operations:
    - SCLogicOperations: Logical operators (AND, OR, NOT, IMPLIES) on complexes

API Status
----------
FROZEN: This API is frozen and cannot be modified without a major version bump.
Layer 1 is the foundation for all temporal and modal reasoning.

Example
-------
>>> from verilogos.core.operators import SCLogicOperations
>>> from verilogos.core.topology import SimplicialComplex
>>> 
>>> # Create two complexes
>>> K1 = SimplicialComplex()
>>> K1.add_simplex((0, 1))
>>> 
>>> K2 = SimplicialComplex()
>>> K2.add_simplex((1, 2))
>>> 
>>> # Perform logical operations
>>> ops = SCLogicOperations()
>>> union = ops.union(K1, K2)  # OR operation
>>> intersection = ops.intersection(K1, K2)  # AND operation
"""

from verilogos.core.operators.sclogic_ops import SCLogicOperations

__all__ = [
    "SCLogicOperations",
]
