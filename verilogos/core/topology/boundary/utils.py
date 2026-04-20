"""Boundary operators utilities — SANN project."""
import numpy as np
from typing import Optional, List


class BoundaryOperator:
    """Boundary operator ∂_n: C_n -> C_{n-1}."""
    def __init__(self, dim: int):
        self.dim = dim

    def apply(self, chain):
        raise NotImplementedError

    def matrix(self) -> Optional[np.ndarray]:
        return None

    def __repr__(self):
        return f"BoundaryOperator(dim={self.dim})"


class CoboundaryOperator:
    """Coboundary operator δ_n: C_n -> C_{n+1}."""
    def __init__(self, dim: int):
        self.dim = dim

    def apply(self, cochain):
        raise NotImplementedError

    def __repr__(self):
        return f"CoboundaryOperator(dim={self.dim})"


class LaplacianOperator:
    """Simplicial Laplacian L_n = ∂_{n+1}∂_{n+1}^T + ∂_n^T∂_n."""
    def __init__(self, dim: int):
        self.dim = dim

    def apply(self, x):
        raise NotImplementedError

    def __repr__(self):
        return f"LaplacianOperator(dim={self.dim})"


class ChainComplex:
    """Chain complex C_n --∂--> C_{n-1}."""
    def __init__(self, max_dim: int = 3):
        self.max_dim = max_dim
        self._chains = {i: [] for i in range(max_dim + 1)}
        self._boundary_maps: dict = {}

    def add_chain(self, dim: int, chain) -> None:
        self._chains.setdefault(dim, []).append(chain)

    def set_boundary_map(self, dim: int, matrix: np.ndarray) -> None:
        self._boundary_maps[dim] = matrix

    def boundary_map(self, dim: int) -> Optional[np.ndarray]:
        return self._boundary_maps.get(dim)

    def chains(self, dim: int) -> list:
        return self._chains.get(dim, [])

    def betti_number(self, dim: int) -> int:
        try:
            B = self._boundary_maps.get(dim)
            B_next = self._boundary_maps.get(dim + 1)
            rank_B = int(np.linalg.matrix_rank(B)) if B is not None else 0
            rank_B_next = int(np.linalg.matrix_rank(B_next)) if B_next is not None else 0
            n = len(self._chains.get(dim, []))
            return n - rank_B - rank_B_next
        except Exception:
            return 0

    def __repr__(self):
        return f"ChainComplex(max_dim={self.max_dim})"


__all__ = ["BoundaryOperator", "CoboundaryOperator", "LaplacianOperator", "ChainComplex"]
