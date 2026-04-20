"""SubComplex module for SANN topology.

Provides a dimension-keyed Subcomplex representation used by
SC-Logic operators, graded negation, and temporal valuations.

The canonical internal storage is ``_simplices: Dict[int, Set[Tuple[int, ...]]]``
mapping dimension → set-of-simplex-tuples.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, Iterable, Optional, Set, Tuple, Union

class SubComplex:
    """A subcomplex of a simplicial complex."""

    def __init__(
        self,
        simplices: Any = None,
        ambient: Any = None,
        parent: Any = None,
        auto_close: bool = False,
        **kwargs,
    ):
        self.ambient = ambient if ambient is not None else parent

        self._simplices: Dict[int, Set[Tuple[int, ...]]] = {}

        if simplices is None:
            pass
        elif isinstance(simplices, dict):
            if simplices and isinstance(next(iter(simplices.keys())), int):
                for dim, sset in simplices.items():
                    normed: Set[Tuple[int, ...]] = set()
                    for s in sset:
                        normed.add(self._normalize(s))
                    self._simplices[dim] = normed
            else:
                for s in simplices:
                    self._add_one(s)
        elif isinstance(simplices, (set, frozenset, list, tuple)):
            if simplices and isinstance(next(iter(simplices)), (str, int)):
                self._add_one(tuple(simplices))
            else:
                for s in simplices:
                    self._add_one(s)
        elif hasattr(simplices, 'simplices'):
            self.ambient = simplices
        else:
            try:
                for s in simplices:
                    self._add_one(s)
            except TypeError:
                pass

        if auto_close:
            self._close_downward()

    @staticmethod
    def _normalize(s: Any) -> Tuple[int, ...]:
        if isinstance(s, tuple):
            return tuple(sorted(s))
        if isinstance(s, (list, frozenset, set)):
            return tuple(sorted(s))
        if isinstance(s, int):
            return (s,)
        if hasattr(s, 'vertices'):
            return tuple(sorted(s.vertices))
        return tuple(sorted(s))

    def _add_one(self, s: Any) -> None:
        normed = self._normalize(s)
        dim = len(normed) - 1
        self._simplices.setdefault(dim, set()).add(normed)

    def add(self, simplex) -> None:
        self._add_one(simplex)

    def add_simplex(self, simplex) -> None:
        self._add_one(simplex)

    @property
    def simplices(self) -> Dict[int, Set[Tuple[int, ...]]]:
        return self._simplices

    @simplices.setter
    def simplices(self, value):
        if isinstance(value, dict):
            self._simplices = value
        else:
            self._simplices = {}
            if value:
                for s in value:
                    self._add_one(s)

    def __contains__(self, simplex):
        normed = self._normalize(simplex)
        dim = len(normed) - 1
        return normed in self._simplices.get(dim, set())

    def __len__(self):
        return sum(len(s) for s in self._simplices.values())

    def __bool__(self):
        return any(len(s) > 0 for s in self._simplices.values())

    def __eq__(self, other):
        if not isinstance(other, SubComplex):
            return NotImplemented
        return self._simplices == other._simplices

    def __hash__(self):
        items = []
        for dim in sorted(self._simplices):
            items.append((dim, frozenset(self._simplices[dim])))
        return hash(tuple(items))

    def __and__(self, other: "SubComplex") -> "SubComplex":
        result_simplices: Dict[int, Set[Tuple[int, ...]]] = {}
        all_dims = set(self._simplices.keys()) | set(other._simplices.keys())
        for dim in all_dims:
            intersection = self._simplices.get(dim, set()) & other._simplices.get(dim, set())
            if intersection:
                result_simplices[dim] = intersection
        ambient = self.ambient or other.ambient
        return SubComplex(simplices=result_simplices, ambient=ambient)

    def __or__(self, other: "SubComplex") -> "SubComplex":
        result_simplices: Dict[int, Set[Tuple[int, ...]]] = {}
        all_dims = set(self._simplices.keys()) | set(other._simplices.keys())
        for dim in all_dims:
            union = self._simplices.get(dim, set()) | other._simplices.get(dim, set())
            if union:
                result_simplices[dim] = union
        ambient = self.ambient or other.ambient
        return SubComplex(simplices=result_simplices, ambient=ambient)

    def __invert__(self) -> "SubComplex":
        if self.ambient is None:
            raise ValueError(
                "Cannot compute complement without an ambient complex. "
                "Set self.ambient or pass ambient= to constructor."
            )
        ambient_simplices = self._get_ambient_simplices()
        complement: Dict[int, Set[Tuple[int, ...]]] = {}
        all_dims = set(ambient_simplices.keys()) | set(self._simplices.keys())
        for dim in all_dims:
            diff = ambient_simplices.get(dim, set()) - self._simplices.get(dim, set())
            if diff:
                complement[dim] = diff
        return SubComplex(simplices=complement, ambient=self.ambient)

    def _get_ambient_simplices(self) -> Dict[int, Set[Tuple[int, ...]]]:
        ambient = self.ambient
        if isinstance(ambient, SubComplex):
            return ambient._simplices
        if hasattr(ambient, '_simplices') and isinstance(ambient._simplices, dict):
            return ambient._simplices
        if hasattr(ambient, 'simplices'):
            sset = ambient.simplices
            if isinstance(sset, dict):
                return sset
            result: Dict[int, Set[Tuple[int, ...]]] = {}
            for s in sset:
                v = s.vertices if hasattr(s, 'vertices') else tuple(sorted(s))
                dim = len(v) - 1
                result.setdefault(dim, set()).add(v)
            return result
        return {}

    def _close_downward(self) -> None:
        extra: Dict[int, Set[Tuple[int, ...]]] = {}
        for dim, sset in list(self._simplices.items()):
            for sigma in sset:
                for r in range(1, len(sigma)):
                    for face in combinations(sigma, r):
                        face = tuple(sorted(face))
                        fdim = len(face) - 1
                        extra.setdefault(fdim, set()).add(face)
        for fdim, fset in extra.items():
            self._simplices.setdefault(fdim, set()).update(fset)

    def downward_closure(self) -> "SubComplex":
        new_sc = SubComplex(ambient=self.ambient)
        for dim, sset in self._simplices.items():
            new_sc._simplices.setdefault(dim, set()).update(sset)
        new_sc._close_downward()
        return new_sc

    def is_face_closed(self) -> bool:
        for dim, sset in self._simplices.items():
            if dim == 0:
                continue
            for sigma in sset:
                for i in range(len(sigma)):
                    face = tuple(sorted(sigma[:i] + sigma[i + 1 :]))
                    if face:
                        fdim = len(face) - 1
                        if face not in self._simplices.get(fdim, set()):
                            return False
        return True

    def is_subset_of(self, other: "SubComplex") -> bool:
        for dim, sset in self._simplices.items():
            other_set = other._simplices.get(dim, set())
            if not sset.issubset(other_set):
                return False
        return True

    def get_simplices(self) -> Set[Tuple[int, ...]]:
        result: Set[Tuple[int, ...]] = set()
        for sset in self._simplices.values():
            result.update(sset)
        return result

    @classmethod
    def empty(cls, ambient: Any = None) -> "SubComplex":
        return cls(ambient=ambient)

    @classmethod
    def from_simplices(
        cls,
        ambient: Any,
        simplices: Dict[int, Set[Tuple[int, ...]]],
        auto_close: bool = False,
    ) -> "SubComplex":
        return cls(simplices=simplices, ambient=ambient, auto_close=auto_close)

    def __repr__(self):
        total = sum(len(s) for s in self._simplices.values())
        return f"SubComplex(simplices={total})"

Subcomplex = SubComplex

__all__ = ["SubComplex", "Subcomplex"]
