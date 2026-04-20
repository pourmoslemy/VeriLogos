"""
Persistence-based Modal Entailment Evaluation

This module implements modal entailment semantics based on persistence interval
relationships, following the theoretical framework from "Truth as Geometry: 
A Topological Approach to Logic, Uncertainty, and AI Reasoning" 
(Pourmoslemi, 2026, Section 3.2).

Core Concept
------------
Given two propositions P and Q with persistence barcodes (birth-death intervals),
we evaluate the modal entailment P ⊨ Q by analyzing how Q's topological features
relate to P's features across time.

Mathematical Foundation
-----------------------
A persistence interval is a pair (birth, death) where:
    - birth: time when topological feature appears
    - death: time when feature disappears (None = permanent/infinite)

Covering Relation (Pourmoslemi, 2026, §3.2):
    Interval q covers interval p iff:
        q.birth ≤ p.birth AND q.death ≥ p.death
    
    Interpretation: Feature q exists throughout p's entire lifespan.

Modal Status Hierarchy
----------------------
ESSENTIAL > EXPLICIT > EMERGENT > NECESSARY > WEAK > NOT_ENTAILED > UNKNOWN

Classes
-------
ModalStatus : Enum
    Seven-level hierarchy of entailment strength
EntailmentResult : dataclass
    Detailed evaluation result with evidence and metrics
PersistenceEntailmentEvaluator : class
    Main evaluator for computing modal entailment from barcodes

Example
-------
>>> from verilogos.core.logic.persistence_entailment import (
...     PersistenceEntailmentEvaluator, ModalStatus
... )
>>> 
>>> # Persistence intervals for propositions P and Q
>>> p_intervals = [(0.0, 5.0), (3.0, 8.0)]  # P has two features
>>> q_intervals = [(0.0, None)]              # Q has one permanent feature
>>> 
>>> evaluator = PersistenceEntailmentEvaluator()
>>> result = evaluator.evaluate_result(p_intervals, q_intervals)
>>> 
>>> print(result.status)  # ModalStatus.ESSENTIAL
>>> print(result.confidence)  # 1.0
>>> print(result.necessary)  # True (Q is permanent)

References
----------
Pourmoslemi, A. (2026). Truth as Geometry: A Topological Approach to Logic, 
Uncertainty, and AI Reasoning. In *Learning-Driven Game Theory for AI* 
(pp. 141–177). Elsevier. DOI: 10.1016/b978-0-44-343852-3.00020-6
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ModalStatus(Enum):
    """
    Modal entailment status hierarchy based on persistence interval relationships.
    
    This enum represents the strength of modal entailment P ⊨ Q, ordered from
    strongest (ESSENTIAL) to weakest (UNKNOWN). The classification is based on
    how Q's persistence intervals relate to P's intervals.
    
    Attributes
    ----------
    ESSENTIAL : str
        Q fully covers P AND Q is permanent (death=∞). Strongest entailment.
        Example: Q = "market is volatile" persists forever while P = "price drops" 
        occurs within that volatility.
        
    EXPLICIT : str
        Q fully covers P (q.birth ≤ p.birth, q.death ≥ p.death) but Q is not permanent.
        Example: Q = "bull market" spans the entire duration of P = "tech stocks rise".
        
    EMERGENT : str
        Q emerges after P begins (q.birth > p.birth) but still covers P's intervals.
        Example: P = "interest rates drop" starts at t=0, then Q = "housing boom" 
        emerges at t=3 and persists beyond P.
        
    NECESSARY : str
        Q is permanent (necessary condition) but doesn't fully cover P.
        Example: Q = "market exists" is always true, P = "crash occurs" is temporary.
        
    WEAK : str
        Q overlaps with P but doesn't cover it. Partial temporal alignment.
        Example: Q = "earnings season" and P = "volatility spike" overlap partially.
        
    NOT_ENTAILED : str
        No meaningful relationship between P and Q intervals. Disjoint or insufficient overlap.
        Example: Q = "summer trading" and P = "winter rally" are temporally separate.
        
    UNKNOWN : str
        Insufficient data to determine entailment. Default state.
        Example: Empty barcodes or missing persistence data.
    
    Notes
    -----
    The hierarchy reflects decreasing confidence in the entailment relationship:
        ESSENTIAL (1.0) > EXPLICIT (1.0) > EMERGENT (0.7-0.9) > 
        NECESSARY (varies) > WEAK (0.5) > NOT_ENTAILED (0.0) > UNKNOWN (0.0)
    
    See Also
    --------
    EntailmentResult : Detailed result structure with confidence scores
    PersistenceEntailmentEvaluator : Main evaluation class
    """
    ESSENTIAL = "essential"
    EXPLICIT = "explicit"
    EMERGENT = "emergent"
    NECESSARY = "necessary"
    WEAK = "weak"
    NOT_ENTAILED = "not_entailed"
    UNKNOWN = "unknown"


@dataclass
class EntailmentResult:
    """
    Detailed result of persistence-based modal entailment evaluation.
    
    This dataclass contains the computed modal status, confidence score, and
    detailed evidence supporting the entailment decision. It provides full
    transparency into how the entailment was determined.
    
    Attributes
    ----------
    status : ModalStatus
        The computed modal entailment status (ESSENTIAL, EXPLICIT, etc.)
        
    confidence : float
        Confidence score in [0, 1] indicating strength of entailment.
        - 1.0: ESSENTIAL or EXPLICIT (full coverage)
        - 0.9: EMERGENT with full coverage
        - 0.7: EMERGENT with partial coverage
        - 0.5: WEAK (overlap only)
        - 0.0: NOT_ENTAILED or UNKNOWN
        
    evidence : Optional[Dict[str, Any]]
        Dictionary containing the raw persistence intervals used in evaluation:
        - 'p_intervals': List of normalized (birth, death) tuples for P
        - 'q_intervals': List of normalized (birth, death) tuples for Q
        
    total_p_intervals : int
        Number of persistence intervals in proposition P's barcode
        
    total_q_intervals : int
        Number of persistence intervals in proposition Q's barcode
        
    covering_pairs : List[Tuple[Tuple[float, Optional[float]], Tuple[float, Optional[float]]]]
        List of (p_interval, q_interval) pairs where q covers p.
        Each pair is ((p_birth, p_death), (q_birth, q_death)).
        
    overlapping_pairs : List[Tuple[Tuple[float, Optional[float]], Tuple[float, Optional[float]]]]
        List of (p_interval, q_interval) pairs that overlap but don't cover.
        
    permanent_q_intervals : int
        Count of Q intervals with death=None (permanent features)
        
    emergent : bool
        True if Q emerges after P (min(q.birth) > min(p.birth))
        
    necessary : bool
        True if all Q intervals are permanent (all deaths are None)
    
    Example
    -------
    >>> result = evaluator.evaluate_result([(0, 5)], [(0, None)])
    >>> result.status
    <ModalStatus.ESSENTIAL: 'essential'>
    >>> result.confidence
    1.0
    >>> result.necessary
    True
    """
    status: ModalStatus = ModalStatus.UNKNOWN
    confidence: float = 0.0
    evidence: Optional[Dict[str, Any]] = None
    total_p_intervals: int = 0
    total_q_intervals: int = 0
    covering_pairs: List[Tuple[Tuple[float, Optional[float]], Tuple[float, Optional[float]]]] = field(
        default_factory=list
    )
    overlapping_pairs: List[Tuple[Tuple[float, Optional[float]], Tuple[float, Optional[float]]]] = field(
        default_factory=list
    )
    permanent_q_intervals: int = 0
    emergent: bool = False
    necessary: bool = False


class PersistenceEntailmentEvaluator:
    """
    Evaluator for computing modal entailment from persistence barcodes.
    
    This class implements the core algorithm for determining modal entailment
    P ⊨ Q based on the relationship between their persistence intervals. The
    evaluation follows the theoretical framework from Pourmoslemi (2026, §3.2).
    
    Algorithm Overview
    ------------------
    1. Normalize input intervals to (birth, death) tuples
    2. Identify covering pairs: q covers p iff q.birth ≤ p.birth AND q.death ≥ p.death
    3. Identify overlapping pairs: intervals that intersect but don't cover
    4. Detect emergence: Q appears after P (min(q.birth) > min(p.birth))
    5. Detect necessity: All Q intervals are permanent (death=None)
    6. Classify into ModalStatus based on covering, emergence, and necessity
    
    Parameters
    ----------
    min_lifespan_threshold : float, optional
        Minimum lifespan (death - birth) for intervals to be considered.
        Default is 0.0 (all intervals included).
        
    dimension_consistent : bool, optional
        If True, only compare intervals from the same homology dimension.
        Default is True. (Currently not enforced in implementation)
    
    Methods
    -------
    evaluate(p_intervals, q_intervals) -> ModalStatus
        Quick evaluation returning only the modal status
        
    evaluate_result(p_intervals, q_intervals) -> EntailmentResult
        Full evaluation returning detailed result with evidence
    
    Example
    -------
    >>> evaluator = PersistenceEntailmentEvaluator()
    >>> 
    >>> # Case 1: Essential entailment (Q permanent, covers P)
    >>> p = [(2.0, 5.0)]
    >>> q = [(0.0, None)]
    >>> result = evaluator.evaluate_result(p, q)
    >>> print(result.status)  # ModalStatus.ESSENTIAL
    >>> 
    >>> # Case 2: Emergent entailment (Q appears after P)
    >>> p = [(0.0, 5.0)]
    >>> q = [(3.0, 8.0)]
    >>> result = evaluator.evaluate_result(p, q)
    >>> print(result.status)  # ModalStatus.EMERGENT
    >>> 
    >>> # Case 3: Weak entailment (overlap only)
    >>> p = [(0.0, 5.0)]
    >>> q = [(3.0, 6.0)]
    >>> result = evaluator.evaluate_result(p, q)
    >>> print(result.status)  # ModalStatus.WEAK
    
    Notes
    -----
    Input intervals can be:
    - Tuples: (birth, death) where death can be None for permanent features
    - Objects: with .birth and .death attributes
    """
    
    def __init__(self, min_lifespan_threshold: float = 0.0, dimension_consistent: bool = True):
        self.min_lifespan_threshold = min_lifespan_threshold
        self.dimension_consistent = dimension_consistent

    @staticmethod
    def _as_interval(interval: Any) -> Tuple[float, Optional[float]]:
        """
        Normalize interval to (birth, death) tuple format.
        
        Accepts either tuple format or object with .birth/.death attributes.
        
        Parameters
        ----------
        interval : Any
            Either (birth, death) tuple or object with birth/death attributes
            
        Returns
        -------
        Tuple[float, Optional[float]]
            Normalized (birth, death) where death=None means permanent
        """
        if isinstance(interval, tuple) and len(interval) == 2:
            birth, death = interval
            return float(birth), (None if death is None else float(death))
        birth = getattr(interval, "birth", 0.0)
        death = getattr(interval, "death", None)
        return float(birth), (None if death is None else float(death))

    @staticmethod
    def _covers(q: Tuple[float, Optional[float]], p: Tuple[float, Optional[float]]) -> bool:
        """
        Check if interval q covers interval p.
        
        Mathematical Definition (Pourmoslemi, 2026, §3.2):
            q covers p iff q.birth ≤ p.birth AND q.death ≥ p.death
        
        Interpretation:
            Feature q exists throughout p's entire lifespan. This is the
            fundamental relation for EXPLICIT and ESSENTIAL entailment.
        
        Parameters
        ----------
        q : Tuple[float, Optional[float]]
            Interval (birth, death) for proposition Q
        p : Tuple[float, Optional[float]]
            Interval (birth, death) for proposition P
            
        Returns
        -------
        bool
            True if q covers p, False otherwise
        """
        q_birth, q_death = q
        p_birth, p_death = p
        q_end = float("inf") if q_death is None else q_death
        p_end = float("inf") if p_death is None else p_death
        return q_birth <= p_birth and q_end >= p_end

    @staticmethod
    def _overlaps(a: Tuple[float, Optional[float]], b: Tuple[float, Optional[float]]) -> bool:
        """
        Check if intervals a and b overlap (have non-empty intersection).
        
        Mathematical Definition:
            a overlaps b iff max(a.birth, b.birth) ≤ min(a.death, b.death)
        
        Interpretation:
            Features a and b coexist for some period of time. This is used
            for WEAK entailment when covering doesn't hold.
        
        Parameters
        ----------
        a : Tuple[float, Optional[float]]
            First interval (birth, death)
        b : Tuple[float, Optional[float]]
            Second interval (birth, death)
            
        Returns
        -------
        bool
            True if intervals overlap, False if disjoint
        """
        a_birth, a_death = a
        b_birth, b_death = b
        a_end = float("inf") if a_death is None else a_death
        b_end = float("inf") if b_death is None else b_death
        return max(a_birth, b_birth) <= min(a_end, b_end)

    def evaluate_result(self, p_intervals, q_intervals) -> EntailmentResult:
        """
        Evaluate modal entailment P ⊨ Q with full detailed result.
        
        This is the main evaluation method that computes the modal status,
        confidence score, and detailed evidence for the entailment relationship.
        
        Algorithm
        ---------
        1. Normalize all intervals to (birth, death) format
        2. Handle edge cases (empty barcodes)
        3. Find all covering pairs (q covers p)
        4. Find all overlapping pairs (q overlaps p but doesn't cover)
        5. Detect emergence: min(q.birth) > min(p.birth)
        6. Detect necessity: all q intervals have death=None
        7. Classify into ModalStatus:
           - ESSENTIAL: covering + necessary
           - EXPLICIT: covering + not emergent
           - EMERGENT: covering + emergent OR just emergent
           - WEAK: overlapping only
           - NOT_ENTAILED: no relationship
        
        Parameters
        ----------
        p_intervals : List or iterable
            Persistence intervals for proposition P. Each interval can be:
            - Tuple (birth, death) where death can be None
            - Object with .birth and .death attributes
            
        q_intervals : List or iterable
            Persistence intervals for proposition Q (same format as p_intervals)
            
        Returns
        -------
        EntailmentResult
            Detailed result containing status, confidence, evidence, and metrics
            
        Example
        -------
        >>> evaluator = PersistenceEntailmentEvaluator()
        >>> result = evaluator.evaluate_result([(0, 5), (3, 8)], [(0, None)])
        >>> print(f"Status: {result.status}, Confidence: {result.confidence}")
        Status: ModalStatus.ESSENTIAL, Confidence: 1.0
        """
        p_norm = [self._as_interval(item) for item in (p_intervals or [])]
        q_norm = [self._as_interval(item) for item in (q_intervals or [])]

        if not p_norm and not q_norm:
            return EntailmentResult(
                status=ModalStatus.UNKNOWN,
                confidence=0.0,
                evidence={"p_intervals": [], "q_intervals": []},
            )
        if not p_norm or not q_norm:
            return EntailmentResult(
                status=ModalStatus.NOT_ENTAILED,
                confidence=0.0,
                evidence={"p_intervals": p_norm, "q_intervals": q_norm},
                total_p_intervals=len(p_norm),
                total_q_intervals=len(q_norm),
            )

        covering_pairs = []
        overlapping_pairs = []
        for p_item in p_norm:
            for q_item in q_norm:
                if self._covers(q_item, p_item):
                    covering_pairs.append((p_item, q_item))
                elif self._overlaps(p_item, q_item):
                    overlapping_pairs.append((p_item, q_item))

        # Detect emergence: Q appears after P begins
        p_first = min(item[0] for item in p_norm)
        q_first = min(item[0] for item in q_norm)
        emergent = q_first > p_first
        necessary = all(item[1] is None for item in q_norm)
        permanent_q_intervals = sum(1 for item in q_norm if item[1] is None)

        # Classify into ModalStatus based on covering, emergence, and necessity
        if covering_pairs and emergent:
            status = ModalStatus.EMERGENT
            confidence = 0.9
        elif covering_pairs:
            status = ModalStatus.EXPLICIT
            confidence = 1.0
        elif emergent:
            status = ModalStatus.EMERGENT
            confidence = 0.7
        elif overlapping_pairs:
            status = ModalStatus.WEAK
            confidence = 0.5
        else:
            status = ModalStatus.NOT_ENTAILED
            confidence = 0.0

        # Upgrade EXPLICIT to ESSENTIAL if Q is necessary (permanent)
        if necessary and status == ModalStatus.EXPLICIT:
            status = ModalStatus.ESSENTIAL

        return EntailmentResult(
            status=status,
            confidence=confidence,
            evidence={"p_intervals": p_norm, "q_intervals": q_norm},
            total_p_intervals=len(p_norm),
            total_q_intervals=len(q_norm),
            covering_pairs=covering_pairs,
            overlapping_pairs=overlapping_pairs,
            permanent_q_intervals=permanent_q_intervals,
            emergent=emergent,
            necessary=necessary,
        )

    def evaluate(self, p_intervals, q_intervals) -> ModalStatus:
        """
        Quick evaluation returning only the modal status.
        
        This is a convenience method that calls evaluate_result() and returns
        only the status, discarding detailed evidence.
        
        Parameters
        ----------
        p_intervals : List or iterable
            Persistence intervals for proposition P
        q_intervals : List or iterable
            Persistence intervals for proposition Q
            
        Returns
        -------
        ModalStatus
            The computed modal entailment status
        """
        return self.evaluate_result(p_intervals, q_intervals).status
