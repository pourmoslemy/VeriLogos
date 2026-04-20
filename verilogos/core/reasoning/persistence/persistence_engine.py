"""
Persistence engine for reasoning layer with legacy-compatible API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from verilogos.core.topology.persistence.barcode import Barcode


@dataclass
class PersistenceInterval:
    """Legacy interval wrapper used across reasoning/application layers."""

    dimension: int
    birth: float
    death: Optional[float] = None
    birth_simplex: Optional[tuple] = None
    death_simplex: Optional[tuple] = None

    @property
    def lifetime(self) -> float:
        if self.death is None or self.death == float("inf"):
            return float("inf")
        return float(self.death - self.birth)

    @property
    def persistence(self) -> float:
        return self.lifetime

    @property
    def is_finite(self) -> bool:
        return self.death is not None and self.death != float("inf")


class PersistenceEngine:
    """
    Reasoning-layer persistence API.

    Returns stable, legacy-compatible outputs:
    - compute_diagram(sc) -> List[PersistenceInterval]
    - compute_barcodes(sc) -> Dict[int, List[(birth, death_or_None)]]
    - compute_score(sc) -> float
    - compute_entropy(sc) -> Dict[int, float]
    """

    def __init__(self, min_persistence: float = 0.0, max_dimension: int = 3):
        self.min_persistence = float(min_persistence)
        self.max_dimension = int(max_dimension)

    @staticmethod
    def _norm(simplex: Any) -> Tuple[int, ...]:
        if isinstance(simplex, tuple):
            return tuple(sorted(simplex))
        if isinstance(simplex, int):
            return (simplex,)
        if hasattr(simplex, "vertices"):
            return tuple(sorted(simplex.vertices))
        return tuple(sorted(simplex))

    def _extract_grouped(self, obj: Any) -> Dict[int, List[Tuple[int, ...]]]:
        if hasattr(obj, "simplices") and isinstance(obj.simplices, dict):
            grouped: Dict[int, List[Tuple[int, ...]]] = {}
            for key, values in obj.simplices.items():
                if isinstance(key, int):
                    for simplex in values:
                        normed = self._norm(simplex)
                        grouped.setdefault(len(normed) - 1, []).append(normed)
                else:
                    normed = self._norm(key)
                    grouped.setdefault(len(normed) - 1, []).append(normed)
            for dim in list(grouped.keys()):
                grouped[dim] = sorted(set(grouped[dim]))
            return grouped

        if hasattr(obj, "steps"):
            grouped: Dict[int, set] = {}
            for sub in getattr(obj, "steps", []):
                simplices = getattr(sub, "simplices", {})
                if isinstance(simplices, dict):
                    for _dim, faces in simplices.items():
                        for simplex in faces:
                            normed = self._norm(simplex)
                            grouped.setdefault(len(normed) - 1, set()).add(normed)
                else:
                    for simplex in simplices:
                        normed = self._norm(simplex)
                        grouped.setdefault(len(normed) - 1, set()).add(normed)
            return {dim: sorted(vals) for dim, vals in grouped.items()}

        return {}

    def compute_diagram(self, obj: Any) -> List[PersistenceInterval]:
        grouped = self._extract_grouped(obj)
        if not grouped:
            return []

        simplices: List[Tuple[int, ...]] = []
        for dim in sorted(grouped.keys()):
            simplices.extend(grouped[dim])
        total = len(simplices)
        if total == 0:
            return []

        simplex_to_idx = {s: i for i, s in enumerate(simplices)}
        intervals: List[PersistenceInterval] = []
        paired_indices = set()

        max_dim = min(max(grouped.keys()), self.max_dimension)
        for dim in range(1, max_dim + 1):
            cols = grouped.get(dim, [])
            rows = grouped.get(dim - 1, [])
            if not cols or not rows:
                continue

            row_index = {s: i for i, s in enumerate(rows)}
            columns: List[List[int]] = []
            for simplex in cols:
                boundary = []
                for k in range(len(simplex)):
                    face = tuple(sorted(simplex[:k] + simplex[k + 1 :]))
                    if face in row_index:
                        boundary.append(row_index[face])
                columns.append(sorted(boundary))

            low: Dict[int, int] = {}
            for col_idx in range(len(columns)):
                while columns[col_idx]:
                    pivot = columns[col_idx][-1]
                    if pivot in low:
                        other = low[pivot]
                        columns[col_idx] = sorted(set(columns[col_idx]) ^ set(columns[other]))
                    else:
                        low[pivot] = col_idx
                        break

            for pivot_row, col_idx in low.items():
                birth_simplex = rows[pivot_row]
                death_simplex = cols[col_idx]
                birth = float(simplex_to_idx[birth_simplex]) / float(total)
                death = float(simplex_to_idx[death_simplex]) / float(total)
                if death <= birth:
                    death = birth + (1.0 / float(total))

                interval = PersistenceInterval(
                    dimension=dim - 1,
                    birth=birth,
                    death=death,
                    birth_simplex=birth_simplex,
                    death_simplex=death_simplex,
                )
                if interval.is_finite and interval.lifetime < self.min_persistence:
                    continue

                intervals.append(interval)
                paired_indices.add(simplex_to_idx[birth_simplex])
                paired_indices.add(simplex_to_idx[death_simplex])

        for simplex in simplices:
            idx = simplex_to_idx[simplex]
            if idx not in paired_indices:
                intervals.append(
                    PersistenceInterval(
                        dimension=len(simplex) - 1,
                        birth=float(idx) / float(total),
                        death=None,
                        birth_simplex=simplex,
                        death_simplex=None,
                    )
                )

        intervals.sort(key=lambda iv: (iv.dimension, iv.birth))
        return intervals

    def compute_barcodes(self, obj: Any) -> Dict[int, List[Tuple[float, Optional[float]]]]:
        class _IntervalList(list):
            def finite(self) -> List[Tuple[float, float]]:
                return [(b, d) for b, d in self if d is not None and d != float("inf")]

            def infinite(self) -> List[Tuple[float, Optional[float]]]:
                return [(b, d) for b, d in self if d is None or d == float("inf")]

            def total_persistence(self) -> float:
                return sum((d - b) for b, d in self.finite())

            def max_persistence(self) -> float:
                finite = self.finite()
                if not finite:
                    return 0.0
                return max((d - b) for b, d in finite)

        diagram = self.compute_diagram(obj)
        by_dim: Dict[int, _IntervalList] = {}
        for interval in diagram:
            by_dim.setdefault(interval.dimension, _IntervalList()).append(
                (interval.birth, interval.death)
            )
        return by_dim

    def compute_score(self, obj: Any) -> float:
        finite = [iv for iv in self.compute_diagram(obj) if iv.is_finite]
        if not finite:
            return 0.0
        return float(sum(iv.lifetime for iv in finite) / len(finite))

    def compute_entropy(self, obj: Any) -> Dict[int, float]:
        barcodes = self.compute_barcodes(obj)
        entropy: Dict[int, float] = {}
        for dim, pairs in barcodes.items():
            bc = Barcode([(birth, death if death is not None else float("inf")) for birth, death in pairs])
            finite = bc.finite()
            if not finite:
                entropy[dim] = 0.0
                continue
            lifetimes = [d - b for b, d in finite if d - b > 0]
            total = sum(lifetimes)
            if total <= 0:
                entropy[dim] = 0.0
                continue
            probs = [lt / total for lt in lifetimes]
            entropy[dim] = max(0.0, -sum(p * math.log(p + 1e-12) for p in probs))
        return entropy
