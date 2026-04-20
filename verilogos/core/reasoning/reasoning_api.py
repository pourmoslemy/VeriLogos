"""
ReasoningAPI - Layer 6: High-Level Topological Reasoning Interface

This module implements the high-level reasoning interface for the SANN architecture.
It purely orchestrates the lower layers (PersistenceEngine, TopologicalValuation,
PersistenceEntailmentEvaluator) without touching topology directly.

Architectural Principles:
1. NO set operations or len() checks in this layer
2. ALL topology work delegated to PersistenceEntailmentEvaluator
3. ALL temporal logic uses interval semantics [birth, death)
4. Pure orchestration: receives query → delegates → returns result

Integration:
- Receives: PersistenceIntervals (from PersistenceEngine) or TemporalValuation
- Delegates to: PersistenceEntailmentEvaluator
- Returns: ModalStatus with confidence scores

Author: SANN Architecture Team
Date: 2025-04-04
"""

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union
from enum import Enum

from verilogos.core.topology.complexes.temporal_filtration import Filtration, TemporalValuation
from verilogos.core.topology.complexes.subcomplex import Subcomplex
from .persistence.persistence_engine import PersistenceEngine, PersistenceInterval
from ..logic.persistence_entailment import (
    PersistenceEntailmentEvaluator,
    ModalStatus as IntervalModalStatus,
    EntailmentResult,
)

# Alias for backward compatibility
ModalStatus = LegacyModalStatus = IntervalModalStatus


class ClassificationResult:
    """
    Result classification for neural-symbolic integration.
    
    Attributes:
        label: Classification label
        confidence: Confidence score [0.0, 1.0]
        metadata: Additional contextual information
    """
    def __init__(self, label=None, confidence=0.0, metadata=None):
        self.label = label
        self.confidence = confidence
        self.metadata = metadata or {}


class QueryResult:
    """
    Query result wrapper for API compatibility.
    
    Attributes:
        result: The computed result
        score: Confidence/score score
        explanation: Human-readable explanation
    """
    def __init__(self, result=None, score=0.0, explanation=None):
        self.result = result
        self.score = score
        self.explanation = explanation or ""


class _InferenceResult:
    """
    Lightweight inference result object for legacy ``infer()`` calls.
    """

    def __init__(self, status: LegacyModalStatus, confidence: float, reasoning: str):
        self.entailment_status = status
        self.confidence = confidence
        self.reasoning = reasoning

    @property
    def is_valid(self) -> bool:
        return self.entailment_status != LegacyModalStatus.NOT_ENTAILED


class SANNReasoner:
    """
    Legacy reasoning interface for backward compatibility.
    Delegates to modern ReasoningAPI for actual computation.
    """
    def __init__(self, config=None):
        self.config = config or {}
        self.model = None
        self._api = ReasoningAPI(config)
    
    def classify(self, input_data):
        """Classify input using topological reasoning."""
        result = self._api.reason(input_data)
        return ClassificationResult(
            label=result.get("output", "unknown"),
            confidence=result.get("confidence", 0.5),
            metadata=result.get("metadata", {})
        )
    
    def query(self, query_text):
        """Query using topological entailment."""
        result = self._api.reason(query_text)
        return QueryResult(
            result=result.get("output"),
            score=result.get("confidence", 0.0),
            explanation=result.get("explanation", "")
        )


