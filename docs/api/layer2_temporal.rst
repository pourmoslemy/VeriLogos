Layer 2: Temporal Semantics
============================

Time-indexed filtrations and temporal valuations for tracking topological evolution.

Temporal Filtration
-------------------

.. automodule:: verilogos.core.topology.complexes.temporal_filtration
   :members:
   :undoc-members:
   :show-inheritance:

Key Concepts
------------

**Filtration**
    A nested sequence of subcomplexes: :math:`\emptyset = K_0 \subseteq K_1 \subseteq \cdots \subseteq K_n = K`

**Temporal Valuation**
    Maps propositions to time-indexed subcomplexes: :math:`V: \text{Prop} \times \mathbb{N} \to \mathcal{P}(K)`

**Emergence**
    A simplex emerges at time :math:`t` if it appears in :math:`K_t` but not in :math:`K_{t-1}`

**Persistence**
    A simplex persists from :math:`t_1` to :math:`t_2` if it exists in all :math:`K_t` for :math:`t \in [t_1, t_2]`

Temporal Operators
------------------

- ``emergence_time(prop)``: First time proposition becomes true
- ``decay_time(prop)``: First time proposition becomes false
- ``is_emergent(prop, simplex, time)``: Check if simplex emerges at time
- ``is_persistent(prop, simplex, start, end)``: Check persistence over interval
- ``compute_lifespan(prop, simplex)``: Total duration of simplex existence
