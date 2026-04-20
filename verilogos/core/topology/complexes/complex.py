"""
Simplicial complex data structures for SANN topology.
Maintains structural integrity and O(1) dimension lookups.
"""
from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple


class Simplex:
    """Represents a mathematical simplex."""

    def __init__(self, vertices):
        self.vertices = tuple(sorted(vertices))
        self.dim = len(self.vertices) - 1

    @property
    def dimension(self):
        return self.dim

    def faces(self) -> List["Simplex"]:
        """Return all (dim-1) faces of this simplex."""
        if self.dim <= 0:
            return []
        return [
            Simplex(self.vertices[:i] + self.vertices[i + 1 :])
            for i in range(len(self.vertices))
        ]

    def __repr__(self):
        return f"Simplex({self.vertices})"

    def __eq__(self, other):
        if isinstance(other, Simplex):
            return self.vertices == other.vertices
        return False

    def __hash__(self):
        return hash(self.vertices)

    def __iter__(self):
        return iter(self.vertices)

    def __len__(self):
        return len(self.vertices)


class SimplicialComplex:
    """
    Represents a mathematical Simplicial Complex.

    Internal storage is ``simplices: Dict[int, Set[Tuple[int, ...]]]``
    mapping dimension -> set-of-vertex-tuples.

    Invariants
    ----------
    - Every face of every stored simplex is also stored (closure property).
    - ``max_dim`` always equals the highest key in ``self.simplices``
      (or -1 if the complex is empty).
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self, simplices=None, **kwargs):
        """
        Initialize a simplicial complex.

        Args:
            simplices: ``Dict[int, Set[Tuple]]`` (canonical), or flat
                iterable of tuples/Simplex objects, or ``None``.
        """
        _max_dim = kwargs.pop("max_dimension", None)
        if _max_dim is None:
            _max_dim = kwargs.pop("max_dim", None)
        kwargs.pop("dim", None)
        kwargs.pop("feature_dim", None)
        kwargs.pop("vertices", None)
        self._max_dim_hint: Optional[int] = _max_dim

        self.simplices: Dict[int, Set[Tuple[int, ...]]] = {}

        if simplices is not None:
            if isinstance(simplices, dict) and simplices:
                first_key = next(iter(simplices))
                if isinstance(first_key, int):
                    # Dict[int, Set[Tuple]] — canonical form
                    # We still run add_simplex to enforce closure.
                    for dim in sorted(simplices.keys()):
                        for s in simplices[dim]:
                            self.add_simplex(s)
                else:
                    for s in simplices:
                        self.add_simplex(s)
            else:
                for s in simplices:
                    self.add_simplex(s)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------
    def add_simplex(self, simplex) -> None:
        """
        Add a simplex **and all of its faces** to the complex.

        Accepts: tuple, list, set, frozenset, int (0-simplex), or Simplex.
        """
        verts = self._norm(simplex)
        dim = len(verts) - 1
        bucket = self.simplices.setdefault(dim, set())
        if verts in bucket:
            return  # already present — skip face recursion
        bucket.add(verts)

        # ---- closure: recursively add all proper faces ----
        if dim > 0:
            for i in range(len(verts)):
                face = verts[:i] + verts[i + 1 :]
                self.add_simplex(face)

    # ------------------------------------------------------------------
    # Normalization helper
    # ------------------------------------------------------------------
    @staticmethod
    def _norm(s: Any) -> Tuple[int, ...]:
        """Normalize any simplex-like input to a sorted int-tuple."""
        if isinstance(s, Simplex):
            return s.vertices
        if isinstance(s, int):
            return (s,)
        if isinstance(s, tuple):
            return tuple(sorted(s))
        if isinstance(s, (list, frozenset, set)):
            return tuple(sorted(s))
        if hasattr(s, "vertices"):
            return tuple(sorted(s.vertices))
        return tuple(sorted(s))

    # ------------------------------------------------------------------
    # Properties (attribute-style access required by boundary_ops.py)
    # ------------------------------------------------------------------
    @property
    def max_dim(self) -> int:
        """Highest simplex dimension present. -1 if empty."""
        if self.simplices:
            return max(self.simplices.keys())
        if self._max_dim_hint is not None:
            return self._max_dim_hint
        return -1

    # Keep method form as well for callers that use max_dimension()
    def max_dimension(self) -> int:
        """Return the maximum simplex dimension present in this complex."""
        return self.max_dim

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------
    def get_simplices(self, dim: int) -> Set[Tuple[int, ...]]:
        """Return the set of simplex-tuples at the given dimension."""
        return self.simplices.get(dim, set())

    def get_all_simplices(self) -> List[Tuple[int, ...]]:
        """Return a flat list of all simplex-tuples, sorted by dimension."""
        result: List[Tuple[int, ...]] = []
        for d in sorted(self.simplices.keys()):
            result.extend(sorted(self.simplices[d]))
        return result

    @property
    def vertices(self) -> Set[int]:
        """Return set of all vertex ids in this complex."""
        return {v for t in self.simplices.get(0, set()) for v in t}

    @property
    def edges(self) -> Set[Tuple[int, ...]]:
        """Return set of all 1-simplices (edges)."""
        return self.simplices.get(1, set()).copy()

    @property
    def triangles(self) -> Set[Tuple[int, ...]]:
        """Return set of all 2-simplices (triangles)."""
        return self.simplices.get(2, set()).copy()

    # ------------------------------------------------------------------
    # Homology helpers (delegated to by boundary_ops.py)
    # ------------------------------------------------------------------
    def compute_betti_numbers(
        self, max_dim: Optional[int] = None
    ) -> Dict[int, int]:
        """
        Compute Betti numbers β_k for k = 0 .. max_dim.

        Uses ChainComplex from boundary_ops (lazy import to avoid circular).
        """
        from verilogos.core.topology.boundary.utils import ChainComplex

        if max_dim is None:
            max_dim = self.max_dim
        betti: Dict[int, int] = {}
        if max_dim < 0:
            return betti
        for k in range(max_dim + 1):
            betti[k] = self._betti_k(k)
        return betti

    def _betti_k(self, k: int) -> int:
        """Compute beta_k = dim(ker boundary_k) - dim(im boundary_{k+1})."""
        import numpy as _np
        n_k = len(self.simplices.get(k, set()))
        if n_k == 0:
            return 0
        rank_dk = self._boundary_rank(k, _np)
        rank_dk1 = self._boundary_rank(k + 1, _np)
        return n_k - rank_dk - rank_dk1

    def _boundary_rank(self, k: int, _np) -> int:
        """Compute rank of boundary_k matrix."""
        simplices_k = sorted(self.simplices.get(k, set()))
        simplices_km1 = sorted(self.simplices.get(k - 1, set()))
        if not simplices_k or not simplices_km1:
            return 0
        idx_km1 = {s: i for i, s in enumerate(simplices_km1)}
        mat = _np.zeros((len(simplices_km1), len(simplices_k)), dtype=_np.float64)
        for j, sigma in enumerate(simplices_k):
            for i_face in range(len(sigma)):
                face = sigma[:i_face] + sigma[i_face + 1:]
                if face in idx_km1:
                    mat[idx_km1[face], j] = (-1.0) ** i_face
        return int(_np.linalg.matrix_rank(mat))

    def euler_characteristic(self) -> int:
        """
        Compute Euler characteristic: χ = Σ (-1)^k · \|K_k\|
        """
        chi = 0
        for dim, sset in self.simplices.items():
            chi += ((-1) ** dim) * len(sset)
        return chi

    # ------------------------------------------------------------------
    # Dunder / container protocol
    # ------------------------------------------------------------------
    def __contains__(self, simplex) -> bool:
        verts = self._norm(simplex)
        dim = len(verts) - 1
        return verts in self.simplices.get(dim, set())

    def __len__(self) -> int:
        return sum(len(s) for s in self.simplices.values())

    def __iter__(self):
        """Iterate over all simplex-tuples, low dimension first."""
        for d in sorted(self.simplices.keys()):
            yield from sorted(self.simplices[d])

    def __repr__(self) -> str:
        total = sum(len(s) for s in self.simplices.values())
        dims = dict(sorted(
            {d: len(s) for d, s in self.simplices.items()}.items()
        ))
        return f"SimplicialComplex(total={total}, per_dim={dims})"
