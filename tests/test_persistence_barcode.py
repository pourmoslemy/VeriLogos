"""Tests for Barcode class and PersistenceEngine with real persistence."""

import pytest

from verilogos.core.topology.persistence.barcode import Barcode
from verilogos.core.reasoning.persistence.persistence_engine import (
    PersistenceEngine,
    PersistenceInterval,
)
from verilogos.core.topology.complexes.complex import SimplicialComplex


class TestBarcode:
    def test_finite_and_infinite(self):
        bc = Barcode([(0, 2), (1, 3), (2, float('inf'))])
        assert bc.finite() == [(0, 2), (1, 3)]
        assert bc.infinite() == [(2, float('inf'))]

    def test_total_persistence(self):
        bc = Barcode([(0, 2), (1, 3)])
        assert bc.total_persistence() == pytest.approx(4.0)

    def test_max_persistence(self):
        bc = Barcode([(0, 1), (0, 5), (2, 3)])
        assert bc.max_persistence() == pytest.approx(5.0)

    def test_max_persistence_empty(self):
        bc = Barcode([])
        assert bc.max_persistence() == 0.0

    def test_filter_by_persistence(self):
        bc = Barcode([(0, 0.5), (0, 3), (1, 1.2)])
        filtered = bc.filter_by_persistence(1.0)
        assert len(filtered) == 1
        assert filtered.intervals == [(0, 3)]

    def test_len(self):
        bc = Barcode([(0, 1), (2, 3)])
        assert len(bc) == 2

    def test_repr(self):
        bc = Barcode([(0, 1), (2, float('inf'))])
        assert "2 intervals" in repr(bc)
        assert "1 infinite" in repr(bc)


class TestPersistenceInterval:
    def test_finite_lifetime(self):
        iv = PersistenceInterval(dimension=1, birth=0.1, death=0.5)
        assert iv.lifetime == pytest.approx(0.4)
        assert iv.is_finite is True

    def test_infinite_lifetime(self):
        iv = PersistenceInterval(dimension=0, birth=0.0, death=None)
        assert iv.lifetime == float('inf')
        assert iv.is_finite is False


class TestPersistenceEngine:
    def _make_triangle_complex(self):
        sc = SimplicialComplex()
        sc.add_simplex([0, 1])
        sc.add_simplex([1, 2])
        sc.add_simplex([0, 2])
        return sc

    def _make_filled_triangle(self):
        sc = SimplicialComplex()
        sc.add_simplex([0, 1, 2])
        return sc

    def _make_two_components(self):
        sc = SimplicialComplex()
        sc.add_simplex([0, 1])
        sc.add_simplex([2, 3])
        return sc

    def _make_large_complex(self):
        sc = SimplicialComplex()
        for edge in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0),
                     (0, 2), (1, 3), (2, 4)]:
            sc.add_simplex(list(edge))
        sc.add_simplex([0, 1, 2])
        return sc

    def test_diagram_not_empty(self):
        engine = PersistenceEngine()
        diagram = engine.compute_diagram(self._make_triangle_complex())
        assert len(diagram) > 0

    def test_scores_are_dynamic(self):
        engine = PersistenceEngine()
        score_triangle = engine.compute_score(self._make_triangle_complex())
        score_filled = engine.compute_score(self._make_filled_triangle())
        score_two = engine.compute_score(self._make_two_components())
        scores = {score_triangle, score_filled, score_two}
        assert len(scores) > 1, (
            f"Scores must vary across complexes, got {scores}"
        )

    def test_score_not_constant_0500(self):
        engine = PersistenceEngine()
        score = engine.compute_score(self._make_large_complex())
        assert score != pytest.approx(0.05, abs=1e-6), (
            "Score should not be the old hardcoded 0.0500"
        )

    def test_filled_triangle_kills_cycle(self):
        engine = PersistenceEngine()
        diag_hollow = engine.compute_diagram(self._make_triangle_complex())
        diag_filled = engine.compute_diagram(self._make_filled_triangle())
        finite_hollow = [iv for iv in diag_hollow if iv.is_finite]
        finite_filled = [iv for iv in diag_filled if iv.is_finite]
        assert len(finite_filled) >= len(finite_hollow), (
            "Filling the triangle should produce at least as many finite pairs"
        )

    def test_barcodes_per_dimension(self):
        engine = PersistenceEngine()
        barcodes = engine.compute_barcodes(self._make_large_complex())
        assert isinstance(barcodes, dict)
        assert 0 in barcodes

    def test_barcode_total_persistence_matches_score(self):
        engine = PersistenceEngine()
        sc = self._make_large_complex()
        barcodes = engine.compute_barcodes(sc)
        diagram = engine.compute_diagram(sc)
        finite = [iv for iv in diagram if iv.is_finite]
        if finite:
            total_from_barcodes = sum(
                bc.total_persistence() for bc in barcodes.values()
            )
            total_from_diagram = sum(iv.lifetime for iv in finite)
            assert total_from_barcodes == pytest.approx(total_from_diagram, rel=1e-6)

    def test_min_persistence_filter(self):
        engine_no_filter = PersistenceEngine(min_persistence=0.0)
        engine_filtered = PersistenceEngine(min_persistence=0.5)
        sc = self._make_large_complex()
        diag_all = engine_no_filter.compute_diagram(sc)
        diag_filt = engine_filtered.compute_diagram(sc)
        finite_all = [iv for iv in diag_all if iv.is_finite]
        finite_filt = [iv for iv in diag_filt if iv.is_finite]
        assert len(finite_filt) <= len(finite_all)

    def test_entropy_is_dict(self):
        engine = PersistenceEngine()
        ent = engine.compute_entropy(self._make_large_complex())
        assert isinstance(ent, dict)
        for dim, val in ent.items():
            assert isinstance(dim, int)
            assert val >= 0.0

    def test_empty_complex(self):
        engine = PersistenceEngine()
        sc = SimplicialComplex()
        assert engine.compute_diagram(sc) == []
        assert engine.compute_score(sc) == 0.0

    def test_single_vertex(self):
        engine = PersistenceEngine()
        sc = SimplicialComplex()
        sc.add_simplex([0])
        diagram = engine.compute_diagram(sc)
        assert len(diagram) >= 1
        assert any(iv.death is None for iv in diagram)
