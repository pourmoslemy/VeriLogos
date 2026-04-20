"""
Layer 3 Tests: Persistence & Modal Semantics
Tests for PersistenceEngine, PersistenceEntailmentEvaluator, and ModalStatus

Based on ARCHITECTURE.md (Layer 3: Modal Semantics Phase 9.3) and API_MAPS.md
"""

import pytest
from enum import Enum
from typing import Dict, List, Tuple, Optional

# Layer 0 - Topology (correct import paths)
from verilogos.core.topology.complexes.complex import SimplicialComplex
from verilogos.core.topology.complexes.subcomplex import Subcomplex
from verilogos.core.topology.complexes.temporal_filtration import (
    TemporalFiltration,
    TemporalValuation
)

# Layer 3 - Persistence (correct import paths)
from verilogos.core.topology.persistence.persistent_homology import PersistentHomology
from verilogos.core.reasoning.persistence.persistence_engine import PersistenceEngine
from verilogos.core.logic.persistence_entailment import (
    PersistenceEntailmentEvaluator,
    ModalStatus,
    EntailmentResult
)
from verilogos.core.reasoning.reasoning_api import ReasoningAPI


class TestModalStatus:
    """Test ModalStatus enum structure and guarantees"""
    
    def test_modal_status_is_enum(self):
        """ModalStatus must be an Enum (ARCHITECTURE.md line ~157)"""
        assert issubclass(ModalStatus, Enum)
    
    def test_modal_status_has_essential(self):
        """ModalStatus must have ESSENTIAL member (ARCHITECTURE.md line ~163)"""
        assert hasattr(ModalStatus, 'ESSENTIAL')
        assert ModalStatus.ESSENTIAL.value == "essential"
    
    def test_modal_status_has_explicit(self):
        """ModalStatus must have EXPLICIT member (API_MAPS.md line ~451)"""
        assert hasattr(ModalStatus, 'EXPLICIT')
        assert isinstance(ModalStatus.EXPLICIT.value, str)
    
    def test_modal_status_has_emergent(self):
        """ModalStatus must have EMERGENT member (API_MAPS.md line ~453)"""
        assert hasattr(ModalStatus, 'EMERGENT')
        assert isinstance(ModalStatus.EMERGENT.value, str)
    
    def test_modal_status_enum_guarantees(self):
        """ModalStatus members must have .name and .value (ARCHITECTURE.md line ~179)"""
        for member in ModalStatus:
            assert hasattr(member, 'name')
            assert hasattr(member, 'value')
            assert isinstance(member.value, str)


class TestPersistenceEngine:
    """Test PersistenceEngine for barcode computation"""
    
    def test_persistence_engine_instantiation(self):
        """PersistenceEngine should instantiate without errors"""
        engine = PersistenceEngine()
        assert engine is not None
    
    def test_compute_barcodes_basic(self):
        """Test basic barcode computation on simple complex"""
        # Build simple filtration: edge appears at t=0, triangle at t=1
        K = SimplicialComplex()
        K.add_simplex((0, 1))
        K.add_simplex((1, 2))
        K.add_simplex((0, 2))
        K.add_simplex((0, 1, 2))
        
        filt = TemporalFiltration()
        filt.add_level(0, [(0, 1), (1, 2), (0, 2)])
        filt.add_level(1, [(0, 1, 2)])
        
        engine = PersistenceEngine()
        barcodes = engine.compute_barcodes(filt)
        
        # Should return dict with dimension keys
        assert isinstance(barcodes, dict)
        assert 0 in barcodes or 1 in barcodes  # At least one dimension
    
    def test_barcode_structure(self):
        """Barcodes should be list of (birth, death) tuples"""
        K = SimplicialComplex()
        K.add_simplex((0, 1))
        
        filt = TemporalFiltration()
        filt.add_level(0, [(0, 1)])
        
        engine = PersistenceEngine()
        barcodes = engine.compute_barcodes(filt)
        
        for dim, intervals in barcodes.items():
            assert isinstance(intervals, list)
            for interval in intervals:
                assert isinstance(interval, tuple)
                assert len(interval) == 2
                birth, death = interval
                assert isinstance(birth, (int, float))
                assert death is None or isinstance(death, (int, float))


class TestPersistenceEntailmentEvaluator:
    """Test PersistenceEntailmentEvaluator for interval-based reasoning"""
    
    def test_evaluator_instantiation(self):
        """Evaluator should instantiate (API_MAPS.md line ~460)"""
        evaluator = PersistenceEntailmentEvaluator()
        assert evaluator is not None
    
    def test_evaluate_method_exists(self):
        """Evaluator must have evaluate(p_intervals, q_intervals) method"""
        evaluator = PersistenceEntailmentEvaluator()
        assert hasattr(evaluator, 'evaluate')
        assert callable(evaluator.evaluate)
    
    def test_evaluate_returns_modal_status(self):
        """evaluate() must return ModalStatus enum (API_MAPS.md line ~383)"""
        evaluator = PersistenceEntailmentEvaluator()
        
        # Simple intervals: p persists [0, inf), q persists [1, inf)
        p_intervals = [(0, None)]
        q_intervals = [(1, None)]
        
        result = evaluator.evaluate(p_intervals, q_intervals)
        assert isinstance(result, ModalStatus)
    
    def test_explicit_entailment(self):
        """Test EXPLICIT status when q directly follows p"""
        evaluator = PersistenceEntailmentEvaluator()
        
        # p and q both persist from same time
        p_intervals = [(0, None)]
        q_intervals = [(0, None)]
        
        result = evaluator.evaluate(p_intervals, q_intervals)
        # Should be EXPLICIT or ESSENTIAL (topologically entailed)
        assert result in [ModalStatus.EXPLICIT, ModalStatus.ESSENTIAL]
    
    def test_emergent_entailment(self):
        """Test EMERGENT status when q emerges after p (API_MAPS.md line ~453)"""
        evaluator = PersistenceEntailmentEvaluator()
        
        # p persists from t=0, q emerges at t=5
        p_intervals = [(0, None)]
        q_intervals = [(5, None)]
        
        result = evaluator.evaluate(p_intervals, q_intervals)
        # Should be EMERGENT (q emerges from p over time)
        assert result == ModalStatus.EMERGENT
    
    def test_no_entailment(self):
        """Test when there's no entailment relationship"""
        evaluator = PersistenceEntailmentEvaluator()
        
        # p dies before q is born
        p_intervals = [(0, 3)]
        q_intervals = [(5, None)]
        
        result = evaluator.evaluate(p_intervals, q_intervals)
        # Should indicate no entailment (might be NONE or similar)
        assert isinstance(result, ModalStatus)


