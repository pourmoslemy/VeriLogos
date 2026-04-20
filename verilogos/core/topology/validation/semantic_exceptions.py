# core/topology/semantic_exceptions.py

class SemanticInvariantError(RuntimeError):
    """
    Raised when a semantic invariant is violated after a logical operation.

    This error indicates that the result is structurally valid
    but semantically inconsistent with the logical theory.
    """
    pass
