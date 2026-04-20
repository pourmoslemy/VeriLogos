"""
Persistent Homology via Delta-Betti Method

Phase 9.1 Implementation
========================
Simple persistent homology computation using Betti number changes.

Key Features:
- Works directly with existing Filtration from temporal_filtration.py
- Uses ChainComplex.rank_of_homology for beta computation
- Tracks birth/death via Betti number changes
- No matrix reduction (deferred to Phase 9.2)

Mathematical Foundation:
    At each time t, compute β_k(K_t) = rank(H_k(K_t))
    When β increases: new features born
    When β decreases: features die
    Remaining features: infinite persistence

Compatible with:
- temporal_filtration.py (412 lines)
- operators/boundary_ops.py (1766 lines) ← CORRECT PATH
- subcomplex.py (326 lines)

Version: 9.1 (Simple Delta-Betti)
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

try:
    import torch
except ImportError:
    torch = None

# ✅ CRITICAL FIX: Correct import path
from ..complexes.temporal_filtration import Filtration
try:
    from ..boundary.boundary_ops import ChainComplex
except ImportError:
    class ChainComplex:
        pass
from ..complexes.complex import SimplicialComplex
from ..complexes.subcomplex import Subcomplex
from ..complexes.temporal_filtration import (
    Filtration,
    TemporalValuation,
    _normalize_to_tuple,
    
)


# ==============================================================================
# INTERNAL UTILITIES
# ==============================================================================

def _extract_simplices_from_subcomplex(subcomplex) -> set:
    """
    Extract all simplices from Subcomplex in canonical tuple form.
    
    Internal helper for PersistentHomology - does NOT use temporal_filtration
    private utilities to maintain architectural separation.
    
    Args:
        subcomplex: Subcomplex instance
        
    Returns:
        Set of normalized simplex tuples
    """
    simplices = set()
    for dim, faces in subcomplex.simplices.items():
        for face in faces:
            # Normalize to tuple
            if isinstance(face, int):
                simplices.add((face,))
            elif isinstance(face, tuple):
                simplices.add(tuple(sorted(face)))
            elif hasattr(face, 'vertices'):
                simplices.add(tuple(sorted(face.vertices)))
            else:
                # Fallback: try converting to tuple
                try:
                    simplices.add(tuple(sorted(face)))
                except:
                    pass
    return simplices


@dataclass
class PersistenceInterval:
    """Backward-compatible persistence interval representation."""
    dimension: int
    birth: float
    death: float = float('inf')

    @property
    def persistence(self) -> float:
        if self.death == float('inf'):
            return float('inf')
        return float(self.death - self.birth)

class PersistentHomology:
    """
    Compute persistent homology from temporal filtration.
    
    Algorithm (Delta-Betti):
        For each dimension k:
            Track β_k(K_t) at each time t
            ∆β > 0 → birth events
            ∆β < 0 → death events
            Remaining → infinite persistence
    
    This is Phase 9.1: simple, correct, foundation for Phase 9.2.
    
    IMPORTANT NOTES:
        - Betti numbers computed on temporary complex per time step
        - NOT a restricted chain complex (Phase 9.2 will address this)
        - H_0 persistence via Delta-Betti is heuristic, not canonical
        - Canonical pairing requires reduction matrix (Phase 9.2)
    
    Attributes:
        filtration: Temporal filtration from temporal_filtration.py
        ambient: Ambient complex (from filtration)
        persistence_pairs: Cached (birth, death) pairs by dimension
    
    Example:
        >>> from verilogos.core.topology.temporal_filtration import Filtration
        >>> from verilogos.core.topology.persistence import PersistentHomology
        >>> ph = PersistentHomology(filtration)
        >>> pairs = ph.compute(dim=1)  # H_1 persistence
        >>> print(pairs)
        [(1, 2), (3, inf)]  # Two 1D features
    """
    
    def __init__(self, filtration: Filtration):
        """
        Initialize PH from existing filtration.
        
        Args:
            filtration: Temporal filtration (K_0 ⊆ K_1 ⊆ ... ⊆ K_n)
                       Must be from temporal_filtration.Filtration
        
        Raises:
            TypeError: If filtration is not a Filtration instance
        """
        if not isinstance(filtration, Filtration):
            raise TypeError(
                f"Expected Filtration, got {type(filtration)}. "
                "Use temporal_filtration.Filtration"
            )
        
        self.filtration = filtration
        self.ambient = filtration.ambient
        
        # Cache for computed persistence pairs
        # Structure: {dim: [(birth, death), ...]}
        self.persistence_pairs: Dict[int, List[Tuple[int, float]]] = {}
    
    def compute(self, dim: int) -> List[Tuple[int, float]]:
        """
        Compute persistence pairs for dimension k.
        
        Algorithm:
            1. For each time t, compute β_k(K_t)
            2. Track changes in β_k:
               - Δβ > 0: birth of (Δβ) new features
               - Δβ < 0: death of (\|Δβ\|) oldest features
            3. Features alive at final time → (birth, ∞)
        
        Args:
            dim: Homology dimension k (0 for components, 1 for loops, etc.)
        
        Returns:
            List of (birth_time, death_time) pairs
            - birth_time: integer time index
            - death_time: integer or float('inf')
        
        Note:
            Results are cached. Subsequent calls return cached values.
        
        Warning (H_0):
            H_0 persistence via Delta-Betti is heuristic and not canonical.
            For exact component tracking, use union-find (Phase 9.3).
        
        Example:
            >>> # Triangle filtration
            >>> pairs = ph.compute(1)
            >>> print(pairs)
            [(1, 2)]  # Loop born at t=1, dies at t=2
        """
        # Check cache first
        if dim in self.persistence_pairs:
            return self.persistence_pairs[dim]
        
        # Edge case: negative dimension
        if dim < 0:
            self.persistence_pairs[dim] = []
            return []
        
        # Track alive features: {feature_id: birth_time}
        alive_features: Dict[int, int] = {}
        next_feature_id = 0
        
        # Storage for completed pairs
        pairs: List[Tuple[int, float]] = []
        
        # Previous Betti number (starts at 0)
        prev_beta = 0
        
        # Iterate through filtration steps
        n_steps = len(self.filtration.steps)
        
        for t in range(n_steps):
            # Get K_t
            K_t = self.filtration.steps[t]
            
            # Compute β_k(K_t) using temporary chain complex
            # NOTE: This is NOT a restricted chain complex
            # Phase 9.2 will introduce proper restriction maps
            beta_t = self._compute_betti_for_subcomplex(K_t, dim)
            
            # Compute change
            delta_beta = beta_t - prev_beta
            
            # Birth events (β increased)
            if delta_beta > 0:
                for _ in range(delta_beta):
                    alive_features[next_feature_id] = t
                    next_feature_id += 1
            
            # Death events (β decreased)
            elif delta_beta < 0:
                num_deaths = -delta_beta
                
                # Kill oldest features (FIFO)
                # Sort by birth time
                sorted_alive = sorted(alive_features.items(), key=lambda x: x[1])
                
                for i in range(min(num_deaths, len(sorted_alive))):
                    feature_id, birth_time = sorted_alive[i]
                    
                    # Record death
                    pairs.append((birth_time, t))
                    
                    # Remove from alive
                    del alive_features[feature_id]
            
            # Update for next iteration
            prev_beta = beta_t
        
        # Remaining features persist to infinity
        for feature_id, birth_time in alive_features.items():
            pairs.append((birth_time, float('inf')))
        
        # Sort by birth time for consistency
        pairs.sort(key=lambda x: x[0])
        
        # Cache and return
        self.persistence_pairs[dim] = pairs
        return pairs
    
    def _compute_betti_for_subcomplex(
        self,
        subcomplex: 'Subcomplex',
        dim: int
    ) -> int:
        """
        Compute Betti number β_k for a subcomplex.
        
        This method constructs a temporary simplicial complex containing
        only the simplices from K_t, then computes homology on that complex.
        
        IMPORTANT:
            This is NOT a restricted chain complex in the categorical sense.
            It is a standalone complex with its own chain group indexing.
            Phase 9.2 will introduce proper restriction maps for efficiency.
        
        Args:
            subcomplex: Subcomplex K_t
            dim: Dimension k
        
        Returns:
            β_k(K_t) = rank of k-th homology group
        
        Implementation Notes:
            - Creates temporary SimplicialComplex with K_t's simplices
            - Adds simplices in dimension order (vertices → edges → ...)
            - Uses ChainComplex from operators/boundary_ops.py
            - Calls rank_of_homology(dim) for Betti number
        
        Performance:
            O(n_t) per time step, where n_t = |K_t|
            Phase 9.2 will optimize to O(∆n_t) using restriction
        """
        # Edge case: empty subcomplex
        if not subcomplex.simplices:
            return 0
        
        # Edge case: dimension not in subcomplex
        if dim not in subcomplex.simplices:
            return 0
        
        # Create temporary SimplicialComplex with only K_t's simplices
        # This is safe because Subcomplex already validated containment
        from ..complexes.complex import SimplicialComplex
        
        temp_complex = SimplicialComplex()
        
        # Add all simplices from subcomplex
        # Must add in order: vertices → edges → triangles → ...
        max_dim = max(subcomplex.simplices.keys())
        
        for d in range(max_dim + 1):
            if d in subcomplex.simplices:
                for simplex in subcomplex.simplices[d]:
                    # Add simplex (automatically adds faces via SimplicialComplex)
                    temp_complex.add_simplex(list(simplex))
        
        # Compute homology on this temporary complex
        betti = temp_complex.compute_betti_numbers(max_dim=dim)
        return betti.get(dim, 0)
    
    def get_diagram(self, dim: int) -> List[Tuple[float, float]]:
        """
        Get persistence diagram (birth, death) points.
        
        Args:
            dim: Homology dimension
        
        Returns:
            List of (birth, death) tuples (same as compute)
        
        Note:
            Alias for compute() for API clarity.
        """
        return self.compute(dim)
    
    def get_barcode(self, dim: int) -> List[Tuple[int, float]]:
        """
        Get barcode intervals.
        
        Args:
            dim: Homology dimension
        
        Returns:
            List of (birth, death) intervals (same as compute)
        
        Note:
            Alias for compute() for API clarity.
        """
        return self.compute(dim)
    
    def total_persistence(self, dim: int) -> float:
        """
        Compute total persistence for dimension k.
        
        Total persistence = Σ (death - birth) for finite intervals
        
        Args:
            dim: Homology dimension
        
        Returns:
            Sum of all finite persistence values
        
        Example:
            >>> pairs = [(0, 2), (1, 3), (2, inf)]
            >>> total = ph.total_persistence(1)
            >>> print(total)
            4.0  # (2-0) + (3-1) = 4
        """
        pairs = self.compute(dim)
        
        total = 0.0
        for birth, death in pairs:
            if death != float('inf'):
                total += (death - birth)
        
        return total
    
    def num_features(self, dim: int) -> int:
        """
        Count number of persistent features in dimension k.
        
        Args:
            dim: Homology dimension
        
        Returns:
            Total count of persistence pairs
        """
        return len(self.compute(dim))
    
    def num_infinite_features(self, dim: int) -> int:
        """
        Count features with infinite persistence.
        
        Args:
            dim: Homology dimension
        
        Returns:
            Count of (birth, ∞) pairs
        """
        pairs = self.compute(dim)
        return sum(1 for _, death in pairs if death == float('inf'))
