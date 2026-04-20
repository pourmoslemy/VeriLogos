"""Boundary operations compatibility module.

Re-exports Subcomplex for backward compatibility with legacy imports.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verilogos.core.topology.complexes.subcomplex import SubComplex as Subcomplex

from verilogos.core.topology.complexes.subcomplex import Subcomplex

__all__ = ["Subcomplex"]

