Layer 3: Persistence Engine
============================

Persistent homology computation and modal reasoning about topological features.

Persistence Engine
------------------

.. automodule:: verilogos.core.reasoning.persistence.persistence_engine
   :members:
   :undoc-members:
   :show-inheritance:

Persistence Entailment
----------------------

.. automodule:: verilogos.core.logic.persistence_entailment
   :members:
   :undoc-members:
   :show-inheritance:

Modal Status
------------

.. automodule:: verilogos.core.modal.config_phase93
   :members:
   :undoc-members:
   :show-inheritance:

Key Concepts
------------

**Persistence Interval**
    A pair :math:`(b, d)` where :math:`b` is birth time and :math:`d` is death time of a topological feature.

**Barcode**
    Visual representation of persistence intervals across dimensions.

**Modal Status**
    Classification of topological features:
    
    - ``ESSENTIAL``: Features that never die (infinite persistence)
    - ``PERSISTENT``: Long-lived features (high persistence)
    - ``TRANSIENT``: Short-lived features (low persistence)
    - ``EMERGENT``: Newly appearing features

**Persistence Score**
    Aggregate measure of topological stability: :math:`\text{score} = \frac{1}{n}\sum_{i=1}^n (d_i - b_i)`

Barcode Methods
---------------

The ``_IntervalList`` class provides utility methods for barcode analysis:

- ``finite()``: Returns list of finite intervals :math:`[(b_1, d_1), \ldots, (b_n, d_n)]`
- ``infinite()``: Returns list of infinite intervals (essential features)
- ``total_persistence()``: Sum of all finite interval lifetimes
- ``max_persistence()``: Maximum lifetime among finite intervals
