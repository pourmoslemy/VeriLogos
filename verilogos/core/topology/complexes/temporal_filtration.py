"""
Temporal Filtration Module

Implements temporal filtrations and valuations for simplicial complexes.
Provides support for time-indexed subcomplexes and proposition valuations.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .complex import SimplicialComplex
from .subcomplex import Subcomplex


# ============================================================================
# Utility Functions
# ============================================================================

def _normalize_to_tuple(simplex: Union[int, Tuple, Any]) -> Tuple[int, ...]:
    """
    Convert any data type to a normalized tuple.

    Supports:
    - int → (int,)
    - tuple → tuple(sorted(...))
    - Simplex object → tuple(sorted(s.vertices))
    
    Args:
        simplex: Input as int, tuple, or Simplex object
        
    Returns:
        tuple: Normalized and sorted version
        
    Raises:
        TypeError: If simplex type is not supported
    """
    if isinstance(simplex, int):
        return (simplex,)
    elif isinstance(simplex, tuple):
        return tuple(sorted(simplex))
    elif hasattr(simplex, "vertices"):
        return tuple(sorted(simplex.vertices))
    else:
        raise TypeError(f"Unsupported simplex type: {type(simplex)}")


# ============================================================================
# Filtration Class
# ============================================================================

class Filtration:
    """
    Represents a temporal filtration {∅ = K₀ ⊆ K₁ ⊆ ... ⊆ Kₙ = K}.
    
    A filtration is a nested sequence of subcomplexes where each step
    is contained in the next, building up to the ambient complex.
    
    Attributes:
        ambient: The maximal simplicial complex K
        steps: List of subcomplexes representing K₀, K₁, ..., Kₙ
    """

    def __init__(
        self, 
        ambient_complex: Optional[SimplicialComplex] = None, 
        steps: Optional[List[Subcomplex]] = None
    ,
        filtration_steps=None
    ):
        """
        Initialize filtration.

        Args:
            ambient_complex: The maximal complex K (optional for test flexibility)
            steps: Pre-defined filtration steps (optional)
            
        Raises:
            ValueError: If K₀ is not face-closed or filtration not monotonic
        """
        self.ambient = ambient_complex

        # Handle filtration_steps alias for steps
        if filtration_steps is not None and steps is None:
            steps = filtration_steps

        if steps is not None:
            # CRITICAL: Validate K_0 is face-closed
            if len(steps) > 0:
                if steps and hasattr(steps[0], 'is_face_closed') and callable(getattr(steps[0], 'is_face_closed', None)) and not steps[0].is_face_closed():
                    raise ValueError(
                        "K_0 must be face-closed! "
                        "Initial filtration step must contain only vertices or be properly face-closed."
                    )

            # Validate monotonicity: Kₜ ⊆ Kₜ₊₁
            for i in range(len(steps) - 1):
                if not self._is_subset(steps[i], steps[i + 1]):
                    raise ValueError(f"Filtration not monotonic at step {i}")

            self.steps = steps
        else:
            # Start with empty filtration
            self.steps = []

    @property
    def n(self) -> int:
        """
        Get number of time steps (n = len(steps) - 1).
        
        Returns:
            int: Number of transitions in filtration, or -1 if empty
        """
        return len(self.steps) - 1

    def get_step(self, t: int) -> Subcomplex:
        """
        Get the subcomplex K_t at time t.
        
        Args:
            t: Time index
            
        Returns:
            Subcomplex at time t
            
        Raises:
            IndexError: If time out of range
        """
        if t < 0 or t >= len(self.steps):
            raise IndexError(f"Time {t} out of range [0, {len(self.steps)-1}]")
        return self.steps[t]

    def add_level(self, t: int, simplices) -> None:
        """
        Add or extend filtration level ``t`` with provided simplices.
        """
        if t < 0:
            raise ValueError("time index must be non-negative")

        while len(self.steps) <= t:
            self.steps.append(Subcomplex(simplices=set(), ambient=self.ambient))

        target = self.steps[t]
        for simplex in simplices:
            target.add_simplex(simplex)

    def _is_subset(self, A: 'Subcomplex', B: 'Subcomplex') -> bool:
        """
        Check if A ⊆ B. Robustly handles both dict-based and flat list/set-based simplices.
        """
        # Helper function to extract a flat set of simplices from either structure
        def get_flat_simplices(subcomplex: Subcomplex) -> Set[Tuple[int, ...]]:
            if isinstance(subcomplex.simplices, dict):
                # Flatten the dict values
                flat = set()
                for dim_simplices in subcomplex.simplices.values():
                    for s in dim_simplices:
                        flat.add(tuple(sorted(s)))
                return flat
            else:
                # It's already a flat iterable (list or set)
                return {tuple(sorted(s)) for s in subcomplex.simplices}

        faces_A = get_flat_simplices(A)
        faces_B = get_flat_simplices(B)

        return faces_A.issubset(faces_B)

    def get_simplices_at_dimension(self, dimension: int, time_step: Optional[int] = None) -> List[Tuple[int, ...]]:
        """
        Get simplices of a given dimension from the filtration.
        
        Args:
            dimension: The homological dimension (0=vertices, 1=edges, 2=triangles, etc.)
            time_step: If specified, return simplices from the subcomplex at this step.
                      If None, collect all simplices from all steps (union).
        
        Returns:
            List of simplex vertex tuples
        """
        if time_step is not None:
            # Return simplices from a specific step
            if time_step < 0 or time_step >= len(self.steps):
                return []
            
            step = self.steps[time_step]
            simplices = []
            
            if isinstance(step.simplices, dict):
                # Dict structure: dim -> set of simplices
                if dimension in step.simplices:
                    for simplex in step.simplices[dimension]:
                        if isinstance(simplex, int):
                            simplices.append((simplex,))
                        elif isinstance(simplex, tuple):
                            simplices.append(tuple(sorted(simplex)))
                        else:
                            simplices.append(tuple(sorted(simplex)))
            else:
                # Flat structure: set of tuples
                for simplex in step.simplices:
                    if isinstance(simplex, int):
                        simplices.append((simplex,))
                    elif isinstance(simplex, tuple):
                        simplices.append(tuple(sorted(simplex)))
                    else:
                        try:
                            simplices.append(tuple(sorted(simplex)))
                        except TypeError:
                            simplices.append((simplex,))
            
            return simplices
        else:
            # Collect all simplices from all steps (union)
            all_simplices = {}
            
            for step in self.steps:
                if isinstance(step.simplices, dict):
                    # Dict structure: dim -> set of simplices
                    if dimension in step.simplices:
                        if dimension not in all_simplices:
                            all_simplices[dimension] = set()
                        for simplex in step.simplices[dimension]:
                            if isinstance(simplex, int):
                                all_simplices[dimension].add((simplex,))
                            elif isinstance(simplex, tuple):
                                all_simplices[dimension].add(tuple(sorted(simplex)))
                            else:
                                all_simplices[dimension].add(tuple(sorted(simplex)))
            
            # Extract simplices for requested dimension
            if dimension in all_simplices:
                return list(all_simplices[dimension])
            return []


# ============================================================================
# Temporal Valuation Class
# ============================================================================

class TemporalValuation:
    """
    Temporal valuation: V(p, t) for propositions over time.

    For each proposition p, maintains a sequence of subcomplexes
    V(p, 0), V(p, 1), ..., V(p, n) where V(p, t) ⊆ K_t.
    
    This represents the truth value of propositions evolving through
    the filtration steps.
    
    Attributes:
        filtration: The underlying temporal filtration
        valuations: Dict mapping proposition names to sequences of subcomplexes
        ambient: The ambient simplicial complex (optional)
    """

    @classmethod
    def from_barcodes(
        cls,
        filtration_or_barcodes,
        barcodes: Optional[List[List['PersistenceInterval']]] = None,
        proposition_names: Optional[List[str]] = None,
    ) -> 'TemporalValuation':
        """
        Construct TemporalValuation from persistence barcodes.
        
        This is the primary method for topological valuation (Layer 4).
        It evaluates proposition P as TRUE at time t only if birth <= t < death.
        
        This enforces that valuation is strictly driven by topological lifespan.
        
        Args:
            filtration: The underlying temporal filtration
            barcodes: List of PersistenceIntervals per proposition
                     barcodes[i] = intervals for proposition i
            proposition_names: Optional list of proposition names
                              If None, auto-generate names prop_0, prop_1, etc.
            
        Returns:
            TemporalValuation instance with topology-driven valuations
            
        Note:
            Mathematical Foundation: V(p, t) = True iff there exists interval I 
            in barcodes(p) such that birth(I) <= t < death(I)
            
        """
        if barcodes is None and isinstance(filtration_or_barcodes, dict):
            raw_barcodes = filtration_or_barcodes
            max_t = 0
            for intervals in raw_barcodes.values():
                for birth, death in intervals:
                    max_t = max(max_t, int(birth))
                    if death is not None:
                        max_t = max(max_t, int(death))
            filtration = Filtration(steps=[Subcomplex(simplices=set()) for _ in range(max_t + 1 or 1)])
            valuations = {"prop_0": [Subcomplex(simplices=set()) for _ in range(filtration.n + 1)]}
            return cls(filtration, valuations)

        filtration = filtration_or_barcodes
        if barcodes is None:
            barcodes = []

        n_steps = filtration.n
        if proposition_names is None:
            proposition_names = [f"prop_{i}" for i in range(len(barcodes))]

        if len(proposition_names) != len(barcodes):
            raise ValueError(
                f"Number of proposition names ({len(proposition_names)}) "
                f"does not match number of barcode sets ({len(barcodes)})"
            )

        valuations = {}
        for prop_name, prop_barcodes in zip(proposition_names, barcodes):
            valuation_sequence = []
            for t in range(n_steps + 1):
                active_simplices = set()
                for interval in prop_barcodes:
                    birth = getattr(interval, "birth", interval[0])
                    death = getattr(interval, "death", interval[1])
                    if birth <= t and (death is None or t < death):
                        generator = getattr(interval, "generator", None)
                        active_simplices.add(generator if generator else (t,))

                valuation_sequence.append(
                    Subcomplex(simplices=active_simplices) if active_simplices else Subcomplex(simplices=set())
                )
            valuations[prop_name] = valuation_sequence

        return cls(filtration, valuations)

    def __init__(
        self,
        filtration: Filtration,
        valuations: Optional[Dict[str, List[Subcomplex]]] = None,
        ambient_complex=None,
    ):
        """
        Initialize temporal valuation with dual construction modes:
        
        Mode 1: Topological (from_barcodes classmethod)
        Mode 2: Traditional (direct constructor with valuations dict)
        
        Args:
            filtration: The underlying filtration
            valuations: Manual valuations (for backward compatibility)
            ambient_complex: Ambient complex reference (optional)
            
        Raises:
            ValueError: If valuation sequences have incorrect length
        """
        self.filtration = filtration
        self.valuations = valuations if valuations is not None else {}
        self.ambient = ambient_complex or (filtration.ambient if hasattr(filtration, 'ambient') else None)
        
        # Validate sequence lengths match filtration (if valuations provided)
        if valuations is not None:
            for prop, sequence in valuations.items():
                if len(sequence) != filtration.n + 1:
                    raise ValueError(
                        f"Valuation sequence for '{prop}' has length {len(sequence)}, "
                        f"expected {filtration.n + 1} (filtration has {filtration.n + 1} steps)"
                    )

            # Validate containment: V(p, t) ⊆ K_t for all t
            for t, v_t in enumerate(sequence):
                k_t = filtration.get_step(t)
                if not self._is_contained(v_t, k_t):
                    raise ValueError(
                        f"V({prop}, {t}) is not contained in K_{t}. "
                        "All valuation simplices must be simplices of the filtration step."
                    )

    def _get_all_simplices(self, subcomplex: Subcomplex) -> Set[tuple]:
        """
        Extract all simplices from a Subcomplex (normalized).
        
        Args:
            subcomplex: Target Subcomplex
            
        Returns:
            set: Set of all simplices as normalized tuples
        """
        all_simplices = set()
        if isinstance(subcomplex.simplices, dict):
            for dim, faces in subcomplex.simplices.items():
                for face in faces:
                    normalized = tuple(face) if not isinstance(face, tuple) else face
                    all_simplices.add(normalized)
        else:
            for face in subcomplex.simplices:
                normalized = tuple(face) if not isinstance(face, tuple) else face
                all_simplices.add(normalized)
        return all_simplices

    def _is_contained(self, subcomplex_v: Subcomplex, subcomplex_k: Subcomplex) -> bool:
        """
        Check if subcomplex V is contained in K (V ⊆ K).
        Robustly handles both dict-based and flat list/set-based simplices.
        
        Args:
            subcomplex_v: First subcomplex
            subcomplex_k: Second subcomplex
            
        Returns:
            bool: True if V ⊆ K
        """
        # Helper function to extract a flat set of simplices from either structure
        def get_flat_simplices(subcomplex: Subcomplex) -> Set[Tuple[int, ...]]:
            if isinstance(subcomplex.simplices, dict):
                # Flatten the dict values
                flat = set()
                for dim_simplices in subcomplex.simplices.values():
                    for s in dim_simplices:
                        if isinstance(s, int):
                            flat.add((s,))
                        elif isinstance(s, tuple):
                            flat.add(s)
                        else:
                            try:
                                flat.add(tuple(sorted(s)))
                            except TypeError:
                                flat.add((s,))
                return flat
            else:
                # It's already a flat iterable (list or set)
                return {
                    tuple(sorted(s)) if not isinstance(s, tuple) else s
                    for s in subcomplex.simplices
                }

        faces_v = get_flat_simplices(subcomplex_v)
        faces_k = get_flat_simplices(subcomplex_k)

        return faces_v.issubset(faces_k)

    def is_emergent(self, prop: str, simplex: tuple, time: int) -> bool:
        """
        Check if simplex emerges at time t: present at t but not at t-1.

        Args:
            prop: Proposition name
            simplex: Simplex to check (tuple)
            time: Time point

        Returns:
            bool: True if simplex appears at t but not at t-1
        """
        if prop not in self.valuations:
            return False

        seq = self.valuations[prop]
        if time >= len(seq) or time == 0:
            return False

        # Normalize simplex
        normalized = tuple(simplex) if not isinstance(simplex, tuple) else simplex

        # Check presence at t and absence at t-1
        current_simplices = self._get_all_simplices(seq[time])
        previous_simplices = self._get_all_simplices(seq[time - 1])

        return normalized in current_simplices and normalized not in previous_simplices

    def is_persistent(
        self, 
        prop: str, 
        simplex: tuple, 
        start_time: int, 
        end_time: int
    ) -> bool:
        """
        Check if simplex persists from start_time to end_time (inclusive).

        Args:
            prop: Proposition name
            simplex: Simplex to check
            start_time: Start time
            end_time: End time (inclusive)

        Returns:
            bool: True if simplex exists throughout the entire interval
        """
        if prop not in self.valuations:
            return False

        seq = self.valuations[prop]
        if end_time >= len(seq) or start_time < 0:
            return False

        normalized = tuple(simplex) if not isinstance(simplex, tuple) else simplex

        # Check presence at all time points
        for t in range(start_time, end_time + 1):
            all_simplices = self._get_all_simplices(seq[t])
            if normalized not in all_simplices:
                return False

        return True

    def compute_lifespan(self, prop: str, simplex: tuple) -> int:
        """
        Calculate the lifespan of a simplex in a proposition.

        Args:
            prop: Proposition name
            simplex: Simplex to check

        Returns:
            int: Number of consecutive time points where simplex exists
        """
        if prop not in self.valuations:
            return 0

        normalized = tuple(simplex) if not isinstance(simplex, tuple) else simplex
        seq = self.valuations[prop]
        lifespan = 0

        for subcomplex in seq:
            all_simplices = self._get_all_simplices(subcomplex)
            if normalized in all_simplices:
                lifespan += 1

        return lifespan

    def first_appearance(self, prop: str) -> Optional[int]:
        """
        Find first time t where V(p,t) is non-empty.

        Args:
            prop: Proposition name
            
        Returns:
            Time index or None if never appears
        """
        if prop not in self.valuations:
            return None

        sequence = self.valuations[prop]
        for t in range(len(sequence)):
            if sequence[t].simplices:  # Non-empty
                return t

        return None

    def decay_time(self, prop: str) -> Optional[int]:
        """
        Find first time t where V(p,t) becomes empty (after being non-empty).

        Args:
            prop: Proposition name
            
        Returns:
            Time index or None if never decays
        """
        if prop not in self.valuations:
            return None

        sequence = self.valuations[prop]
        was_nonempty = False

        for t in range(len(sequence)):
            is_nonempty = bool(sequence[t].simplices)

            if was_nonempty and not is_nonempty:
                return t

            was_nonempty = is_nonempty

        return None

    def emerges_at(self, prop: str) -> Optional[int]:
        """
        Return first time index where proposition becomes non-empty.
        
        Args:
            prop: Proposition name
            
        Returns:
            Time index of first non-empty valuation or ``None`` if never appears
        """
        if prop not in self.valuations:
            return None
        for t, subcomplex in enumerate(self.valuations[prop]):
            if bool(subcomplex):
                return t
        return None

    def persists_from(self, prop: str) -> Optional[int]:
        """
        Return the earliest time index where proposition is persistent to the end.
        
        Proposition must be non-empty for every time step from this index onward.
        
        Args:
            prop: Proposition name
            
        Returns:
            Earliest start index with end-persistent support, or ``None``.
        """
        if prop not in self.valuations:
            return None

        sequence = self.valuations[prop]
        horizon = len(sequence) - 1
        for t_start in range(horizon + 1):
            persistent = True
            for t in range(t_start, horizon + 1):
                if not bool(sequence[t]):
                    persistent = False
                    break
            if persistent:
                return t_start

        return None

    def __getitem__(self, prop: str) -> List[Subcomplex]:
        """
        Get valuation sequence for proposition.
        
        Args:
            prop: Proposition name
            
        Returns:
            List of subcomplexes representing V(p,0), V(p,1), ..., V(p,n)
        """
        return self.valuations[prop]

    def get_valuation(self, prop: str, t: int) -> Subcomplex:
        """
        Get the subcomplex V(p, t) for a proposition at time t.

        Args:
            prop: Proposition name
            t: Time index

        Returns:
            Subcomplex at time t for the given proposition
        """
        return self.valuations[prop][t]

    def emergence_time(self, prop: str) -> Optional[int]:
        """Alias for first_appearance. Returns first time prop becomes non-empty."""
        return self.first_appearance(prop)


# === Phase C3 Compatibility Alias ===
TemporalFiltration = Filtration

__all__ = [
    "Filtration",
    "TemporalFiltration",
    "TemporalValuation",
    "PersistenceInterval",
]
