from typing import Iterable, Tuple, List, Union

"""
Lightweight simplex utilities compatible with:
- complex.Simplex (619-line canonical version you provided)
- subcomplex.py (311-line version)
- boundary_ops (as described in sann_structure_full.json)

This module provides minimal structural simplex operations:
- normalize_simplex
- is_valid_simplex
- simplex_dimension
- simplex_to_tuple
- faces(simplex)  (wrapper for complex.Simplex or bare tuples)

A Simplex here is NOT the same as complex.Simplex:
- This is a utility-layer simplex handler.
- It works with tuples, lists, sets, or complex.Simplex.
"""

from ..complexes.complex import Simplex as ComplexSimplex

Vertex = int
SimplexTuple = Tuple[Vertex, ...]
SimplexLike = Union[SimplexTuple, Iterable[int], "ComplexSimplex"]


def normalize_simplex(s: SimplexLike) -> SimplexTuple:
    """
    Normalize input simplex to canonical sorted tuple form.

    Grounded from:
    - complex.Simplex always uses tuple(sorted(vertices))
    - boundary_ops expects normalized sorted tuples
    - subcomplex expects sorted tuple form

    Args:
        s: simplex-like object (tuple, list, set, Simplex)

    Returns:
        Sorted tuple of vertices
    """
    if isinstance(s, tuple):
        return tuple(sorted(s))

    if isinstance(s, list) or isinstance(s, set) or isinstance(s, frozenset):
        return tuple(sorted(s))

    if ComplexSimplex is not None and isinstance(s, ComplexSimplex):
        return tuple(sorted(s.vertices))

    raise TypeError(f"Unsupported simplex type for normalize_simplex: {type(s)}")


def simplex_dimension(s: SimplexLike) -> int:
    """
    Compute dimension k of simplex.

    For vertices (v0,...,vk): dimension = k.

    Fully grounded:
    - your complex.Simplex sets dimension = len(vertices)-1
    - your boundary_ops uses same rule
    """
    st = normalize_simplex(s)
    return len(st) - 1


def is_valid_simplex(s: SimplexLike) -> bool:
    """
    Check validity: all vertices are ints, all distinct.

    Canonical TDA rule.
    """
    try:
        st = normalize_simplex(s)
        return all(isinstance(v, int) for v in st) and len(st) == len(set(st))
    except Exception:
        return False


def simplex_to_tuple(s: SimplexLike) -> SimplexTuple:
    """
    Convert simplex-like object to canonical tuple.

    BoundaryOps and Subcomplex depend on this.
    """
    return normalize_simplex(s)


def faces(s: SimplexLike) -> List[SimplexTuple]:
    """
    Compute all (k-1)-faces of a k-simplex.

    Grounded on:
    - complex.Simplex.faces()
    - boundary_ops expectation: removing each vertex once
    """
    st = normalize_simplex(s)
    if len(st) <= 1:
        return []

    f_list = []
    for i in range(len(st)):
        face = st[:i] + st[i + 1:]
        f_list.append(face)

    return f_list


# Critical Alias for Import Compatibility
Simplex = ComplexSimplex


# ── Auto-added stub ──────────────────────────────────────────────────────────
class Simplex:
    """Stub for Simplex — replace with real implementation."""
    def __init__(self, vertices):
        self.vertices = frozenset(vertices)

    def __repr__(self):
        return f"Simplex({sorted(self.vertices)})"

    def __hash__(self):
        return hash(self.vertices)

    def __eq__(self, other):
        return isinstance(other, Simplex) and self.vertices == other.vertices

    def dimension(self) -> int:
        return len(self.vertices) - 1
# ─────────────────────────────────────────────────────────────────────────────


class SimplicialComplex:
    """
    A simplicial complex: a collection of simplices closed under taking faces.
    Auto-generated stub in simplex.py for import compatibility.
    """
    def __init__(self):
        self.simplices = set()

    def add_simplex(self, simplex):
        s = frozenset(simplex)
        self.simplices.add(s)
        # Add all faces
        vertices = list(s)
        for i in range(1, len(vertices) + 1):
            from itertools import combinations
            for face in combinations(vertices, i):
                self.simplices.add(frozenset(face))

    def __repr__(self):
        return f"SimplicialComplex({len(self.simplices)} simplices)"



# ── Auto-added missing names ──────────────────

def build_clique_complex(graph, **kwargs):
    """
    Build a simplicial complex from the cliques of a graph.
    graph: any object with .cliques() method or a networkx Graph.
    """
    kwargs.pop("max_dim", None)
    kwargs.pop("feature_dim", None)
    kwargs.pop("max_dimension", None)

    try:
        import networkx as nx
        if hasattr(graph, "cliques") and callable(graph.cliques):
            cliques = list(graph.cliques())
        elif isinstance(graph, nx.Graph):
            cliques = list(nx.find_cliques(graph))
        else:
            cliques = None

        if cliques is not None:
            sc = SimplicialComplex()
            for clique in cliques:
                for i in range(len(clique)):
                    for j in range(i, len(clique) + 1):
                        sc.add_simplex(frozenset(clique[i:j]))
            return sc
    except ImportError:
        pass
    raise NotImplementedError("build_clique_complex requires networkx")
