import importlib


def _assert_module_importable(module_name: str) -> None:
    module = importlib.import_module(module_name)
    assert module is not None


def test_import_simplices_simplex():
    _assert_module_importable("verilogos.core.topology.simplices.simplex")


def test_import_simplices_k_simplex():
    _assert_module_importable("verilogos.core.topology.simplices.k_simplex")


def test_import_simplices_face():
    _assert_module_importable("verilogos.core.topology.simplices.face")


def test_import_simplices_coface():
    _assert_module_importable("verilogos.core.topology.simplices.coface")


def test_import_complexes_complex():
    _assert_module_importable("verilogos.core.topology.complexes.complex")


def test_import_complexes_subcomplex():
    _assert_module_importable("verilogos.core.topology.complexes.subcomplex")


def test_import_complexes_temporal_filtration():
    _assert_module_importable("verilogos.core.topology.complexes.temporal_filtration")


def test_import_complexes_chain_complex():
    _assert_module_importable("verilogos.core.topology.complexes.chain_complex")


def test_import_boundary_ops():
    _assert_module_importable("verilogos.core.topology.boundary.boundary_ops")


def test_import_persistent_homology():
    _assert_module_importable("verilogos.core.topology.persistence.persistent_homology")


def test_import_barcode():
    _assert_module_importable("verilogos.core.topology.persistence.barcode")


def test_import_semantic_exceptions():
    _assert_module_importable("verilogos.core.topology.validation.semantic_exceptions")


def test_import_semantic_validators():
    _assert_module_importable("verilogos.core.topology.validation.semantic_validators")


def test_import_config_phase93():
    _assert_module_importable("verilogos.core.modal.config_phase93")


def test_import_reasoning_api():
    _assert_module_importable("verilogos.core.reasoning.reasoning_api")


def test_import_sclogic_ops():
    _assert_module_importable("verilogos.core.operators.sclogic_ops")