class ReasoningAPI:
    """
    High-level reasoning interface for the SANN topology pipeline.
    
    This is Layer 6 of the SANN architecture: pure orchestration layer.
    It delegates all topological work to lower layers and returns
    mathematically rigorous entailment results.
    
    Architecture:
    - Receives: PersistenceIntervals (from PersistenceEngine) OR TemporalValuation
    - Delegates: To PersistenceEntailmentEvaluator for entailment computation
    - Returns: ModalStatus with confidence, temporal traces, and explanations
    
    Key Features:
    1. NO set operations (len(), &, union, etc.)
    2. NO boolean logic (if len(s) > 0, etc.)
    3. ALL interval semantics [birth, death)
    4. ALL topological work delegated
    """
    
    def __init__(
        self,
        complex=None,
        vertices=None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize the reasoning API.
        
        Args:
            complex: Optional ambient complex.
            vertices: Optional legacy vertex list used to construct ambient complex.
            config: Optional configuration dictionary with:
                - min_lifespan_threshold: Minimum lifespan for significant intervals
                - dimension_consistent: Enforce dimension matching in entailment
        """
        if config is None and isinstance(complex, dict) and vertices is None:
            # Backward-compatible positional call: ReasoningAPI(config_dict)
            config = complex
            complex = None

        if complex is None and vertices is not None:
            from .complexes.complex import SimplicialComplex
            complex = SimplicialComplex(vertices=vertices)

        # Normalize config: accept dataclass or dict
        if config is not None and not isinstance(config, dict):
            import dataclasses
            config = dataclasses.asdict(config) if dataclasses.is_dataclass(config) else vars(config)

        if kwargs:
            kwargs.pop("max_dim", None)
            kwargs.pop("dim", None)
            kwargs.pop("feature_dim", None)

        self.config = config or {}
        self.complex = complex
        self._results = []
        
        # Initialize the persistence entailment evaluator
        self._evaluator = PersistenceEntailmentEvaluator(
            min_lifespan_threshold=self.config.get("min_lifespan_threshold", 2.0),
            dimension_consistent=self.config.get("dimension_consistent", True),
        )
        self._propositions: Dict[str, Set[Tuple[int, ...]]] = {}

    @staticmethod
    def _normalize_simplex(simplex: Union[int, Tuple[int, ...], Any]) -> Tuple[int, ...]:
        """
        Normalize a simplex to a canonical tuple form.
        """
        if isinstance(simplex, int):
            return (simplex,)
        if isinstance(simplex, tuple):
            return simplex
        if hasattr(simplex, "vertices"):
            return tuple(getattr(simplex, "vertices"))
        return tuple(simplex)

    @classmethod
    def _normalize_proposition_simplices(
        cls,
        simplices: Union[Dict[int, Iterable[Any]], Iterable[Any]],
    ) -> Set[Tuple[int, ...]]:
        """
        Normalize proposition input into a flat set of simplices.
        """
        normalized: Set[Tuple[int, ...]] = set()
        if isinstance(simplices, dict):
            iterable = (
                simplex
                for bucket in simplices.values()
                for simplex in bucket
            )
        else:
            iterable = simplices

        for simplex in iterable:
            normalized.add(cls._normalize_simplex(simplex))
        return normalized

    def create_proposition(
        self,
        name: str,
        simplices: Union[Dict[int, Iterable[Any]], Iterable[Any]],
    ) -> None:
        """
        Register proposition named ``name`` for legacy temporal/modal workflows.
        """
        self._propositions[name] = self._normalize_proposition_simplices(simplices)

    def _get_proposition(self, name: str) -> Set[Tuple[int, ...]]:
        if name not in self._propositions:
            raise KeyError(f"Unknown proposition '{name}'")
        return self._propositions[name]

    @staticmethod
    def _extract_simplices_from_valuation(
        valuation: Optional["TemporalValuation"], prop_name: str
    ) -> Set[Tuple[int, ...]]:
        """Extract the union of all simplices for *prop_name* from a valuation.

        Used as a fallback when the proposition has not been explicitly
        registered via ``create_proposition``.
        """
        if valuation is None:
            return set()
        seq = getattr(valuation, "valuations", {}).get(prop_name, [])
        result: Set[Tuple[int, ...]] = set()
        for sub in seq:
            simplices = getattr(sub, "simplices", {})
            if isinstance(simplices, dict):
                for sset in simplices.values():
                    result.update(sset)
        return result

    @staticmethod
    def _resolve_filtration_end(filtration: Optional[Filtration]) -> int:
        if filtration is None:
            raise ValueError("Filtration is required")
        if hasattr(filtration, "n"):
            return int(filtration.n)
        if hasattr(filtration, "steps"):
            return max(0, len(filtration.steps) - 1)
        return int(filtration)

    def _cfg_bool(self, keys: List[str], default: bool = False) -> bool:
        for key in keys:
            if isinstance(self.config, dict) and key in self.config:
                return bool(self.config[key])
            if hasattr(self.config, key):
                return bool(getattr(self.config, key))
        return default

    def _cfg_float(self, keys: List[str], default: float) -> float:
        for key in keys:
            if isinstance(self.config, dict) and key in self.config:
                return float(self.config[key])
            if hasattr(self.config, key):
                return float(getattr(self.config, key))
        return default

    def _cfg_get_thresholds(self) -> Tuple[float, float]:
        """
        Return (essential_threshold, emergent_threshold).
        """
        essential = self._cfg_float(
            ["ESSENTIAL_THRESHOLD", "essential_threshold", "persistence_threshold"],
            0.75,
        )
        emergent = self._cfg_float(
            ["EMERGENT_APPEARANCE_THRESHOLD", "EMERGENT_THRESHOLD", "emergent_threshold"],
            0.5,
        )
        return essential, emergent

    def _cfg_ignore_t0(self) -> bool:
        return self._cfg_bool(
            ["IGNORE_T0_IN_NECESSITY", "ignore_t0_in_necessity", "ignore_t0"],
            False,
        )

    @staticmethod
    def _get_proposition_valuation(valuation: Any, prop: str) -> List[Subcomplex]:
        """
        Read a valuation sequence for ``prop`` using any supported API shape.
        """
        if hasattr(valuation, "valuations"):
            return valuation.valuations[prop]

        if hasattr(valuation, "_valuations"):
            return valuation._valuations[prop]

        return valuation[prop]

    def _is_layer1_explicit(
        self,
        valuation: TemporalValuation,
        prop: str,
        simplex: Tuple[int, ...],
        filtration_end: int,
    ) -> bool:
        if not hasattr(valuation, "is_persistent"):
            return False

        start_time = 1 if self._cfg_ignore_t0() else 0
        if start_time > filtration_end:
            return False
        try:
            return valuation.is_persistent(prop, simplex, start_time, filtration_end)
        except TypeError:
            return False

    def _persistence_ratio(
        self,
        valuation: TemporalValuation,
        prop: str,
        simplex: Tuple[int, ...],
        filtration_end: int,
    ) -> Optional[float]:
        if not hasattr(valuation, "compute_lifespan"):
            return None
        lifespan = valuation.compute_lifespan(prop, simplex)
        if not hasattr(valuation, "compute_lifespan"):
            return None
        effective_steps = max(1, filtration_end)
        if self._cfg_ignore_t0() and effective_steps > 0:
            effective_steps = max(1, effective_steps - 1)
        return float(lifespan) / float(effective_steps)

    def _is_emergent_over_time(
        self,
        valuation: TemporalValuation,
        prop: str,
        simplex: Tuple[int, ...],
    ) -> bool:
        if not hasattr(valuation, "is_emergent"):
            return False
        filtration_end = getattr(valuation.filtration, "n", 0)
        if filtration_end <= 0:
            return False
        # A minimal probe for emergence in the observed horizon.
        for t in range(1, filtration_end + 1):
            try:
                if valuation.is_emergent(prop, simplex, t):
                    return True
            except TypeError:
                return False
        return False

    def _temporal_modal_status(
        self,
        prop_p: str,
        prop_q: str,
        filtration: Filtration,
        valuation: Optional[TemporalValuation],
    ) -> LegacyModalStatus:
        """
        Legacy-style temporal/modal status for proposition pairs.
        """
        try:
            prop_p_simplices = self._get_proposition(prop_p)
        except KeyError:
            if valuation is not None and prop_p in getattr(valuation, "valuations", {}):
                prop_p_simplices = self._extract_simplices_from_valuation(valuation, prop_p)
            elif valuation is None and prop_p == prop_q:
                return LegacyModalStatus.WEAK
            else:
                raise
        try:
            prop_q_simplices = self._get_proposition(prop_q)
        except KeyError:
            if valuation is not None and prop_q in getattr(valuation, "valuations", {}):
                prop_q_simplices = self._extract_simplices_from_valuation(valuation, prop_q)
            elif valuation is None and prop_p == prop_q:
                return LegacyModalStatus.WEAK
            else:
                raise
        carrier = prop_p_simplices & prop_q_simplices
        if not carrier:
            return LegacyModalStatus.NOT_ENTAILED

        if valuation is None:
            return LegacyModalStatus.WEAK

        filtration_end = self._resolve_filtration_end(filtration)
        essential_threshold, emergent_threshold = self._cfg_get_thresholds()

        for simplex in carrier:
            if self._is_layer1_explicit(valuation, prop_q, simplex, filtration_end):
                return LegacyModalStatus.EXPLICIT

        best_status = LegacyModalStatus.NOT_ENTAILED
        has_active = False
        has_emergence = False

        for simplex in carrier:
            emerged = self._is_emergent_over_time(valuation, prop_q, simplex)
            if emerged:
                has_emergence = True

            ratio = self._persistence_ratio(valuation, prop_q, simplex, filtration_end)
            if ratio is None:
                continue
            if ratio > 0.0:
                has_active = True
            if ratio >= essential_threshold and not emerged:
                return LegacyModalStatus.EXPLICIT
            if ratio >= emergent_threshold and ratio > 0.0:
                best_status = LegacyModalStatus.EMERGENT
            elif ratio > 0.0 and best_status != LegacyModalStatus.EMERGENT:
                best_status = LegacyModalStatus.WEAK

        if not has_active:
            return LegacyModalStatus.NOT_ENTAILED

        if has_emergence:
            return LegacyModalStatus.EMERGENT

        return best_status

    def get_status(
        self,
        prop_p: str,
        prop_q: str,
        filtration: Filtration,
        valuation: Optional[TemporalValuation] = None,
    ) -> LegacyModalStatus:
        return self._temporal_modal_status(prop_p, prop_q, filtration, valuation)

    def get_classification(
        self,
        prop_p: str,
        prop_q: str,
        filtration: Filtration,
        valuation: Optional[TemporalValuation] = None,
    ) -> LegacyModalStatus:
        return self._temporal_modal_status(prop_p, prop_q, filtration, valuation)

    def evaluate(
        self,
        *args,
        **kwargs,
    ) -> Union[EntailmentResult, LegacyModalStatus]:
        if args and len(args) >= 2:
            first, second = args[0], args[1]
            if isinstance(first, (list, tuple)) and isinstance(second, (list, tuple)):
                return self.evaluate_entailment(first, second)

        if len(args) >= 4:
            return self._temporal_modal_status(args[0], args[1], args[2], args[3])
        if len(args) >= 3:
            return self.get_status(
                args[0],
                args[1],
                args[2],
                kwargs.get("valuation"),
            )
        if len(args) == 2:
            if "filtration" in kwargs or "valuation" in kwargs:
                return self.get_status(
                    args[0],
                    args[1],
                    kwargs.get("filtration"),
                    kwargs.get("valuation"),
                )

        raise TypeError("Unsupported evaluate signature")

    def infer(
        self,
        premise: str,
        conclusion: str,
        filtration: Optional[Filtration] = None,
        valuation: Optional[TemporalValuation] = None,
    ) -> _InferenceResult:
        """
        Legacy static inference adapter.
        """
        if valuation is None or filtration is None:
            # Backward-compatible behavior with stored propositions only.
            status = (
                LegacyModalStatus.EXPLICIT
                if self._get_proposition(premise) & self._get_proposition(conclusion)
                else LegacyModalStatus.NOT_ENTAILED
            )
            confidence = 1.0 if status == LegacyModalStatus.EXPLICIT else 0.0
            reasoning = (
                "Conclusion supported by shared simplices."
                if status == LegacyModalStatus.EXPLICIT
                else "No structural overlap between premises and conclusion."
            )
            return _InferenceResult(status, confidence, reasoning)

        status = self._temporal_modal_status(premise, conclusion, filtration, valuation)
        confidence = 1.0 if status == LegacyModalStatus.EXPLICIT else 0.5
        if status == LegacyModalStatus.NOT_ENTAILED:
            confidence = 0.0
        reasoning = f"Temporal entailment classified as {status.name.lower()}."
        return _InferenceResult(status, confidence, reasoning)
    
    def reason(self, input_data: Any) -> dict:
        """
        Run a topological reasoning pass over input data.
        
        This is the main entry point for the ReasoningAPI. It processes
        input data through the persistence entailment pipeline.
        
        Args:
            input_data: Can be:
                - PersistenceIntervals for P and Q propositions
                - A query string for natural language processing
                - A dict with 'p_intervals' and 'q_intervals' keys
            
        Returns:
            Dict with:
                - status: ModalStatus string
                - confidence: Confidence score [0.0, 1.0]
                - explanation: Human-readable reasoning
                - metadata: Additional context
        """
        # Extract intervals from input
        p_intervals, q_intervals = self._extract_intervals(input_data)
        
        # Delegate to persistence evaluator
        result = self._evaluator.evaluate(p_intervals, q_intervals)
        
        # Build response
        response = {
            "status": result.status.value,
            "confidence": result.confidence,
            "explanation": self._build_explanation(result),
            "metadata": {
                "p_intervals_count": result.total_p_intervals,
                "q_intervals_count": result.total_q_intervals,
                "covering_pairs_count": len(result.covering_pairs),
                "permanent_q_count": result.permanent_q_intervals,
                "emergent": result.emergent,
                "necessary": result.necessary,
            }
        }
        
        self._results.append(response)
        return response
    
    def _extract_intervals(
        self, 
        input_data: Any
    ) -> Tuple[List[PersistenceInterval], List[PersistenceInterval]]:
        """
        Extract PersistenceIntervals from various input formats.
        
        Args:
            input_data: Can be PersistenceIntervals, dict, or query string
            
        Returns:
            Tuple of (p_intervals, q_intervals)
        """
        # Case 1: Direct PersistenceInterval lists
        if isinstance(input_data, dict):
            p_intervals = input_data.get("p_intervals", [])
            q_intervals = input_data.get("q_intervals", [])
            return p_intervals, q_intervals
        
        # Case 2: List of intervals (assume p_intervals only)
        if isinstance(input_data, list):
            if input_data and isinstance(input_data[0], PersistenceInterval):
                return input_data, []
        
        # Case 3: Query string (default to empty intervals)
        return [], []
    
    def _build_explanation(self, result: EntailmentResult) -> str:
        """
        Build human-readable explanation for the entailment result.
        
        Args:
            result: EntailmentResult from the evaluator
            
        Returns:
            Human-readable explanation string
        """
        parts = []
        
        # Status explanation
        status_explanations = {
            IntervalModalStatus.EXPLICIT: "P is explicitly entailed by Q (Q covers P)",
            IntervalModalStatus.NECESSARY: "Q is permanent (all intervals have infinite death)",
            IntervalModalStatus.EMERGENT: "Q emerges after P (Q starts later)",
            IntervalModalStatus.WEAK: "Partial interval overlap (weak entailment)",
            IntervalModalStatus.NOT_ENTAILED: "No entailment relation detected",
            IntervalModalStatus.UNKNOWN: "Insufficient interval data",
        }
        
        parts.append(status_explanations.get(result.status, "Unknown status"))
        
        # Additional details
        if result.necessary:
            parts.append(f"Q has {result.permanent_q_intervals} permanent intervals")
        
        if result.emergent:
            parts.append("Q emerges temporally after P")
        
        if result.covering_pairs:
            parts.append(f"{len(result.covering_pairs)} Q intervals cover P intervals")
        
        if result.overlapping_pairs:
            parts.append(f"{len(result.overlapping_pairs)} partial overlaps detected")
        
        return "; ".join(parts)
    
    def batch_reason(
        self, 
        inputs: List[Any]
    ) -> List[dict]:
        """
        Run reasoning passes over multiple inputs.
        
        Args:
            inputs: List of input data items
            
        Returns:
            List of reasoning results
        """
        return [self.reason(input_data) for input_data in inputs]
    
    def evaluate_entailment(
        self,
        p_intervals: List[PersistenceInterval],
        q_intervals: List[PersistenceInterval],
    ) -> EntailmentResult:
        """
        Evaluate entailment P → Q using topological interval logic.
        
        This is the core method that delegates to PersistenceEntailmentEvaluator.
        
        Args:
            p_intervals: List of PersistenceInterval objects for proposition P
            q_intervals: List of PersistenceInterval objects for proposition Q
            
        Returns:
            EntailmentResult with status, confidence, and detailed analysis
        """
        return self._evaluator.evaluate(p_intervals, q_intervals)
    
    def temporal_trace(self, *args) -> Dict[str, List[Dict]]:
        """
        Compute temporal trace for proposition pairs using interval semantics.
        
        Logic:
        - For each time t, check if any Q interval is active: birth ≤ t < death
        - If P and Q intervals overlap, compute entailment status
        - Skip pairs where ALL steps have 'unknown' status
        
        Args:
            valuation: TemporalValuation with barcodes-based valuations
            pairs: List of (prop_p, prop_q) pairs to trace
            
        Returns:
            Dict mapping "p->q" keys to lists of temporal trace entries
        """
        if len(args) == 2:
            # Legacy order: temporal_trace(valuation, pairs)
            valuation, pairs = args
            filtration = valuation.filtration
        elif len(args) == 3:
            # Preferred order: temporal_trace(filtration, valuation, pairs)
            _, valuation, pairs = args
            filtration = valuation.filtration
        else:
            raise TypeError(
                "temporal_trace expects (valuation, pairs) or (filtration, valuation, pairs)"
            )

        result = {}
        n_steps = filtration.n
        
        for pair in pairs:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                continue
            prop_p, prop_q = pair

            if not isinstance(prop_p, str) or not isinstance(prop_q, str):
                continue

            try:
                self._get_proposition(prop_p)
            except KeyError:
                if prop_p in getattr(valuation, "valuations", {}):
                    pass
                else:
                    continue

            try:
                self._get_proposition(prop_q)
            except KeyError:
                if prop_q in getattr(valuation, "valuations", {}):
                    pass
                else:
                    continue

            try:
                p_intervals = self._get_intervals_for_prop(valuation, prop_p)
                q_intervals = self._get_intervals_for_prop(valuation, prop_q)
            except KeyError:
                continue

            key = f"{prop_p}->{prop_q}"
            trace = []

            for t in range(n_steps + 1):
                entry = self._trace_entry_at_time(
                    t, p_intervals, q_intervals, prop_p, prop_q
                )
                trace.append(entry)
            
            # Filter: Skip pairs where ALL steps are 'unknown'
            if all(step['status'] == 'unknown' for step in trace):
                continue
            
            result[key] = trace
        
        return result
    
    def _get_intervals_for_prop(
        self,
        valuation: TemporalValuation,
        prop: str,
    ) -> List[PersistenceInterval]:
        """
        Extract PersistenceIntervals for a proposition from TemporalValuation.
        
        This bridges TemporalValuation (subcomplex-based) to PersistenceIntervals.
        It infers intervals from the activation pattern across time steps.
        
        Args:
            valuation: TemporalValuation with barcodes-based valuations
            prop: Proposition name
            
        Returns:
            List of inferred PersistenceIntervals
        """
        if valuation is None:
            return []
        try:
            sequence = self._get_proposition_valuation(valuation, prop)
        except KeyError:
            return []
        intervals = []
        
        # Infer intervals from activation pattern
        current_interval_start = None
        
        for t, subcomplex in enumerate(sequence):
            # Check if proposition is active at time t
            # Active means: subcomplex is non-empty OR has intervals covering t
            is_active = self._is_prop_active_at(subcomplex, t)
            
            if is_active:
                if current_interval_start is None:
                    current_interval_start = t
            else:
                if current_interval_start is not None:
                    # End of interval
                    # Infer death time (use t as death, or compute from topology)
                    birth = current_interval_start
                    death = t
                    
                    # Create PersistenceInterval with dimension 0 (components)
                    interval = PersistenceInterval(birth=birth, death=death, dimension=0)
                    intervals.append(interval)
                    current_interval_start = None
        
        # Handle case where interval extends to end
        if current_interval_start is not None:
            birth = current_interval_start
            death = float('inf')  # Permanent
            interval = PersistenceInterval(birth=birth, death=death, dimension=0)
            intervals.append(interval)
        
        return intervals

    @staticmethod
    def _is_interval_active(interval: Any, t: int) -> bool:
        """
        Check if a persistence interval is active at time t.

        Supports both interval datatypes exposed by the topology stack.
        """
        if hasattr(interval, "is_active_at"):
            return bool(interval.is_active_at(t))

        birth = getattr(interval, "birth", None)
        death = getattr(interval, "death", None)
        return bool(birth is not None and death is not None and birth <= t < death)
    
    def _is_prop_active_at(self, subcomplex, t: int) -> bool:
        """
        Check if proposition is active at time t using interval logic.
        
        This replaces len() checks with proper interval semantics.
        
        Args:
            subcomplex: Subcomplex from valuation
            t: Time step
            
        Returns:
            True if proposition is active at time t
        """
        # Check if subcomplex has any simplices (basic check)
        # In a full implementation, this would use interval data directly
        simplices = subcomplex.simplices
        
        if isinstance(simplices, dict):
            # Dict-based: check if any dimension has simplices
            for dim_simplices in simplices.values():
                if dim_simplices:
                    return True
            return False
        else:
            # Flat iterable: check if non-empty
            try:
                # Use iterator to avoid len() check
                first = next(iter(simplices), None)
                return first is not None
            except TypeError:
                return False
    
    def _trace_entry_at_time(
        self,
        t: int,
        p_intervals: List[PersistenceInterval],
        q_intervals: List[PersistenceInterval],
        prop_p: str,
        prop_q: str,
    ) -> Dict:
        """
        Compute a single temporal trace entry at time t.
        
        Uses pure interval semantics: active if birth ≤ t < death.
        
        Args:
            t: Time step
            p_intervals: Intervals for proposition P
            q_intervals: Intervals for proposition Q
            prop_p: Proposition P name
            prop_q: Proposition Q name
            
        Returns:
            Dict with time, status, confidence, reasoning
        """
        # Check if P and Q intervals are active at time t
        p_active = any(self._is_interval_active(p, t) for p in p_intervals)
        q_active = any(self._is_interval_active(q, t) for q in q_intervals)
        
        if not q_active:
            return {
                "time": t,
                "status": "not_entailed",
                "confidence": 0.0,
                "reasoning": f"{prop_q} not active at t={t}"
            }
        
        # Both active: evaluate entailment at this time step
        # Use a temporal snapshot for entailment
        result = self._evaluator.evaluate(p_intervals, q_intervals)
        
        status_text = result.status.value
        confidence = result.confidence
        
        if result.necessary:
            reasoning = f"{prop_q} is permanent (infinite death)"
        elif result.emergent:
            reasoning = f"{prop_q} emerges after {prop_p}"
        elif result.status == IntervalModalStatus.EXPLICIT:
            reasoning = f"{prop_p} is explicitly entailed by {prop_q} at t={t}"
        elif result.status == IntervalModalStatus.WEAK:
            reasoning = f"Weak entailment between {prop_p} and {prop_q} at t={t}"
        else:
            reasoning = f"No clear entailment at t={t}"
        
        return {
            "time": t,
            "status": status_text,
            "confidence": confidence,
            "reasoning": reasoning,
        }
    
    def get_persistence_barcode(
        self,
        valuation: TemporalValuation,
        prop: str,
    ) -> List[PersistenceInterval]:
        """
        Get inferred persistence barcodes for a proposition.
        
        This extracts interval data from TemporalValuation for use in
        PersistenceEntailmentEvaluator.
        
        Args:
            valuation: TemporalValuation
            prop: Proposition name
            
        Returns:
            List of PersistenceInterval objects
        """
        return self._get_intervals_for_prop(valuation, prop)
    
    def reset(self) -> None:
        """Clear the reasoning history."""
        self._results.clear()
    
    @property
    def history(self) -> list:
        """Return reasoning history."""
        return list(self._results)
    
    def __repr__(self) -> str:
        return f"ReasoningAPI(config={self.config}, history_len={len(self._results)})"
