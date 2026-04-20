"""
matrix_reduction.py — Phase 9.2

Column reduction algorithm for persistence computation over ℤ₂.

Mathematical Foundation
=======================
Implements standard persistence algorithm from Edelsbrunner–Harer:
    1. Process columns left-to-right (filtration order)
    2. Reduce each column by eliminating lower pivots
    3. Track low(j) = lowest non-zero row in column j

Key Properties:
    - Working in ℤ₂: addition = XOR, no signs
    - Columns represented as sorted List[int]
    - Reduction preserves filtration ordering
    - No matrix materialization (memory efficient)

Algorithm Invariant:
    After processing column j:
        low(i) = low(j) for i < j  ⟹  columns i,j are already reduced

Output Contract:
    low_map: Dict[int, int]
        - Maps column index → pivot row index
        - Only non-empty columns have entries
        - If low_map[j] = i, then column j has pivot at row i

NO Dependencies:
    ❌ torch
    ❌ numpy
    ❌ scipy
    ✅ Pure Python with sorted lists
"""

# BROKEN_IMPORT (auto-commented): from __future__ import annotations
from typing import Dict, List, Optional, Set

from .persistence_boundary import PersistenceBoundary


class MatrixReduction:
    """
    Column reduction engine for persistence computation.

    Performs standard reduction algorithm over ℤ₂ using efficient
    list operations instead of matrix multiplication.

    Attributes
    ----------
    boundary : PersistenceBoundary
        Source of boundary columns.
    low_map : Dict[int, int]
        Maps column j → pivot row i (lowest non-zero entry).
    _reduced_columns : Dict[int, List[int]]
        Cache of reduced columns {column_idx: sorted_row_indices}.
    _pivot_to_column : Dict[int, int]
        Inverse map: pivot row i → column j that has it.
    """

    def __init__(self, boundary: PersistenceBoundary):
        """
        Initialize reduction engine.

        Parameters
        ----------
        boundary : PersistenceBoundary
            Provides boundary columns in filtration order.
        """
        self.boundary = boundary

        # Primary output: low map
        self.low_map: Dict[int, int] = {}

        # Working storage
        self._reduced_columns: Dict[int, List[int]] = {}
        self._pivot_to_column: Dict[int, int] = {}

    # ------------------------------------------------------------------
    # core reduction
    # ------------------------------------------------------------------
    def reduce(self) -> Dict[int, int]:
        """
        Execute full column reduction algorithm.

        Processes all columns in filtration order (0, 1, ..., n-1),
        reducing each column by XOR with previously reduced columns
        to eliminate shared pivots.

        Returns
        -------
        Dict[int, int]
            low_map: column index → pivot row index.
            Only non-empty reduced columns have entries.

        Algorithm
        ---------
        For each column j (in order):
            1. Get boundary column from PersistenceBoundary
            2. While column is non-empty and pivot conflicts:
                a. Find column k < j with same pivot
                b. XOR column j with column k
            3. If column non-empty: record low(j) = pivot

        Complexity
        ----------
        - Time: O(n² · m) worst case, where:
            - n = number of simplices
            - m = max column length
        - Space: O(n · m) for storing reduced columns

        Examples
        --------
        >>> reducer = MatrixReduction(persistence_boundary)
        >>> low_map = reducer.reduce()
        >>> low_map[5]  # Pivot row of column 5
        3
        """
        n = len(self.boundary)

        # Clear previous results
        self.low_map.clear()
        self._reduced_columns.clear()
        self._pivot_to_column.clear()

        # Process columns in filtration order
        for j in range(n):
            # Get initial boundary column
            column = self.boundary.get_column(j).copy()

            # Reduce column until pivot is unique or column is empty
            column = self._reduce_column(column, j)

            # Store reduced column
            self._reduced_columns[j] = column

            # Record pivot if column is non-empty
            if column:
                pivot = column[-1]  # Last element = lowest row (sorted)
                self.low_map[j] = pivot
                self._pivot_to_column[pivot] = j

        return self.low_map

    def _reduce_column(self, column: List[int], j: int) -> List[int]:
        """
        Reduce a single column by eliminating pivot conflicts.

        Parameters
        ----------
        column : List[int]
            Sorted list of row indices (boundary of simplex j).
        j : int
            Column index being reduced.

        Returns
        -------
        List[int]
            Reduced column (sorted, possibly empty).

        Algorithm
        ---------
        while column is non-empty:
            pivot = column[-1]  # lowest row
            if pivot is unique:
                break
            else:
                find column k < j with low(k) = pivot
                column = column ⊕ reduced_column[k]  # XOR in ℤ₂

        Notes
        -----
        - XOR operation maintains sorted order
        - Termination guaranteed: pivots strictly decrease or column empties
        """
        while column:
            pivot = column[-1]  # Lowest row in sorted list

            # Check if this pivot already appears in an earlier column
            if pivot in self._pivot_to_column:
                # Get the earlier column with same pivot
                k = self._pivot_to_column[pivot]

                # Sanity check: k must be less than j (filtration order)
                if k >= j:
                    raise ValueError(
                        f"Reduction invariant violated: "
                        f"pivot {pivot} in column {k} >= current column {j}"
                    )

                # XOR current column with reduced column k
                other_column = self._reduced_columns[k]
                column = self._xor_columns(column, other_column)

            else:
                # Pivot is unique — reduction complete for this column
                break

        return column

    def _xor_columns(self, col1: List[int], col2: List[int]) -> List[int]:
        """
        Compute symmetric difference (XOR) of two sorted column lists.

        In ℤ₂, addition and subtraction are both XOR:
            - Elements appearing once remain
            - Elements appearing twice cancel out

        Parameters
        ----------
        col1, col2 : List[int]
            Sorted lists of row indices.

        Returns
        -------
        List[int]
            Sorted list containing symmetric difference.

        Algorithm
        ---------
        Two-pointer merge with cancellation:
            - If elements equal: skip both (cancel in ℤ₂)
            - If different: take smaller, advance that pointer

        Complexity
        ----------
        O(m₁ + m₂) where mᵢ = len(colᵢ)

        Examples
        --------
        >>> _xor_columns([1, 3, 5], [3, 5, 7])
        [1, 7]  # 3 and 5 cancel

        >>> _xor_columns([1, 2], [3, 4])
        [1, 2, 3, 4]  # No cancellation
        """
        result = []
        i, j = 0, 0

        while i < len(col1) and j < len(col2):
            if col1[i] == col2[j]:
                # Elements cancel in ℤ₂
                i += 1
                j += 1
            elif col1[i] < col2[j]:
                result.append(col1[i])
                i += 1
            else:
                result.append(col2[j])
                j += 1

        # Append remaining elements
        result.extend(col1[i:])
        result.extend(col2[j:])

        return result

    # ------------------------------------------------------------------
    # accessors
    # ------------------------------------------------------------------
    def get_reduced_column(self, j: int) -> List[int]:
        """
        Get reduced column for simplex at index j.

        Parameters
        ----------
        j : int
            Column index.

        Returns
        -------
        List[int]
            Reduced column (sorted row indices), possibly empty.

        Raises
        ------
        ValueError
            If reduction has not been run yet.
        """
        if j not in self._reduced_columns:
            raise ValueError(
                f"Column {j} not found. Run reduce() first."
            )
        return self._reduced_columns[j]

    def get_pivot(self, j: int) -> Optional[int]:
        """
        Get pivot row of column j (if non-empty).

        Parameters
        ----------
        j : int
            Column index.

        Returns
        -------
        Optional[int]
            Pivot row index, or None if column is empty.
        """
        return self.low_map.get(j)

    def is_reduced(self) -> bool:
        """
        Check if reduction has been performed.

        Returns
        -------
        bool
            True if reduce() has been called.
        """
        return len(self._reduced_columns) > 0

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------
    def validate_reduction(self) -> bool:
        """
        Verify reduction correctness invariants.

        Checks:
            1. All pivots are unique
            2. Columns are sorted
            3. Pivots respect filtration ordering

        Returns
        -------
        bool
            True if all invariants hold.

        Notes
        -----
        This is a sanity check for debugging.
        Should always return True for correct implementation.
        """
        if not self.is_reduced():
            return False

        seen_pivots: Set[int] = set()

        for j in sorted(self._reduced_columns.keys()):
            column = self._reduced_columns[j]

            # Check sorted property
            if column != sorted(column):
                return False

            # Check pivot uniqueness
            if column:
                pivot = column[-1]

                if pivot in seen_pivots:
                    return False

                seen_pivots.add(pivot)

                # Check pivot row < column index (filtration property)
                if pivot >= j:
                    return False

        return True

    # ------------------------------------------------------------------
    # introspection
    # ------------------------------------------------------------------
    def num_persistent_pairs(self) -> int:
        """
        Count number of non-trivial persistence pairs.

        Returns
        -------
        int
            Number of columns with non-empty reduction.
        """
        return len(self.low_map)

    def num_infinite_bars(self) -> int:
        """
        Count number of infinite persistence bars.

        Returns
        -------
        int
            Number of columns with empty reduction.
        """
        if not self.is_reduced():
            return 0

        total = len(self._reduced_columns)
        finite = len(self.low_map)

        return total - finite

    def get_pairing_stats(self) -> Dict[str, int]:
        """
        Get detailed statistics on persistence pairing.

        Returns
        -------
        dict
            Statistics including:
                - total_simplices
                - paired_simplices (death events)
                - unpaired_simplices (infinite bars)
                - max_column_length
                - avg_column_length
        """
        if not self.is_reduced():
            return {
                "total_simplices": 0,
                "paired_simplices": 0,
                "unpaired_simplices": 0,
                "max_column_length": 0,
                "avg_column_length": 0.0
            }

        total = len(self._reduced_columns)
        paired = len(self.low_map)
        unpaired = total - paired

        lengths = [len(col) for col in self._reduced_columns.values()]
        max_len = max(lengths) if lengths else 0
        avg_len = sum(lengths) / len(lengths) if lengths else 0.0

        return {
            "total_simplices": total,
            "paired_simplices": paired,
            "unpaired_simplices": unpaired,
            "max_column_length": max_len,
            "avg_column_length": avg_len
        }

    # ------------------------------------------------------------------
    # dunder
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        """Number of columns processed."""
        return len(self._reduced_columns)

    def __repr__(self) -> str:
        reduced = len(self._reduced_columns)
        paired = len(self.low_map)

        return (
            f"MatrixReduction("
            f"{reduced} columns, "
            f"{paired} paired, "
            f"{reduced - paired} infinite)"
        )
