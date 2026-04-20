import pytest

from verilogos.core.operators.sclogic_ops import SCLogicOperations
from verilogos.core.topology.complexes.complex import SimplicialComplex
from verilogos.core.topology.complexes.subcomplex import Subcomplex


def _ambient_complex() -> SimplicialComplex:
    complex_obj = SimplicialComplex()
    complex_obj.add_simplex((1, 2, 3))
    return complex_obj


def _subcomplex(ambient: SimplicialComplex, simplices: dict) -> Subcomplex:
    return Subcomplex(simplices=simplices, ambient=ambient)


def test_conjunction_intersection_empty_identity():
    ops = SCLogicOperations()
    ambient = _ambient_complex()
    p = _subcomplex(ambient, {0: {(1,), (2,)}, 1: {(1, 2)}})
    q = _subcomplex(ambient, {0: {(2,), (3,)}, 1: {(2, 3)}})
    full = _subcomplex(ambient, ambient.simplices)

    result = ops.conjunction(p, q)
    empty = ops.conjunction(p, _subcomplex(ambient, {}))
    identity = ops.conjunction(p, full)

    assert result.simplices == {0: {(2,)}}
    assert empty.simplices == {}
    assert identity.simplices == p.simplices


def test_disjunction_union_and_idempotence():
    ops = SCLogicOperations()
    ambient = _ambient_complex()
    p = _subcomplex(ambient, {0: {(1,)}, 1: {(1, 2)}})
    q = _subcomplex(ambient, {0: {(2,), (3,)}, 1: {(2, 3)}})

    result = ops.disjunction(p, q)
    idem = ops.disjunction(p, p)

    assert result.simplices == {0: {(1,), (2,), (3,)}, 1: {(1, 2), (2, 3)}}
    assert idem.simplices == p.simplices


def test_negation_complement_and_double_negation_identity():
    ops = SCLogicOperations()
    ambient = _ambient_complex()
    p = _subcomplex(ambient, {0: {(1,), (2,), (3,)}, 1: {(1, 2)}})

    neg_p = ops.negation(p)
    dneg_p = ops.negation(neg_p)

    for dim in set(ambient.simplices) | set(p.simplices):
        expected = ambient.simplices.get(dim, set()) - p.simplices.get(dim, set())
        assert neg_p.simplices.get(dim, set()) == expected

    assert dneg_p.simplices == p.simplices


def test_implication_equivalent_to_not_p_or_q():
    ops = SCLogicOperations()
    ambient = _ambient_complex()
    p = _subcomplex(ambient, {0: {(1,), (2,)}, 1: {(1, 2)}})
    q = _subcomplex(ambient, {0: {(2,), (3,)}, 1: {(2, 3)}})

    impl = ops.implication(p, q)
    expected = ops.disjunction(ops.negation(p), q)

    assert impl.simplices == expected.simplices


def test_necessity_true_when_all_faces_present_false_when_missing():
    ops = SCLogicOperations()
    ambient = _ambient_complex()
    all_faces = _subcomplex(ambient, {1: {(1, 2), (1, 3), (2, 3)}})
    missing_face = _subcomplex(ambient, {1: {(1, 2), (1, 3)}})

    assert ops.necessity(all_faces, (1, 2, 3)) is True
    assert ops.necessity(missing_face, (1, 2, 3)) is False


def test_possibility_true_for_sigma_or_face_membership():
    ops = SCLogicOperations()
    ambient = _ambient_complex()
    sigma_in_p = _subcomplex(ambient, {2: {(1, 2, 3)}})
    face_in_p = _subcomplex(ambient, {1: {(1, 2)}})

    assert ops.possibility(sigma_in_p, (1, 2, 3)) is True
    assert ops.possibility(face_in_p, (1, 2, 3)) is True
    assert ops.possibility(_subcomplex(ambient, {}), (1, 2, 3)) is False


def test_query_returns_all_three_labels():
    ops = SCLogicOperations()
    ambient = _ambient_complex()

    explicit = _subcomplex(ambient, {2: {(1, 2, 3)}})
    inferable = _subcomplex(ambient, {1: {(1, 2), (1, 3), (2, 3)}})
    not_entailed = _subcomplex(ambient, {1: {(1, 2)}})

    assert ops.query(explicit, (1, 2, 3)) == "explicit"
    assert ops.query(inferable, (1, 2, 3)) == "inferable"
    assert ops.query(not_entailed, (1, 2, 3)) == "not_entailed"


def test_edge_cases_empty_single_vertex_and_sigma_outside_parent():
    ops = SCLogicOperations()
    ambient = _ambient_complex()
    empty = _subcomplex(ambient, {})
    single = _subcomplex(ambient, {0: {(1,)}})

    assert ops.necessity(empty, (1,)) is False
    assert ops.possibility(single, (1,)) is True
    assert ops.query(empty, (9, 10)) == "not_entailed"


def test_negation_requires_ambient_parent():
    ops = SCLogicOperations()
    p = Subcomplex(simplices={0: {(1,)}})

    with pytest.raises(ValueError):
        ops.negation(p)


def test_necessity_all_faces_required():
    """necessity requires ALL faces present, not just membership."""
    ops = SCLogicOperations()
    ambient = _ambient_complex()

    p_complete = _subcomplex(ambient, {1: {(1, 2), (1, 3), (2, 3)}})
    assert ops.necessity(p_complete, (1, 2, 3)) is True

    p_incomplete = _subcomplex(ambient, {1: {(1, 2), (1, 3)}})
    assert ops.necessity(p_incomplete, (1, 2, 3)) is False

    p_vertex = _subcomplex(ambient, {0: {(1,)}})
    assert ops.necessity(p_vertex, (1,)) is True
    assert ops.necessity(p_vertex, (2,)) is False


def test_possibility_sigma_or_any_face():
    """possibility = sigma in p OR any face in p."""
    ops = SCLogicOperations()
    ambient = _ambient_complex()

    p1 = _subcomplex(ambient, {2: {(1, 2, 3)}})
    assert ops.possibility(p1, (1, 2, 3)) is True

    p2 = _subcomplex(ambient, {1: {(1, 2)}})
    assert ops.possibility(p2, (1, 2, 3)) is True

    p3 = _subcomplex(ambient, {0: {(1,)}})
    assert ops.possibility(p3, (1, 2, 3)) is False


def test_query_inferable_case():
    """query returns 'inferable' when necessity holds but sigma not in p."""
    ops = SCLogicOperations()
    ambient = _ambient_complex()

    p = _subcomplex(ambient, {1: {(1, 2), (1, 3), (2, 3)}})
    assert ops.query(p, (1, 2, 3)) == "inferable"
    assert ops.query(p, (1, 2)) == "explicit"

    p_incomplete = _subcomplex(ambient, {1: {(1, 2)}})
    assert ops.query(p_incomplete, (1, 2, 3)) == "not_entailed"
