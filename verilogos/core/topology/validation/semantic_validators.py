# core/topology/semantic_validators.py

from typing import Optional

from ..complexes.subcomplex import Subcomplex
from .semantic_exceptions import SemanticInvariantError


def validate_subcomplex_operation(
    result: Subcomplex,
    operation_name: str,
    left: Optional[Subcomplex] = None,
    right: Optional[Subcomplex] = None,
) -> None:
    """
    Validate semantic invariants after a logical operation.

    Args:
        result: Resulting subcomplex
        operation_name: Name of logical operation (e.g. 'intersection')
        left: Left operand
        right: Right operand

    Raises:
        SemanticInvariantError if invariant is violated
    """

    # 1. Face-closure (semantic-level check, not structural)
    if not result.is_face_closed():
        raise SemanticInvariantError(
            f"Result of '{operation_name}' is not face-closed"
        )

    # 2. Dimension monotonicity (only for intersection-like ops where result
    #    cannot exceed operand dimension)
    if left is not None:
        if operation_name in ("conjunction", "intersection") and result.max_dimension() > left.max_dimension():
            raise SemanticInvariantError(
                f"'{operation_name}' increased dimension unexpectedly"
            )

    # 3. Intersection-specific invariant
    if operation_name == "intersection" and left and right:
        if not result.is_subset_of(left) or not result.is_subset_of(right):
            raise SemanticInvariantError(
                "Intersection result is not subset of operands"
            )

    # 4. Union-specific invariant
    if operation_name == "union" and left and right:
        if not left.is_subset_of(result) or not right.is_subset_of(result):
            raise SemanticInvariantError(
                "Union result does not contain both operands"
            )
