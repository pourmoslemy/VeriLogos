"""
Persistence Pair Extraction Module

Phase 9.2 - File #4/5
=====================
Converts reduced boundary matrix (low_map) into birth-death pairs with full metadata.

Contract:
    Input:
        - simplex_birth_times: Dict[int, int] (filtration_index → time)
        - simplex_dimensions: Dict[int, int] (filtration_index → dimension)
        - MatrixReduction.low_map (Dict[int, int])
    
    Output:
        - List[PersistencePair] with complete lifecycle metadata

Critical Rules:
    1. Dimension = dim(birth_simplex), NOT dim(death_simplex)
    2. Infinite bars: simplices NOT in low_map (neither as key nor value)
    3. Finite bars: low_map[death_idx] = birth_idx
    4. All times from filtration, NOT from reduction indices

Mathematical Foundation:
    - Birth: simplex enters filtration
    - Death: simplex kills a cycle (becomes boundary)
    - Persistence = death_time - birth_time
    - Essential classes: never die (infinite persistence)

Compatibility:
    - Zero Core 2.1 dependencies (pure data transformation)
    - Works with any filtration ordering
    - Dimension-agnostic (handles dim=0,1,2,...)

Version: Phase 9.2 Final (Ninja-approved)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class PersistencePair:
    """
    Single persistence pair with complete lifecycle metadata.
    
    Attributes:
        dimension: Homological dimension (from birth simplex)
        birth_index: Filtration index where feature appears
        death_index: Filtration index where feature dies (None = infinite)
        birth_time: Filtration time when feature appears
        death_time: Filtration time when feature dies (None = infinite)
        persistence: Lifespan (death_time - birth_time, None = infinite)
    
    Invariants:
        - dimension >= 0
        - 0 <= birth_index < total_simplices
        - death_index > birth_index (if finite)
        - death_time > birth_time (if finite)
        - persistence = death_time - birth_time (if finite)
    """
    dimension: int
    birth_index: int
    death_index: Optional[int]
    birth_time: int
    death_time: Optional[int]
    persistence: Optional[int]
    
    def is_infinite(self) -> bool:
        """Check if this is an essential (infinite) class."""
        return self.death_index is None
    
    def is_finite(self) -> bool:
        """Check if this is a finite-persistence feature."""
        return self.death_index is not None
    
    def __repr__(self) -> str:
        """Human-readable representation."""
        if self.is_infinite():
            return (
                f"PersistencePair(dim={self.dimension}, "
                f"birth={self.birth_time}, death=∞, pers=∞)"
            )
        else:
            return (
                f"PersistencePair(dim={self.dimension}, "
                f"birth={self.birth_time}, death={self.death_time}, "
                f"pers={self.persistence})"
            )


@dataclass
class PersistenceResult:
    """Compatibility wrapper for persistence outputs."""
    pairs: List[PersistencePair] = field(default_factory=list)
    by_dimension: Dict[int, List[PersistencePair]] = field(default_factory=dict)
    betti_numbers: Dict[int, int] = field(default_factory=dict)


class PersistencePairExtractor:
    """
    Extract persistence pairs from reduced boundary matrix.
    
    Core Algorithm:
        1. Identify birth simplices (NOT in low_map values OR reduced to zero)
        2. Identify death simplices (IN low_map keys with non-zero low)
        3. Match births to deaths via low_map
        4. Compute dimensions from birth simplices
        5. Compute times from filtration timestamps
    
    Edge Cases Handled:
        - Infinite bars (essential classes)
        - Zero-simplices (connected components)
        - Empty filtration
        - All-zero reduction (no deaths)
    
    Attributes:
        simplex_birth_times: Maps filtration_index → birth_time
        simplex_dimensions: Maps filtration_index → dimension
        total_simplices: Total number of simplices in filtration
    """
    
    def __init__(
        self,
        simplex_birth_times: Dict[int, int],
        simplex_dimensions: Dict[int, int],
        total_simplices: int
    ):
        """
        Initialize extractor with filtration metadata.
        
        Args:
            simplex_birth_times: Maps simplex index → filtration time
            simplex_dimensions: Maps simplex index → topological dimension
            total_simplices: Total number of simplices in filtration
        
        Raises:
            ValueError: If metadata is inconsistent
        """
        # Validation
        if len(simplex_birth_times) != total_simplices:
            raise ValueError(
                f"Birth times count ({len(simplex_birth_times)}) "
                f"!= total_simplices ({total_simplices})"
            )
        
        if len(simplex_dimensions) != total_simplices:
            raise ValueError(
                f"Dimensions count ({len(simplex_dimensions)}) "
                f"!= total_simplices ({total_simplices})"
            )
        
        # Check index coverage
        expected_indices = set(range(total_simplices))
        if set(simplex_birth_times.keys()) != expected_indices:
            raise ValueError("Birth times must cover all indices [0, total_simplices)")
        
        if set(simplex_dimensions.keys()) != expected_indices:
            raise ValueError("Dimensions must cover all indices [0, total_simplices)")
        
        self.simplex_birth_times = simplex_birth_times
        self.simplex_dimensions = simplex_dimensions
        self.total_simplices = total_simplices
    
    def extract_pairs(
        self,
        low_map: Dict[int, int]
    ) -> List[PersistencePair]:
        """
        Extract all persistence pairs from reduced boundary matrix.
        
        Algorithm:
            1. Find all death simplices (columns with non-zero low)
            2. Find all birth simplices (NOT killed by any death)
            3. Create finite pairs for deaths
            4. Create infinite pairs for unkilled births
        
        Args:
            low_map: Maps column_index → low_index (from MatrixReduction)
                     - Keys: columns with non-zero low (death simplices)
                     - Values: birth simplices killed by those columns
        
        Returns:
            List of PersistencePair objects (finite + infinite)
            Sorted by (birth_time, dimension, birth_index)
        
        Examples:
            # Simple cycle: edge [1] births, triangle [2] kills it
            >>> low_map = {2: 1}
            >>> pairs = extract_pairs(low_map)
            >>> pairs[0].dimension  # dimension of simplex 1 (edge)
            1
            >>> pairs[0].birth_index
            1
            >>> pairs[0].death_index
            2
        """
        # Step 1: Identify all simplices killed (appear as birth in low_map)
        killed_simplices: Set[int] = set(low_map.values())
        
        # Step 2: Collect finite pairs (deaths)
        finite_pairs: List[PersistencePair] = []
        
        for death_idx, birth_idx in low_map.items():
            # Dimension comes from BIRTH simplex, not death
            dimension = self.simplex_dimensions[birth_idx]
            
            # Times from filtration
            birth_time = self.simplex_birth_times[birth_idx]
            death_time = self.simplex_birth_times[death_idx]
            
            # Compute persistence
            persistence = death_time - birth_time
            
            # Sanity check
            if death_time <= birth_time:
                raise ValueError(
                    f"Death before birth: simplex {birth_idx} (t={birth_time}) "
                    f"killed by {death_idx} (t={death_time})"
                )
            
            pair = PersistencePair(
                dimension=dimension,
                birth_index=birth_idx,
                death_index=death_idx,
                birth_time=birth_time,
                death_time=death_time,
                persistence=persistence
            )
            
            finite_pairs.append(pair)
        
        # Step 3: Collect infinite pairs (unkilled simplices)
        infinite_pairs: List[PersistencePair] = []
        
        for simplex_idx in range(self.total_simplices):
            # Skip if this simplex was killed
            if simplex_idx in killed_simplices:
                continue
            
            # This simplex creates an essential class
            dimension = self.simplex_dimensions[simplex_idx]
            birth_time = self.simplex_birth_times[simplex_idx]
            
            pair = PersistencePair(
                dimension=dimension,
                birth_index=simplex_idx,
                death_index=None,
                birth_time=birth_time,
                death_time=None,
                persistence=None
            )
            
            infinite_pairs.append(pair)
        
        # Step 4: Combine and sort
        all_pairs = finite_pairs + infinite_pairs
        
        # Sort by (birth_time, dimension, birth_index) for canonical ordering
        all_pairs.sort(key=lambda p: (p.birth_time, p.dimension, p.birth_index))
        
        return all_pairs
    
    def extract_by_dimension(
        self,
        low_map: Dict[int, int]
    ) -> Dict[int, List[PersistencePair]]:
        """
        Extract pairs grouped by dimension.
        
        Useful for separate analysis of:
            - dim=0: Connected components
            - dim=1: Loops/cycles
            - dim=2: Voids/cavities
        
        Args:
            low_map: Reduced boundary matrix low map
        
        Returns:
            Dict mapping dimension → list of pairs in that dimension
        """
        all_pairs = self.extract_pairs(low_map)
        
        # Group by dimension
        by_dimension: Dict[int, List[PersistencePair]] = {}
        
        for pair in all_pairs:
            dim = pair.dimension
            if dim not in by_dimension:
                by_dimension[dim] = []
            by_dimension[dim].append(pair)
        
        return by_dimension
    
    def extract_infinite_only(
        self,
        low_map: Dict[int, int]
    ) -> List[PersistencePair]:
        """
        Extract only essential (infinite persistence) classes.
        
        These represent:
            - dim=0: Connected components that never merge
            - dim=1: Loops that never fill
            - dim=2: Voids that never close
        
        Args:
            low_map: Reduced boundary matrix low map
        
        Returns:
            List of infinite persistence pairs only
        """
        all_pairs = self.extract_pairs(low_map)
        return [p for p in all_pairs if p.is_infinite()]
    
    def extract_finite_only(
        self,
        low_map: Dict[int, int]
    ) -> List[PersistencePair]:
        """
        Extract only finite persistence features.
        
        These represent topological noise or transient features.
        
        Args:
            low_map: Reduced boundary matrix low map
        
        Returns:
            List of finite persistence pairs only
        """
        all_pairs = self.extract_pairs(low_map)
        return [p for p in all_pairs if p.is_finite()]
    
    def get_betti_numbers(
        self,
        low_map: Dict[int, int],
        at_time: int
    ) -> Dict[int, int]:
        """
        Compute Betti numbers at specific filtration time.
        
        Betti number β_k(t) = number of k-dimensional features alive at time t
        
        A feature is alive at time t if:
            - birth_time <= t
            - death_time > t (or death_time = None)
        
        Args:
            low_map: Reduced boundary matrix low map
            at_time: Filtration time to query
        
        Returns:
            Dict mapping dimension → Betti number at that dimension
        """
        all_pairs = self.extract_pairs(low_map)
        
        # Count alive features per dimension
        betti: Dict[int, int] = {}
        
        for pair in all_pairs:
            # Check if feature is alive at at_time
            if pair.birth_time > at_time:
                continue  # Not born yet
            
            if pair.death_time is not None and pair.death_time <= at_time:
                continue  # Already dead
            
            # Feature is alive
            dim = pair.dimension
            betti[dim] = betti.get(dim, 0) + 1
        
        return betti
    
    def get_persistence_diagram(
        self,
        low_map: Dict[int, int],
        dimension: Optional[int] = None
    ) -> List[Tuple[int, Optional[int]]]:
        """
        Get persistence diagram (birth, death) points.
        
        Persistence diagram is a multiset of (birth, death) points,
        used for visualization and statistical analysis.
        
        Args:
            low_map: Reduced boundary matrix low map
            dimension: Filter by specific dimension (None = all dimensions)
        
        Returns:
            List of (birth_time, death_time) tuples
            death_time = None for infinite bars
        """
        all_pairs = self.extract_pairs(low_map)
        
        # Filter by dimension if requested
        if dimension is not None:
            all_pairs = [p for p in all_pairs if p.dimension == dimension]
        
        # Extract (birth, death) points
        diagram = [(p.birth_time, p.death_time) for p in all_pairs]
        
        return diagram


def validate_persistence_pairs(
    pairs: List[PersistencePair],
    total_simplices: int
) -> bool:
    """
    Validate persistence pair list for consistency.
    
    Checks:
        1. All birth indices in valid range
        2. All death indices > birth indices
        3. All death times > birth times
        4. No duplicate births (each simplex births at most once)
    
    Args:
        pairs: List of persistence pairs to validate
        total_simplices: Total number of simplices in filtration
    
    Returns:
        True if valid, raises ValueError otherwise
    
    Raises:
        ValueError: If any invariant is violated
    """
    seen_births: Set[int] = set()
    
    for pair in pairs:
        # Check birth index range
        if pair.birth_index < 0 or pair.birth_index >= total_simplices:
            raise ValueError(
                f"Birth index {pair.birth_index} out of range [0, {total_simplices})"
            )
        
        # Check for duplicate births (for ALL pairs, not just finite)
        if pair.birth_index in seen_births:
            raise ValueError(
                f"Duplicate birth: simplex {pair.birth_index} births multiple times"
            )
        seen_births.add(pair.birth_index)
        
        # Check death index (if finite)
        if pair.death_index is not None:
            if pair.death_index < 0 or pair.death_index >= total_simplices:
                raise ValueError(
                    f"Death index {pair.death_index} out of range [0, {total_simplices})"
                )
            
            if pair.death_index <= pair.birth_index:
                raise ValueError(
                    f"Death index {pair.death_index} <= birth index {pair.birth_index}"
                )
        
        # Check times (if finite)
        if pair.death_time is not None:
            if pair.death_time <= pair.birth_time:
                raise ValueError(
                    f"Death time {pair.death_time} <= birth time {pair.birth_time}"
                )
            
            if pair.persistence != pair.death_time - pair.birth_time:
                raise ValueError(
                    f"Persistence mismatch: stored={pair.persistence}, "
                    f"computed={pair.death_time - pair.birth_time}"
                )
        
        # Check infinite consistency
        if pair.is_infinite():
            if pair.death_index is not None:
                raise ValueError("Infinite pair has non-None death_index")
            if pair.death_time is not None:
                raise ValueError("Infinite pair has non-None death_time")
            if pair.persistence is not None:
                raise ValueError("Infinite pair has non-None persistence")
    
    return True
