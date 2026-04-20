"""
Integration tests for VeriLogos public API facade.

This test suite verifies that all public APIs are correctly exposed through
the unified verilogos.core namespace and that no internal modules leak through.
"""

import pytest


class TestPublicAPIImports:
    """Test that all public APIs are importable from verilogos.core"""
    
    def test_wildcard_import_works(self):
        """Wildcard import should work without errors"""
        # This should not raise any exceptions
        exec("from verilogos.core import *")
    
    def test_layer0_topology_imports(self):
        """Layer 0 (Topology) classes should be importable"""
        from verilogos.core import (
            SimplicialComplex,
            Subcomplex,
            ChainComplex,
            Filtration,
            TemporalValuation,
            TemporalState,
            PersistentHomology,
            PersistenceInterval,
            Barcode,
        )
        
        # Verify they are actual classes/types
        assert SimplicialComplex is not None
        assert Filtration is not None
        assert PersistentHomology is not None
        assert PersistenceInterval is not None
    
    def test_layer1_sclogic_imports(self):
        """Layer 1 (SC-Logic) classes should be importable"""
        from verilogos.core import SCLogicOperations
        
        assert SCLogicOperations is not None
    
    def test_layer3_modal_imports(self):
        """Layer 3 (Modal Semantics) classes should be importable"""
        from verilogos.core import (
            ModalStatus,
            EntailmentResult,
            PersistenceEntailmentEvaluator,
        )
        
        assert ModalStatus is not None
        assert EntailmentResult is not None
        assert PersistenceEntailmentEvaluator is not None
    
    def test_layer3_persistence_imports(self):
        """Layer 3 (Persistence Engine) classes should be importable"""
        from verilogos.core import PersistenceEngine, ReasoningAPI
        
        assert PersistenceEngine is not None
        assert ReasoningAPI is not None


class TestLayerSpecificImports:
    """Test that layer-specific imports also work"""
    
    def test_topology_layer_import(self):
        """Should be able to import from verilogos.core.topology"""
        from verilogos.core.topology import SimplicialComplex, Filtration
        
        assert SimplicialComplex is not None
        assert Filtration is not None
    
    def test_logic_layer_import(self):
        """Should be able to import from verilogos.core.logic"""
        from verilogos.core.logic import ModalStatus, PersistenceEntailmentEvaluator
        
        assert ModalStatus is not None
        assert PersistenceEntailmentEvaluator is not None
    
    def test_operators_layer_import(self):
        """Should be able to import from verilogos.core.operators"""
        from verilogos.core.operators import SCLogicOperations
        
        assert SCLogicOperations is not None
    
    def test_reasoning_layer_import(self):
        """Should be able to import from verilogos.core.reasoning"""
        from verilogos.core.reasoning import PersistenceEngine
        
        assert PersistenceEngine is not None


class TestAPIConsistency:
    """Test that imports from different paths refer to the same objects"""
    
    def test_simplicial_complex_consistency(self):
        """SimplicialComplex from core and topology should be identical"""
        from verilogos.core import SimplicialComplex as SC1
        from verilogos.core.topology import SimplicialComplex as SC2
        
        assert SC1 is SC2
    
    def test_modal_status_consistency(self):
        """ModalStatus from core and logic should be identical"""
        from verilogos.core import ModalStatus as MS1
        from verilogos.core.logic import ModalStatus as MS2
        
        assert MS1 is MS2
    
    def test_persistence_engine_consistency(self):
        """PersistenceEngine from core and reasoning should be identical"""
        from verilogos.core import PersistenceEngine as PE1
        from verilogos.core.reasoning import PersistenceEngine as PE2
        
        assert PE1 is PE2


class TestNoInternalLeaks:
    """Test that internal modules are not exposed"""
    
    def test_no_private_modules_in_all(self):
        """__all__ should not contain private modules"""
        from verilogos import core
        
        if hasattr(core, '__all__'):
            for name in core.__all__:
                assert not name.startswith('_'), f"Private name {name} in __all__"
    
    def test_no_internal_submodules_exposed(self):
        """Internal submodules should not be directly accessible"""
        from verilogos import core
        
        # These should not be in __all__
        if hasattr(core, '__all__'):
            assert 'complexes' not in core.__all__
            assert 'simplices' not in core.__all__
            assert 'boundary' not in core.__all__
            assert 'persistence' not in core.__all__


class TestBasicFunctionality:
    """Test that imported classes actually work"""
    
    def test_create_simplicial_complex(self):
        """Should be able to create and use SimplicialComplex"""
        from verilogos.core import SimplicialComplex
        
        K = SimplicialComplex()
        K.add_simplex((0, 1))
        K.add_simplex((1, 2))
        
        assert (0, 1) in K
        assert (1, 2) in K
    
    def test_create_filtration(self):
        """Should be able to create and use Filtration"""
        from verilogos.core import Filtration
        
        filt = Filtration()
        filt.add_level(0, [(0, 1)])
        filt.add_level(1, [(1, 2)])
        
        assert filt.n >= 1  # At least 2 levels (0 and 1)
    
    def test_modal_status_enum(self):
        """Should be able to use ModalStatus enum"""
        from verilogos.core import ModalStatus
        
        assert hasattr(ModalStatus, 'ESSENTIAL')
        assert hasattr(ModalStatus, 'EXPLICIT')
        assert hasattr(ModalStatus, 'EMERGENT')
        assert ModalStatus.ESSENTIAL.value == "essential"
    
    def test_persistence_entailment_evaluator(self):
        """Should be able to create and use PersistenceEntailmentEvaluator"""
        from verilogos.core import PersistenceEntailmentEvaluator, ModalStatus
        
        evaluator = PersistenceEntailmentEvaluator()
        
        # Test basic entailment
        p_intervals = [(0.0, 5.0)]
        q_intervals = [(0.0, None)]  # Permanent
        
        result = evaluator.evaluate_result(p_intervals, q_intervals)
        
        assert result.status == ModalStatus.ESSENTIAL
        assert result.confidence == 1.0
        assert result.necessary is True


class TestVersionInfo:
    """Test that version information is available"""
    
    def test_version_exists(self):
        """Module should have version info"""
        from verilogos import core
        
        assert hasattr(core, '__version__')
        assert isinstance(core.__version__, str)
    
    def test_author_exists(self):
        """Module should have author info"""
        from verilogos import core
        
        assert hasattr(core, '__author__')
        assert isinstance(core.__author__, str)


class TestDocstrings:
    """Test that public API has proper documentation"""
    
    def test_core_module_has_docstring(self):
        """Core module should have a docstring"""
        from verilogos import core
        
        assert core.__doc__ is not None
        assert len(core.__doc__) > 100
        assert "VeriLogos Core" in core.__doc__
    
    def test_topology_module_has_docstring(self):
        """Topology module should have a docstring"""
        from verilogos.core import topology
        
        assert topology.__doc__ is not None
        assert "Layer 0" in topology.__doc__
    
    def test_logic_module_has_docstring(self):
        """Logic module should have a docstring"""
        from verilogos.core import logic
        
        assert logic.__doc__ is not None
        assert "Modal" in logic.__doc__ or "Logic" in logic.__doc__
    
    def test_operators_module_has_docstring(self):
        """Operators module should have a docstring"""
        from verilogos.core import operators
        
        assert operators.__doc__ is not None
        assert "SC-Logic" in operators.__doc__ or "FROZEN" in operators.__doc__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
