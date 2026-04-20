"""
Barcode and Persistence Diagram Utilities

Phase 9.1 Implementation
========================
Tools for working with persistence diagrams and barcodes.

Features:
- Barcode representation and filtering
- Finite/infinite interval separation
- Persistence statistics

Version: 9.1
"""

from typing import List, Optional, Tuple


class Barcode:
    """
    Barcode representation of persistence intervals.
    
    A barcode is a collection of intervals [birth, death) representing
    the lifespan of topological features.
    
    Attributes:
        intervals: List of (birth, death) pairs
                  death can be float('inf') for infinite features
    
    Example:
        >>> intervals = [(0, 2), (1, 3), (2, float('inf'))]
        >>> bc = Barcode(intervals)
        >>> print(bc.finite())
        [(0, 2), (1, 3)]
        >>> print(bc.infinite())
        [(2, inf)]
    """
    
    def __init__(self, intervals: List[Tuple[float, float]]):
        """
        Initialize barcode from intervals.
        
        Args:
            intervals: List of (birth, death) pairs
        """
        self.intervals = intervals
    
    def finite(self) -> List[Tuple[float, float]]:
        """
        Get finite intervals only.
        
        Returns:
            List of (birth, death) where death != ∞
        """
        return [(b, d) for b, d in self.intervals if d != float('inf')]
    
    def infinite(self) -> List[Tuple[float, float]]:
        """
        Get infinite intervals only.
        
        Returns:
            List of (birth, ∞) pairs
        """
        return [(b, d) for b, d in self.intervals if d == float('inf')]
    
    def persistence(self, interval: Tuple[float, float]) -> float:
        """
        Compute persistence (lifespan) of an interval.
        
        Args:
            interval: (birth, death) pair
        
        Returns:
            death - birth (∞ if infinite)
        """
        birth, death = interval
        return death - birth
    
    def total_persistence(self) -> float:
        """
        Sum of all finite persistence values.
        
        Returns:
            Σ (death - birth) for finite intervals
        """
        return sum(self.persistence(i) for i in self.finite())
    
    def max_persistence(self) -> float:
        """
        Maximum persistence among finite intervals.
        
        Returns:
            max(death - birth) or 0 if no finite intervals
        """
        finite_ints = self.finite()
        if not finite_ints:
            return 0.0
        
        return max(self.persistence(i) for i in finite_ints)
    
    import math

    def filter_by_persistence(self, min_persistence: float) -> 'Barcode':
        """Filter intervals by minimum persistence."""
        filtered = [
            interval for interval in self.intervals
            if interval[1] != float('inf') and  # ← این خط را اضافه کن
            self.persistence(interval) >= min_persistence
        ]
        return Barcode(filtered)
    
    def __len__(self) -> int:
        """Number of intervals."""
        return len(self.intervals)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Barcode({len(self)} intervals, {len(self.infinite())} infinite)"


def compute_barcode(intervals: List[Tuple[float, float]]) -> Barcode:
    """Compatibility helper: build a Barcode from interval pairs."""
    return Barcode(intervals)


def plot_barcode(
    intervals: List[Tuple[float, float]],
    ax: Optional["object"] = None,
    title: str = "Persistence Barcode",
):
    """Compatibility helper: optionally plot barcode intervals."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return None

    created_fig = False
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))
        created_fig = True

    y = 0
    for birth, death in intervals:
        end = death if death != float("inf") else birth + 1.0
        ax.hlines(y, birth, end, linewidth=2.0)
        y += 1

    ax.set_title(title)
    ax.set_xlabel("Filtration Value")
    ax.set_ylabel("Feature Index")
    ax.grid(True, alpha=0.3, axis="x")

    if created_fig:
        plt.tight_layout()
    return ax
