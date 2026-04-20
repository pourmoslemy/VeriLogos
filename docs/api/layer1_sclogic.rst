Layer 1: SC-Logic Operations
=============================

Modal logic operations on simplicial complexes based on "Truth as Geometry" (Definition 2.13).

SC-Logic Operators
------------------

.. automodule:: verilogos.core.operators.sclogic_ops
   :members:
   :undoc-members:
   :show-inheritance:

Mathematical Foundation
-----------------------

SC-Logic operations implement the following semantics:

**Negation**: :math:`(\neg \mu)(x) = K \setminus \mu(x)`

**Conjunction**: :math:`(\mu \wedge \nu)(x) = \mu(x) \cap \nu(x)`

**Disjunction**: :math:`(\mu \vee \nu)(x) = \mu(x) \cup \nu(x)`

**Implication**: :math:`(\mu \to \nu)(x) = (K \setminus \mu(x)) \cup \nu(x)`

**Necessity**: :math:`\Box \mu` is true at :math:`x` iff all faces of :math:`x` satisfy :math:`\mu`

**Possibility**: :math:`\Diamond \mu` is true at :math:`x` iff :math:`x` or any face satisfies :math:`\mu`

API Stability
-------------

The ``SCLogicOperations`` API is **frozen** and cannot be modified without a major version bump. All methods maintain backward compatibility guarantees.
