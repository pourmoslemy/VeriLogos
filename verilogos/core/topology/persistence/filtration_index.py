r"""
filtration_index.py — Phase 9.2

Builds a total ordering on all simplices respecting filtration time.

Ground contract (temporal_filtration.py):
    - Filtration.steps  : List[Subcomplex]   ← only public timeline API
    - Subcomplex.simplices : Dict[int, Set[Tuple[int,...]]]
    - _get_all_simplices is PRIVATE → never called

Invariant maintained:
    σ ∈ K_t  ∧  τ ∈ K_{t+1} \ K_t   ⟹   index(σ) < index(τ)

Within the same time-step simplices are sorted by
(dimension ASC, tuple lexicographic ASC) for reproducibility.
"""

# BROKEN_IMPORT (auto-commented): from __future__ import annotations
from typing import Dict, List, Optional, Tuple


class FiltrationIndex:
    """Total ordering on simplices induced by a Filtration.

    Attributes
    ----------
    simplex_to_index : Dict[Tuple[int,...], int]
        Canonical simplex  →  global position.
    index_to_simplex : List[Tuple[int,...]]
        Global position  →  canonical simplex.
    simplex_birth_time : Dict[Tuple[int,...], int]
        Canonical simplex  →  first time-step it appears.
    _time_ranges : Dict[int, Tuple[int, int]]
        time  →  (start_idx inclusive, end_idx exclusive) in global order.
    """

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    def __init__(self, filtration) -> None:
        """
        Parameters
        ----------
        filtration : Filtration
            Object whose `.steps` attribute is ``List[Subcomplex]``.
        """
        self.simplex_to_index:  Dict[Tuple[int, ...], int] = {}
        self.index_to_simplex: List[Tuple[int, ...]]       = []
        self.simplex_birth_time: Dict[Tuple[int, ...], int] = {}
        self._time_ranges: Dict[int, Tuple[int, int]]      = {}

        seen: set = set()                          # dedup across steps

        for t, subcomplex in enumerate(filtration.steps):
            start_idx = len(self.index_to_simplex)

            # ── collect NEW simplices at this step ──────────────────
            new_at_t: List[Tuple[int, Tuple[int, ...]]] = []

            for dim in sorted(subcomplex.simplices.keys()):
                for raw in subcomplex.simplices[dim]:
                    canon = _normalize(raw)
                    if canon not in seen:
                        new_at_t.append((dim, canon))
                        seen.add(canon)

            # ── stable sort: dim ASC, then lex ASC ──────────────────
            new_at_t.sort(key=lambda pair: (pair[0], pair[1]))

            # ── assign global indices ───────────────────────────────
            for _dim, canon in new_at_t:
                idx = len(self.index_to_simplex)
                self.simplex_to_index[canon]    = idx
                self.index_to_simplex.append(canon)
                self.simplex_birth_time[canon]  = t

            end_idx = len(self.index_to_simplex)
            self._time_ranges[t] = (start_idx, end_idx)

    # ------------------------------------------------------------------
    # accessors
    # ------------------------------------------------------------------
    def get_index(self, simplex) -> Optional[int]:
        """Return global index of *simplex*, or ``None`` if absent."""
        return self.simplex_to_index.get(_normalize(simplex))

    def get_simplex(self, index: int) -> Tuple[int, ...]:
        """Return the canonical simplex at *index*."""
        return self.index_to_simplex[index]

    def get_birth_time(self, simplex) -> Optional[int]:
        """Return the first time-step at which *simplex* appears."""
        return self.simplex_birth_time.get(_normalize(simplex))

    def total_simplices(self) -> int:
        """Total number of distinct simplices across the filtration."""
        return len(self.index_to_simplex)

    def simplices_at_time(self, t: int) -> List[Tuple[int, ...]]:
        """All simplices **born** (first appearing) at time *t*."""
        if t not in self._time_ranges:
            return []
        lo, hi = self._time_ranges[t]
        return self.index_to_simplex[lo:hi]

    # ------------------------------------------------------------------
    # dunder
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.index_to_simplex)

    def __repr__(self) -> str:
        return (f"FiltrationIndex("
                f"{len(self)} simplices, "
                f"{len(self._time_ranges)} time-steps)")


# ======================================================================
# module-level helper
# ======================================================================
def _normalize(simplex) -> Tuple[int, ...]:
    """Canonical sorted-tuple normalisation (mirrors BoundaryOperator contract).

    Handles: int, tuple, list, set, frozenset, Simplex-objects (have .vertices).
    """
    if hasattr(simplex, 'vertices'):          # Simplex object
        return tuple(sorted(simplex.vertices))
    if isinstance(simplex, int):
        return (simplex,)
    if isinstance(simplex, (tuple, list, set, frozenset)):
        return tuple(sorted(simplex))
    # last-resort
    try:
        return tuple(sorted(simplex))
    except (TypeError, AttributeError):
        raise TypeError(f"Cannot normalise simplex of type {type(simplex)}: {simplex}")
