# VeriLogos

**Topological Market Regime Detection and Verification Framework**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/pourmoslemy/VeriLogos)

VeriLogos is a research‑oriented Python framework for modeling **structural dynamics and verification** using ideas from **topology**, **geometric logic**, **temporal filtrations**, and **persistent homology**.

Instead of representing system states as simple numerical labels, VeriLogos models them as **geometric structures**, enabling the study of how relationships between elements form, persist, evolve, or collapse over time.

The framework was originally extracted from the broader SANN architecture but is now a standalone, modular system focused on **structural modeling and reasoning**.  
The current applied focus is **topological market regime detection**, but the architecture is intentionally general and can be extended to other structural‑reasoning tasks.

---

## Table of Contents

- Overview
- Why VeriLogos
- Core Idea
- Key Features
- Architecture
- Project Structure
- Installation
- Quick Start
- Example Workflow
- Testing
- Research Motivation
- Roadmap
- Contributing
- License
- Author
- Citation

---

## Overview

Most analytical or machine‑learning models describe a system state using a **single scalar output**, such as:

- bullish / bearish  
- anomaly / normal  
- true / false  

Such representations discard the **structure of relationships** that underlie the system.

VeriLogos provides an alternative:  
it represents system states as **topological objects**, preserving and analyzing the relationships between components.

This perspective enables:

- representation of relational structure  
- detection of persistent patterns  
- study of structural evolution through time  
- logical reasoning over geometric states  

---

## Why VeriLogos

Many real‑world systems are **relational** and **dynamic**. Their behavior is determined not only by values but by **relationships**.

VeriLogos captures these relationships using:

- **Simplicial complexes**  
- **Subcomplex structures**  
- **Temporal filtrations**  
- **Persistent homology**  
- **Geometric logic operations**  

This allows us to analyze structural questions such as:

- Which patterns persist across time or scale?
- Which structural transitions mark regime shifts?
- Which relationships remain stable even as data changes?

---

## Core Idea

VeriLogos is based on the hypothesis that complex systems can be more effectively understood as **geometric structures of relations** rather than flat vectors.

Instead of asking:

> “What label should be predicted?”

The system investigates:

- What geometric configuration represents the current state?
- Which structures persist across scales?
- Which structural transformations preserve or violate logical properties?

This approach is useful when:

- relationships matter more than individual datapoints  
- systems evolve over time  
- interpretability and structure are valuable  

---

## Key Features

### Topological Foundations
- Construction of simplicial complexes  
- Subcomplex representation  
- Face‑closure validation  
- Dimension tracking  
- Set‑theoretic operations  

### Geometric Logic
- Logical reasoning on geometric structures  
- Timeless, deterministic evaluation  
- Entailment‑style outcomes (`explicit`, `inferable`, `not_entailed`)  

### Temporal Semantics
- Filtration sequences  
- Structural evolution over time  
- Dynamic valuation mechanisms  

### Persistent Homology
- Interfaces for persistence computation  
- Betti number extraction  
- Barcode / interval output  
- Multi‑scale feature detection  

### Application Layer
- Market monitoring utilities  
- Structural alerting  
- Backtesting tools  
- Example scripts and test suite  

---

## Architecture

VeriLogos follows a clear **layered architecture**:

```
Layer 3 — Modal Semantics
Layer 2 — Temporal Semantics
Layer 1 — Geometric Logic
Layer 0 — Topology
```

### Layer 0 — Topology
Responsible for:
- simplicial complexes  
- face‑closure  
- dimension analysis  
- set operations  

No temporal or modal reasoning happens here.

### Layer 1 — Geometric Logic
Provides:
- deterministic structural reasoning  
- timeless evaluation  
- entailment‑style logic  

### Layer 2 — Temporal Semantics
Adds:
- filtrations  
- structural evolution  
- dynamic logical evaluation  

### Layer 3 — Modal Semantics
Provides:
- higher‑level reasoning  
- structural verification APIs  
- orchestration across layers  

---

## Project Structure

```
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
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/pourmoslemy/VeriLogos.git
cd VeriLogos
```

Install in development mode:

```bash
pip install -e .
```

---

## Quick Start

Run tests to verify installation:

```bash
pytest tests/ -v
```

Basic imports:

```python
from verilogos.core import SimplicialComplex
from verilogos.core import Subcomplex
from verilogos.core import TemporalFiltration
from verilogos.persistence import PersistenceEngine
```

---

## Example Workflow

Typical workflow:

1. Build a **simplicial complex** from relational data  
2. Construct a **temporal filtration** over time  
3. Compute **persistent homology**  
4. Extract topological features  
5. Perform geometric or logical reasoning  

---

## Testing

Run the full suite:

```bash
pytest tests/ -v
```

Verbose:

```bash
pytest tests/ -vv
```

---

## Research Motivation

VeriLogos explores the idea that **truth structures and system states can be represented geometrically**.

Research directions include:

- topological AI  
- geometric logic  
- structural reasoning  
- topology‑driven explainable ML  

---

## Roadmap

Planned additions:

- visualization tools (complexes, filtrations, diagrams)  
- persistence diagrams and Betti curves  
- expanded datasets  
- structural reasoning benchmarks  

---

## Contributing

Contributions are welcome.

Possible areas:

- topology algorithms  
- reasoning engines  
- visualization  
- documentation  

---

## License

MIT License

---

## Author

**Alireza Pourmoslemi**  
Email: `apmath99@gmail.com`

---

## Citation

If you use this framework in research:

```bibtex
@software{pourmoslemi_verilogos_2026,
  author = {Pourmoslemi, Alireza},
  title = {VeriLogos: Topological Market Regime Detection Framework},
  year = {2026},
  license = {MIT}
}
