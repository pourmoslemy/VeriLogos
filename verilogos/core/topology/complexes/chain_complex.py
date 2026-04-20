"""
Chain Complex for SANN topology module.
Auto-generated to resolve missing module imports.
"""
from typing import Dict, List, Optional
import numpy as np


class ChainComplex:
    """
    A chain complex: sequence of abelian groups connected by boundary operators.
    C_n --∂_n--> C_{n-1} --∂_{n-1}--> ... --∂_1--> C_0
    """
    def __init__(self, max_dim: int = 3):
        self.max_dim = max_dim
        self._chains: Dict[int, List] = {i: [] for i in range(max_dim + 1)}
        self._boundary_maps: Dict[int, Optional[np.ndarray]] = {}

    def add_chain(self, dim: int, chain) -> None:
        if 0 <= dim <= self.max_dim:
            self._chains[dim].append(chain)

    def set_boundary_map(self, dim: int, matrix: np.ndarray) -> None:
        self._boundary_maps[dim] = matrix

    def boundary_map(self, dim: int) -> Optional[np.ndarray]:
        return self._boundary_maps.get(dim)

    def chains(self, dim: int) -> List:
        return self._chains.get(dim, [])

    def betti_number(self, dim: int) -> int:
        """Compute Betti number at dimension dim (rank of homology group)."""
        try:
            B = self._boundary_maps.get(dim)
            B_next = self._boundary_maps.get(dim + 1)
            rank_B = int(np.linalg.matrix_rank(B)) if B is not None else 0
            rank_B_next = int(np.linalg.matrix_rank(B_next)) if B_next is not None else 0
            n_chains = len(self._chains.get(dim, []))
            return n_chains - rank_B - rank_B_next
        except Exception:
            return 0

    def __repr__(self):
        return f"ChainComplex(max_dim={self.max_dim}, chains={[len(v) for v in self._chains.values()]})"
