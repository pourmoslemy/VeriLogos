"""Compatibility shim for elements.simplex.

Re-exports Simplex from the canonical simplices.simplex module
for backward compatibility with legacy import paths.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verilogos.core.topology.simplices.simplex import Simplex

from verilogos.core.topology.simplices.simplex import Simplex
__all__ = ["Simplex"]
