from typing import Tuple, Iterable, Union
from .simplex import normalize_simplex, simplex_dimension

"""
K-simplex utilities compatible with SANN topology stack.

Grounded on:
- complex.Simplex (619-line version)
- boundary_ops chain_group and normalize_simplex
- subcomplex dimension conventions

Provides:
- KSimplex class (lightweight)
- promote_to_k_simplex
- is_k_simplex
"""

from typing import Tuple, Iterable, Union

from .simplex import normalize_simplex, simplex_dimension


class KSimplex:
    """
    Lightweight K-simplex structure.

    This is *not* the main Simplex class from complex.py.

    It is a minimal wrapper for boundary_ops cases where:
    - we need explicit dimension k
    - we need normalized tuple
    """
    def __init__(self, vertices: Iterable[int]):
        st = normalize_simplex(vertices)
        self.vertices: Tuple[int, ...] = st
        self.dimension: int = simplex_dimension(st)

    def __repr__(self):
        return f"KSimplex(dim={self.dimension}, vertices={self.vertices})"

    def __len__(self):
        return len(self.vertices)

    def to_tuple(self):
        return self.vertices


def is_k_simplex(obj) -> bool:
    """
    Check if object is a valid k-simplex wrapper.
    """
    return isinstance(obj, KSimplex)


def promote_to_k_simplex(obj: Union[Iterable[int], Tuple[int, ...], KSimplex]) -> KSimplex:
    """
    Promote any simplex-like object to KSimplex.

    Grounded by:
    - boundary_ops.chain_group requires canonical wrapping
    - chain_complex/ChainComplex may depend on explicit dimension
    """
    if isinstance(obj, KSimplex):
        return obj

    return KSimplex(obj)
