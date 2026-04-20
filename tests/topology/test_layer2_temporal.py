"""
Layer-2 Tests: Temporal Semantics
=================================
Tests for Filtration, TemporalValuation, and temporal operators.

Covers:
  - Filtration construction, monotonicity validation, step access
  - TemporalValuation construction, containment validation
  - emergence_time, decay_time
  - is_emergent, is_persistent, compute_lifespan
  - Edge cases and error handling
"""

import pytest
from verilogos.core.topology.complexes.complex import SimplicialComplex
from verilogos.core.topology.complexes.subcomplex import Subcomplex
from verilogos.core.topology.complexes.temporal_filtration import (
    Filtration,
    TemporalValuation,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def triangle_complex():
    """Full triangle K = {0,1,2} with all faces."""
    K = SimplicialComplex()
    K.add_simplex((0,))
    K.add_simplex((1,))
    K.add_simplex((2,))
    K.add_simplex((0, 1))
    K.add_simplex((1, 2))
    K.add_simplex((0, 2))
    K.add_simplex((0, 1, 2))
    return K


@pytest.fixture
def filtration_3step(triangle_complex):
    """
    3-step filtration on the triangle:
      K0 = {0, 1, 2}           (vertices only, face-closed)
      K1 = {0, 1, 2, (0,1)}    (one edge added)
      K2 = full triangle        (all simplices)
    """
    K = triangle_complex

    K0 = Subcomplex(parent=K)
    K0.add_simplex((0,))
    K0.add_simplex((1,))
    K0.add_simplex((2,))

    K1 = Subcomplex(parent=K)
    K1.add_simplex((0,))
    K1.add_simplex((1,))
    K1.add_simplex((2,))
    K1.add_simplex((0, 1))

    K2 = Subcomplex(parent=K)
    K2.add_simplex((0,))
    K2.add_simplex((1,))
    K2.add_simplex((2,))
    K2.add_simplex((0, 1))
    K2.add_simplex((1, 2))
    K2.add_simplex((0, 2))
    K2.add_simplex((0, 1, 2))

    return Filtration(ambient_complex=K, steps=[K0, K1, K2])


# ── Filtration Tests ──────────────────────────────────────────────────


class TestFiltration:
    """Tests for Filtration construction and access."""

    def test_filtration_construction(self, filtration_3step):
        """Filtration builds with 3 monotonic steps."""
        f = filtration_3step
        assert len(f.steps) == 3
        assert f.n == 2  # n = len(steps) - 1

    def test_filtration_get_step(self, filtration_3step):
        """get_step returns correct subcomplex at each index."""
        f = filtration_3step
        step0 = f.get_step(0)
        step2 = f.get_step(2)
        # K0 has only vertices
        assert (0,) in step0.simplices.get(0, set())
        # K2 has the full triangle
        assert (0, 1, 2) in step2.simplices.get(2, set())

    def test_filtration_get_step_out_of_range(self, filtration_3step):
        """get_step raises IndexError for invalid index."""
        with pytest.raises(IndexError):
            filtration_3step.get_step(10)

    def test_filtration_empty(self, triangle_complex):
        """Empty filtration has n == -1."""
        f = Filtration(ambient_complex=triangle_complex, steps=[])
        assert f.n == -1

    def test_filtration_monotonicity_violation(self, triangle_complex):
        """Non-monotonic steps raise ValueError."""
        K = triangle_complex

        # K_big has an edge
        K_big = Subcomplex(parent=K)
        K_big.add_simplex((0,))
        K_big.add_simplex((1,))
        K_big.add_simplex((0, 1))

        # K_small has only vertices
        K_small = Subcomplex(parent=K)
        K_small.add_simplex((0,))
        K_small.add_simplex((1,))

        # K_big -> K_small is NOT monotonic
        with pytest.raises(ValueError, match="monotonic"):
            Filtration(ambient_complex=K, steps=[K_big, K_small])

    def test_filtration_single_step(self, triangle_complex):
        """Single-step filtration is valid, n == 0."""
        K = triangle_complex
        K0 = Subcomplex(parent=K)
        K0.add_simplex((0,))
        f = Filtration(ambient_complex=K, steps=[K0])
        assert f.n == 0
        assert f.get_step(0) is K0


# ── TemporalValuation Tests ──────────────────────────────────────────


class TestTemporalValuation:
    """Tests for TemporalValuation construction and queries."""

    def _make_valuation(self, triangle_complex, filtration_3step):
        """Helper: build a TemporalValuation with prop 'p'."""
        K = triangle_complex
        f = filtration_3step

        # V(p,0) = empty
        v0 = Subcomplex(parent=K)

        # V(p,1) = {(0,), (1,)}
        v1 = Subcomplex(parent=K)
        v1.add_simplex((0,))
        v1.add_simplex((1,))

        # V(p,2) = {(0,), (1,), (0,1)}
        v2 = Subcomplex(parent=K)
        v2.add_simplex((0,))
        v2.add_simplex((1,))
        v2.add_simplex((0, 1))

        return TemporalValuation(
            filtration=f,
            valuations={"p": [v0, v1, v2]},
        )

    def test_valuation_construction(self, triangle_complex, filtration_3step):
        """TemporalValuation builds with matching lengths."""
        tv = self._make_valuation(triangle_complex, filtration_3step)
        assert "p" in tv.valuations
        assert len(tv.valuations["p"]) == 3

    def test_get_valuation(self, triangle_complex, filtration_3step):
        """get_valuation returns correct subcomplex."""
        tv = self._make_valuation(triangle_complex, filtration_3step)
        v1 = tv.get_valuation("p", 1)
        assert (0,) in v1.simplices.get(0, set())

    def test_get_valuation_bad_prop(self, triangle_complex, filtration_3step):
        """get_valuation raises KeyError for unknown prop."""
        tv = self._make_valuation(triangle_complex, filtration_3step)
        with pytest.raises(KeyError):
            tv.get_valuation("unknown", 0)

    def test_get_valuation_bad_time(self, triangle_complex, filtration_3step):
        """get_valuation raises IndexError for out-of-range time."""
        tv = self._make_valuation(triangle_complex, filtration_3step)
        with pytest.raises(IndexError):
            tv.get_valuation("p", 99)

    def test_length_mismatch_raises(self, triangle_complex, filtration_3step):
        """Valuation length != filtration steps raises ValueError."""
        K = triangle_complex
        v0 = Subcomplex(parent=K)
        # Only 1 step but filtration has 3
        with pytest.raises(ValueError, match="length"):
            TemporalValuation(
                filtration=filtration_3step,
                valuations={"p": [v0]},
            )

    def test_containment_violation_raises(self, triangle_complex, filtration_3step):
        """V(p,t) ⊄ K_t raises ValueError."""
        K = triangle_complex

        # V(p,0) contains edge (0,1) but K0 only has vertices
        v0_bad = Subcomplex(parent=K)
        v0_bad.add_simplex((0,))
        v0_bad.add_simplex((1,))
        v0_bad.add_simplex((0, 1))  # NOT in K0

        v1 = Subcomplex(parent=K)
        v2 = Subcomplex(parent=K)

        with pytest.raises(ValueError, match="contained"):
            TemporalValuation(
                filtration=filtration_3step,
                valuations={"p": [v0_bad, v1, v2]},
            )


# ── Temporal Operators Tests ──────────────────────────────────────────


class TestTemporalOperators:
    """Tests for emergence, decay, persistence, lifespan."""

    @pytest.fixture
    def tv_with_lifecycle(self, triangle_complex, filtration_3step):
        """
        Valuation with lifecycle:
          V(p,0) = empty
          V(p,1) = {(0,), (1,)}
          V(p,2) = {(0,), (1,), (0,1)}

          V(q,0) = {(0,)}
          V(q,1) = {(0,)}
          V(q,2) = empty  (decay)
        """
        K = triangle_complex
        f = filtration_3step

        # prop p: grows over time
        vp0 = Subcomplex(parent=K)
        vp1 = Subcomplex(parent=K)
        vp1.add_simplex((0,))
        vp1.add_simplex((1,))
        vp2 = Subcomplex(parent=K)
        vp2.add_simplex((0,))
        vp2.add_simplex((1,))
        vp2.add_simplex((0, 1))

        # prop q: present then decays
        vq0 = Subcomplex(parent=K)
        vq0.add_simplex((0,))
        vq1 = Subcomplex(parent=K)
        vq1.add_simplex((0,))
        vq2 = Subcomplex(parent=K)  # empty = decay

        return TemporalValuation(
            filtration=f,
            valuations={
                "p": [vp0, vp1, vp2],
                "q": [vq0, vq1, vq2],
            },
        )

    # ── emergence_time ──

    def test_emergence_time_p(self, tv_with_lifecycle):
        """p emerges at t=1 (first non-empty)."""
        assert tv_with_lifecycle.emergence_time("p") == 1

    def test_emergence_time_q(self, tv_with_lifecycle):
        """q emerges at t=0."""
        assert tv_with_lifecycle.emergence_time("q") == 0

    def test_emergence_time_unknown_prop(self, tv_with_lifecycle):
        """Unknown prop returns None."""
        assert tv_with_lifecycle.emergence_time("z") is None

    # ── decay_time ──

    def test_decay_time_q(self, tv_with_lifecycle):
        """q decays at t=2 (was non-empty, becomes empty)."""
        assert tv_with_lifecycle.decay_time("q") == 2

    def test_decay_time_p_never_decays(self, tv_with_lifecycle):
        """p never decays -> None."""
        assert tv_with_lifecycle.decay_time("p") is None

    def test_decay_time_unknown_prop(self, tv_with_lifecycle):
        """Unknown prop returns None."""
        assert tv_with_lifecycle.decay_time("z") is None

    # ── is_emergent ──

    def test_is_emergent_true(self, tv_with_lifecycle):
        """(0,) emerges in p at t=1."""
        assert tv_with_lifecycle.is_emergent("p", (0,), 1) is True

    def test_is_emergent_false_already_present(self, tv_with_lifecycle):
        """(0,) in q at t=1 is NOT emergent (was in t=0 too)."""
        assert tv_with_lifecycle.is_emergent("q", (0,), 1) is False

    def test_is_emergent_at_t0_always_false(self, tv_with_lifecycle):
        """t=0 can never be emergent (no t-1)."""
        assert tv_with_lifecycle.is_emergent("q", (0,), 0) is False

    def test_is_emergent_edge_at_t2(self, tv_with_lifecycle):
        """Edge (0,1) emerges in p at t=2."""
        assert tv_with_lifecycle.is_emergent("p", (0, 1), 2) is True

    # ── is_persistent ──

    def test_is_persistent_true(self, tv_with_lifecycle):
        """(0,) persists in q from t=0 to t=1."""
        assert tv_with_lifecycle.is_persistent("q", (0,), 0, 1) is True

    def test_is_persistent_false_due_to_decay(self, tv_with_lifecycle):
        """(0,) does NOT persist in q from t=0 to t=2 (decays at t=2)."""
        assert tv_with_lifecycle.is_persistent("q", (0,), 0, 2) is False

    def test_is_persistent_single_step(self, tv_with_lifecycle):
        """Single step [t,t] is persistent if simplex present."""
        assert tv_with_lifecycle.is_persistent("p", (0,), 1, 1) is True

    def test_is_persistent_unknown_prop(self, tv_with_lifecycle):
        """Unknown prop returns False."""
        assert tv_with_lifecycle.is_persistent("z", (0,), 0, 1) is False

    # ── compute_lifespan ──

    def test_lifespan_q_vertex(self, tv_with_lifecycle):
        """(0,) in q lives for 2 steps (t=0, t=1)."""
        assert tv_with_lifecycle.compute_lifespan("q", (0,)) == 2

    def test_lifespan_p_vertex(self, tv_with_lifecycle):
        """(0,) in p lives for 2 steps (t=1, t=2)."""
        assert tv_with_lifecycle.compute_lifespan("p", (0,)) == 2

    def test_lifespan_p_edge(self, tv_with_lifecycle):
        """(0,1) in p lives for 1 step (t=2 only)."""
        assert tv_with_lifecycle.compute_lifespan("p", (0, 1)) == 1

    def test_lifespan_never_appears(self, tv_with_lifecycle):
        """Simplex that never appears has lifespan 0."""
        assert tv_with_lifecycle.compute_lifespan("p", (1, 2)) == 0


# ── Stub Import Tests ────────────────────────────────────────────────


class TestLayer2Stubs:
    """Verify persistence stubs are importable."""

    def test_import_persistence_engine(self):
        from verilogos.core.reasoning.persistence.persistence_engine import (
            PersistenceEngine,
            PersistenceInterval,
        )
        assert PersistenceEngine is not None
        assert PersistenceInterval is not None

    def test_import_persistence_entailment(self):
        from verilogos.core.logic.persistence_entailment import (
            PersistenceEntailmentEvaluator,
            ModalStatus,
            EntailmentResult,
        )
        assert PersistenceEntailmentEvaluator is not None
        assert ModalStatus is not None
        assert EntailmentResult is not None
