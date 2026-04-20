API Reference
=============

VeriLogos follows a strict 5-layer architecture. Each layer builds upon the previous one with no upward dependencies.

.. toctree::
   :maxdepth: 2

   layer0_topology
   layer1_sclogic
   layer2_temporal
   layer3_persistence
   layer4_application

Architecture Overview
---------------------

**Layer 0: Topology Foundation**
    Core simplicial complex data structures and boundary operators.

**Layer 1: SC-Logic Operations**
    Modal logic operations on simplicial complexes (conjunction, disjunction, negation, etc.).

**Layer 2: Temporal Semantics**
    Time-indexed filtrations and temporal valuations.

**Layer 3: Persistence Engine**
    Persistent homology computation and barcode generation.

**Layer 4: Application Layer**
    Market monitoring engines and real-time analysis.