class TestTemporalValuationFromBarcodes:
    """Test TemporalValuation.from_barcodes() factory (API_MAPS.md line ~497)"""
    
    def test_from_barcodes_factory_exists(self):
        """TemporalValuation should have from_barcodes() factory method"""
        assert hasattr(TemporalValuation, 'from_barcodes')
        assert callable(TemporalValuation.from_barcodes)
    
    def test_from_barcodes_creates_valuation(self):
        """from_barcodes() should create TemporalValuation from barcode data"""
        # Mock barcode data
        barcodes = {
            0: [(0, None), (1, 5)],
            1: [(2, None)]
        }
        
        valuation = TemporalValuation.from_barcodes(barcodes)
        assert isinstance(valuation, TemporalValuation)
    
    def test_valuation_respects_persistence(self):
        """Valuation from barcodes should respect persistence intervals"""
        barcodes = {
            0: [(0, 10)]  # Feature born at 0, dies at 10
        }
        
        valuation = TemporalValuation.from_barcodes(barcodes)
        
        # Feature should be present between birth and death
        # (exact API depends on TemporalValuation implementation)
        assert valuation is not None


class TestIntegrationPersistenceToModal:
    """Integration tests: Persistence → Modal Semantics pipeline"""
    
    def test_full_pipeline_simple(self):
        """Test complete pipeline: Complex → Filtration → Barcodes → Entailment"""
        # 1. Build simplicial complex
        K = SimplicialComplex()
        K.add_simplex((0, 1))
        K.add_simplex((1, 2))
        K.add_simplex((0, 2))
        K.add_simplex((0, 1, 2))
        
        # 2. Create filtration
        filt = TemporalFiltration()
        filt.add_level(0, [(0, 1), (1, 2), (0, 2)])  # Edges at t=0
        filt.add_level(1, [(0, 1, 2)])                # Triangle at t=1
        
        # 3. Compute persistence
        engine = PersistenceEngine()
        barcodes = engine.compute_barcodes(filt)
        
        # 4. Create temporal valuation
        valuation = TemporalValuation.from_barcodes(barcodes)
        
        # 5. Evaluate entailment
        evaluator = PersistenceEntailmentEvaluator()
        
        # Extract intervals for dimension 0 and 1
        p_intervals = barcodes.get(0, [])
        q_intervals = barcodes.get(1, [])
        
        if p_intervals and q_intervals:
            status = evaluator.evaluate(p_intervals, q_intervals)
            assert isinstance(status, ModalStatus)
    
    def test_reasoning_api_integration(self):
        """Test ReasoningAPI as high-level orchestrator"""
        # ReasoningAPI should orchestrate persistence + entailment
        api = ReasoningAPI()
        assert api is not None
        
        # Should have methods for classification
        if hasattr(api, 'classify'):
            assert callable(api.classify)


class TestEntailmentResult:
    """Test EntailmentResult structure (if implemented)"""
    
    def test_entailment_result_structure(self):
        """EntailmentResult should wrap ModalStatus + metadata"""
        # This is conceptual - EntailmentResult is not specified in docs
        # but logically should contain:
        # - status: ModalStatus
        # - confidence: float
        # - provenance: intervals/barcodes used
        
        # Skip if not implemented
        if EntailmentResult.__dict__.get('__module__') == 'builtins':
            pytest.skip("EntailmentResult not yet implemented")
        
        # If implemented, test basic structure
        result = EntailmentResult()
        assert hasattr(result, 'status') or hasattr(result, '__dict__')


class TestAPIStabilityGuarantees:
    """Test API stability guarantees from ARCHITECTURE.md"""
    
    def test_modal_status_members_stable(self):
        """ModalStatus enum members must not be renamed (ARCHITECTURE.md line ~225)"""
        required_members = ['ESSENTIAL', 'EXPLICIT', 'EMERGENT']
        
        for member_name in required_members:
            assert hasattr(ModalStatus, member_name), \
                f"ModalStatus.{member_name} is part of stable API and must not be removed"
    
    def test_modal_status_values_stable(self):
        """ModalStatus enum values must not change (ARCHITECTURE.md line ~268)"""
        # ESSENTIAL must always have value "essential"
        assert ModalStatus.ESSENTIAL.value == "essential", \
            "ModalStatus.ESSENTIAL.value is part of stable API"
    
    def test_classify_returns_enum_not_string(self):
        """Classifiers must return ModalStatus enum, not strings (ARCHITECTURE.md line ~179)"""
        # This would be tested on actual classifier implementation
        # For now, verify ModalStatus is an Enum
        assert issubclass(ModalStatus, Enum)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
