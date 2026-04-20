"""
VeriLogos Logic Layer (Layer 3 - Modal Semantics)

This module provides modal entailment evaluation based on persistence intervals,
implementing the theoretical framework from "Truth as Geometry" (Pourmoslemi, 2026).

Core Components
---------------
Modal Status:
    - ModalStatus: Enum of entailment strength levels
    - EntailmentResult: Detailed evaluation result with evidence

Entailment Evaluation:
    - PersistenceEntailmentEvaluator: Main evaluator for modal entailment

Example
-------
>>> from verilogos.core.logic import PersistenceEntailmentEvaluator, ModalStatus
>>> 
>>> # Evaluate entailment from persistence intervals
>>> evaluator = PersistenceEntailmentEvaluator()
>>> p_intervals = [(0.0, 5.0)]
>>> q_intervals = [(0.0, None)]  # Permanent feature
>>> 
>>> result = evaluator.evaluate_result(p_intervals, q_intervals)
>>> print(result.status)  # ModalStatus.ESSENTIAL
>>> print(result.confidence)  # 1.0
"""

from verilogos.core.logic.persistence_entailment import (
    ModalStatus,
    EntailmentResult,
    PersistenceEntailmentEvaluator,
)

__all__ = [
    "ModalStatus",
    "EntailmentResult",
    "PersistenceEntailmentEvaluator",
]
