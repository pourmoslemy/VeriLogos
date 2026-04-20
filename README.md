VeriLogos
Topological Market Regime Detection and Verification Framework







VeriLogos is a research‑oriented Python framework for modeling structural dynamics and verification using concepts from topology, geometric logic, temporal filtrations, and persistent homology.

Rather than representing system states as simple scalar labels, VeriLogos models them as geometric structures. This enables analysis of how relationships between elements form, evolve, persist, and collapse over time.

The project was originally extracted from the broader SANN architecture and redesigned as a standalone framework with a clear layered structure.

The current application focus is topological market regime detection, though the architecture is intentionally general enough to support other structural reasoning and verification tasks.

Table of Contents
Overview
Why VeriLogos
Core Idea
Key Features
Architecture
Project Structure
Installation
Quick Start
Example Workflow
Testing
Research Motivation
Roadmap
Contributing
License
Author
Citation
Overview
Many analytical and machine learning systems represent system state as a single label or scalar value, for example:

bullish / bearish
true / false
anomaly / normal
While useful, these representations often discard the structure of relationships that produce those outcomes.

VeriLogos approaches the problem differently.

It represents system states as topological objects, allowing the system to analyze not only outcomes, but also the structural patterns that generate them.

Using this perspective, the framework enables:

structural representation of complex systems
analysis of relationships between variables
detection of persistent patterns across scales
reasoning about structural change over time
Why VeriLogos
Many real‑world systems are fundamentally relational and dynamic.

Financial markets, information systems, and complex networks evolve through interacting structures rather than isolated signals.

VeriLogos models these systems using:

Simplicial complexes for relational structure
Subcomplex relations for structural decomposition
Temporal filtrations for evolution through time
Persistent homology for identifying stable patterns
Geometric logic for reasoning about structural states
This structural perspective allows investigation of questions such as:

Which structural patterns persist across time?
Which structural changes signal regime shifts?
Which relationships remain stable under scale changes?
Core Idea
VeriLogos is based on the hypothesis that many complex systems are better modeled as geometric structures of relations rather than flat feature vectors.

Instead of asking only:

What label should be predicted?

The framework asks additional structural questions:

What geometric configuration describes the system state?
Which structures persist across scales or time?
Which transformations preserve or violate structural logic?
This viewpoint is particularly useful when:

relationships between variables are critical
systems evolve over time
structural stability matters
interpretability is important
Key Features
Topological Foundations
Simplicial complex construction
Subcomplex representation
Face‑closure validation
Dimension tracking
Set‑theoretic operations on complexes
Geometric Logic
Deterministic logical reasoning over structures
Timeless structural evaluation
Explicit separation from temporal reasoning
Entailment‑style logical outcomes
Temporal Semantics
Filtration‑based structural evolution
Time‑indexed valuation of complexes
Support for dynamic structural reasoning
Persistent Homology
Persistence computation interfaces
Betti number extraction
Barcode and interval representations
Multi‑scale topological feature detection
Application Components
Market monitoring engines
Realtime structural analysis
Backtesting utilities
Example scripts and test suite
Architecture
VeriLogos follows a layered architecture designed to keep mathematical structure, temporal reasoning, and application logic clearly separated.

text
Layer 3 — Modal Semantics
Layer 2 — Temporal Semantics
Layer 1 — Geometric Logic
Layer 0 — Topology
Layer 0 — Topology
Core mathematical structures.

Responsibilities:

simplicial complex representation
simplex normalization
face‑closure validation
dimension tracking
set operations
Constraints:

no temporal reasoning
no modal logic
no external side effects
Layer 1 — Geometric Logic
Performs logical reasoning over topological structures.

Properties:

deterministic
side‑effect free
independent of temporal context
Typical outputs include structural entailment states such as:

explicit
inferable
not_entailed
Layer 2 — Temporal Semantics
Introduces temporal evolution of structures through filtration sequences and time‑dependent evaluation.

Components include:

temporal filtration construction
structural state evolution
dynamic reasoning support
Layer 3 — Modal Semantics
High‑level reasoning and evaluation layer.

This layer coordinates:

modal reasoning
structural verification
reasoning APIs exposed to applications
Project Structure
text
VeriLogos/
│
├── docs/
├── examples/
├── scripts/
├── tests/
│
├── verilogos/
│   ├── core/
│   ├── topology/
│   ├── logic/
│   ├── persistence/
│   ├── reasoning/
│   └── application/
│
├── ARCHITECTURE.md
├── API_MAPS.md
├── pyproject.toml
├── requirements.txt
└── README.md
Installation
Clone the repository:

text
git clone https://github.com/pourmoslemy/VeriLogos.git
cd VeriLogos
Install in development mode:

text
pip install -e .
Quick Start
Run the test suite:

text
pytest tests/ -v
Example imports:

text
from verilogos.core import SimplicialComplex
from verilogos.core import Subcomplex
from verilogos.core import TemporalFiltration
from verilogos.persistence import PersistenceEngine
Example Workflow
A typical workflow in VeriLogos involves:

Constructing a simplicial complex from relational data
Building a temporal filtration describing system evolution
Computing persistent homology across scales
Extracting topological features
Applying logical reasoning to analyze structural regimes
Testing
Run all tests:

text
pytest tests/ -v
Verbose mode:

text
pytest tests/ -vv
Research Motivation
VeriLogos explores the idea that system states and logical relationships can be represented as geometric structures.

Potential research directions include:

topology‑based AI systems
geometric reasoning architectures
structural anomaly detection
topology‑driven explainable models
Roadmap
Future work may include:

topology visualization tools
persistence diagram generation
Betti curve plotting utilities
larger experimental datasets
extended structural reasoning modules
Contributing
Contributions are welcome.

Areas of interest include:

topology algorithms
structural reasoning methods
visualization tools
documentation improvements
License
MIT License

Author
Alireza Pourmoslemi

Email: apmath99@gmail.com

Citation
If you use VeriLogos in research:

text
@software{pourmoslemi_verilogos_2026,
  author = {Pourmoslemi, Alireza},
  title = {VeriLogos: Topological Market Regime Detection Framework},
  year = {2026},
  license = {MIT}
}
