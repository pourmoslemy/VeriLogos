"""
Boundary operator for persistence computation over ℤ₂.

Phase 9.2 — builds boundary columns from a filtration of simplices.

Contract:
    Input:  ordered list of simplices (from FiltrationIndex)
    Output: boundary columns as sorted lists of row-indices (ℤ₂)

Mathematical definition:
    ∂(σ) = Σ (-1)^i · (σ without vertex i)
    Over ℤ₂: signs vanish, so ∂(σ) = set of (dim-1)-faces of σ.

Design:
    - No matrix materialization (columns are sparse sorted lists)
    - Compatible with MatrixReduction.reduce()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SimplexEntry:
    """A simplex in the filtration with its metadata."""
    index: int
    vertices: Tuple[int, ...]
    dimension: int
    birth_time: int

    def faces(self) -> List[Tuple[int, ...]]:
        """Return all (dim-1)-faces of this simplex (ℤ₂: no signs)."""
        if self.dimension == 0:
            return []
        return [
            tuple(v for k, v in enumerate(self.vertices) if k != i)
            for i in range(len(self.vertices))
        ]


class PersistenceBoundary:
    """
    Builds and stores boundary columns for the persistence matrix.

    Usage:
        pb = PersistenceBoundary()
        pb.build_from_filtration(filtration_simplices)
        mr = MatrixReduction(pb)
        mr.reduce()
    """

    def __init__(self) -> None:
        self._entries: List[SimplexEntry] = []
        self._simplex_to_index: Dict[Tuple[int, ...], int] = {}
        self._columns: Dict[int, List[int]] = {}
        self._dimensions: Dict[int, int] = {}
        self._birth_times: Dict[int, int] = {}
        self._num_simplices: int = 0
        self._built: bool = False

    # ── Public API ──────────────────────────────────────────────

    def build_from_filtration(
        self,
        simplices: List[Tuple[Tuple[int, ...], int]],
    ) -> None:
        """
        Build boundary columns from an ordered filtration.

        Args:
            simplices: list of (vertex_tuple, birth_time) in filtration order.
                       Must be ordered so that every face of σ appears before σ.
        """
        self._entries.clear()
        self._simplex_to_index.clear()
        self._columns.clear()
        self._dimensions.clear()
        self._birth_times.clear()

        for idx, (vertices, birth_time) in enumerate(simplices):
            verts = tuple(sorted(vertices))
            dim = len(verts) - 1

            entry = SimplexEntry(
                index=idx,
                vertices=verts,
                dimension=dim,
                birth_time=birth_time,
            )
            self._entries.append(entry)
            self._simplex_to_index[verts] = idx
            self._dimensions[idx] = dim
            self._birth_times[idx] = birth_time

            # Build boundary column (sorted list of face indices)
            if dim == 0:
                self._columns[idx] = []
            else:
                col = []
                for face in entry.faces():
                    face_sorted = tuple(sorted(face))
                    if face_sorted in self._simplex_to_index:
                        col.append(self._simplex_to_index[face_sorted])
                    # If face not found, filtration ordering is broken
                    # We skip silently — MatrixReduction.validate will catch it
                col.sort()
                self._columns[idx] = col

        self._num_simplices = len(simplices)
        self._built = True

    # ── Accessors (used by MatrixReduction) ─────────────────────

    @property
    def num_simplices(self) -> int:
        return self._num_simplices

    def get_column(self, j: int) -> List[int]:
        """Return boundary column j as a sorted list of row indices."""
        if not self._built:
            raise RuntimeError("Call build_from_filtration() first")
        return list(self._columns.get(j, []))

    def get_dimension(self, j: int) -> int:
        """Return dimension of simplex j."""
        return self._dimensions.get(j, 0)

    def get_birth_time(self, j: int) -> int:
        """Return birth time of simplex j in the filtration."""
        return self._birth_times.get(j, 0)

    def get_simplex_vertices(self, j: int) -> Optional[Tuple[int, ...]]:
        """Return vertex tuple for simplex j."""
        if 0 <= j < len(self._entries):
            return self._entries[j].vertices
        return None

    def get_all_columns(self) -> Dict[int, List[int]]:
        """Return all boundary columns (copy)."""
        return {k: list(v) for k, v in self._columns.items()}

    def get_simplex_birth_times(self) -> Dict[int, int]:
        """Return mapping of filtration index → birth time."""
        return dict(self._birth_times)

    def get_simplex_dimensions(self) -> Dict[int, int]:
        """Return mapping of filtration index → dimension."""
        return dict(self._dimensions)

    # ── Validation ──────────────────────────────────────────────

    def validate_filtration_order(self) -> bool:
        """Check that every face of σ has a lower index than σ."""
        for entry in self._entries:
            for face in entry.faces():
                face_sorted = tuple(sorted(face))
                if face_sorted not in self._simplex_to_index:
                    return False
                if self._simplex_to_index[face_sorted] >= entry.index:
                    return False
        return True

    # ── Dunder ──────────────────────────────────────────────────

    def __len__(self) -> int:
        return self._num_simplices

    def __repr__(self) -> str:
        if not self._built:
            return "PersistenceBoundary(not built)"
        dims = {}
        for d in self._dimensions.values():
            dims[d] = dims.get(d, 0) + 1
        dim_str = ", ".join(f"dim{k}={v}" for k, v in sorted(dims.items()))
        return f"PersistenceBoundary(n={self._num_simplices}, {dim_str})"
