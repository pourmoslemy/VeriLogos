# VeriLogos

**Topological Market Regime Detection and Verification Framework**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/pourmoslemy/VeriLogos)

VeriLogos is a research-oriented Python framework for modeling structure, dynamics, and verification through **topology**, **geometric logic**, **temporal filtration**, and **persistent homology**.

Originally migrated from the broader **SANN** architecture, VeriLogos provides a clean, layered foundation for building systems that reason about complex structures as **geometric objects** rather than flat labels or isolated signals.

It is currently focused on **topological market regime detection**, with an architecture extensible to broader verification and reasoning tasks.

---

## 📋 Table of Contents

- [Why VeriLogos?](#why-verilogos)
- [Core Idea](#core-idea)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Example Workflows](#example-workflows)
- [Testing](#testing)
- [Current Scope](#current-scope)
- [Research Motivation](#research-motivation)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)
- [Citation](#citation)

---

## Why VeriLogos?

Most analytical systems treat truth, risk, or market state as a **scalar output**:
- bullish / bearish
- true / false
- anomaly / normal

VeriLogos takes a different approach.

It treats structure as something that can be represented by:
- **simplicial complexes**
- **subcomplex relations**
- **filtrations over time**
- **persistent topological features**
- **logical operations over geometry**

This makes it possible to study not only *what* a system predicts, but also **how structure forms, persists, transforms, and collapses**.

In practical terms, this supports:
- structural market regime detection
- interpretable topology-driven alerts
- topological backtesting
- geometry-based reasoning pipelines
- future extensions toward misinformation detection and truth-structure modeling

---

## Core Idea

VeriLogos is built on the idea that important phenomena are often better modeled as **shapes of relations** rather than isolated variables.

Instead of asking only:

> "What is the predicted label?"

VeriLogos also asks:

> "What is the geometric structure of the situation?"  
> "What persists across scales or time?"  
> "What transformations preserve or violate the underlying logic?"  

This perspective is especially useful when:
- relationships matter more than individual datapoints
- temporal evolution is part of the signal
- explainability is needed
- persistent structural patterns carry semantic value

---

## Key Features

### 🔷 Topological Foundations
- Simplicial complex construction
- Subcomplex representation
- Face-closure validation
- Dimension tracking
- Set-theoretic operations on complexes

### 🔶 Geometric Logic
- Pure SC-logic style operations
- Deterministic, timeless logical evaluation
- Explicit separation from temporal and modal layers
- Structured entailment-style outputs

### ⏱️ Temporal Semantics
- Filtration-based evolution of structure
- Temporal valuation components
- Support for dynamic structural reasoning

### 📊 Persistent Homology
- Persistence computation interfaces
- Barcode and interval abstractions
- Persistence engine support
- Topological feature extraction across scales

### 🧠 Reasoning and API Layer
- Public facade-style imports
- Reasoning API access
- Modal status abstractions
- Clean architecture aligned API mapping

### 🚀 Applied System Components
- Application engines
- Realtime monitoring modules
- Market data sources
- Backtesting infrastructure
- Example scripts and test suite

---

## Architecture

VeriLogos follows a **strict layered architecture**.

This is one of the project's defining design principles.

### Layer
درست می‌گویی — برای `README.md` باید **Markdown خالص** باشد تا مستقیم در گیت‌هاب کار کند. پایین یک نسخه کامل و تمیز Markdown می‌گذارم که **می‌توانی مستقیم کپی کنی داخل `README.md`**.

# VeriLogos

Topological Market Regime Detection and Verification Framework

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Version](https://img.shields.io/badge/version-0.1.0-green)

VeriLogos is a research-oriented Python framework for modeling structure, dynamics, and verification using topology, geometric logic, temporal filtration, and persistent homology.

Originally migrated from the SANN architecture, VeriLogos provides a layered foundation for systems that reason about structures as geometric objects instead of scalar labels.

Current focus: **topological market regime detection**.

---

# Table of Contents

- Why VeriLogos
- Core Idea
- Key Features
- Architecture
- Project Structure
- Installation
- Quick Start
- Testing
- Research Motivation
- Roadmap
- License
- Author
- Citation

---

# Why VeriLogos

Most analytical systems treat system state as scalar outputs:

- bullish / bearish
- true / false
- anomaly / normal

VeriLogos models **structure as geometry** instead.

This includes:

- simplicial complexes
- subcomplex relations
- filtrations across time
- persistent homology
- logical operations over topology

This allows analysis of:

- structural market regimes
- persistence of patterns
- structural anomalies
- interpretable topology-driven alerts

---

# Core Idea

VeriLogos treats system state as a **geometric structure**.

Instead of asking:

"What label should be predicted?"

VeriLogos asks:

- What is the geometric structure?
- What persists across time?
- Which structures remain stable across scales?

This approach is useful when:

- relationships matter more than individual variables
- systems evolve through time
- interpretability is required
- persistent structure carries meaning

---

# Key Features

## Topological Foundations

- Simplicial complex construction
- Subcomplex representation
- Face closure validation
- Dimension tracking
- Set-theoretic operations

## Geometric Logic

- Deterministic SC‑Logic operations
- Pure structural reasoning
- Layer separation from temporal semantics
- Entailment-style evaluation

## Temporal Semantics

- Filtration sequences
- Temporal valuation
- Structural evolution across time

## Persistent Homology

- Betti numbers
- Persistence intervals
- Barcode representation
- Topological feature extraction

## Application Layer

- Market monitoring engines
- Realtime topology tracking
- Backtesting pipeline
- Data connectors

---

# Architecture

VeriLogos uses a strict layered architecture.


Layer 3  Modal Semantics
Layer 2  Temporal Semantics
Layer 1  Geometric Logic
Layer 0  Topology

## Layer 0 — Topology

Core structures:

- SimplicialComplex
- Subcomplex

Responsibilities:

- simplex normalization
- face closure
- dimension tracking
- set operations

Forbidden at this layer:

- temporal awareness
- modal logic
- external state mutation

---

## Layer 1 — Geometric Logic

Pure logical operations on complexes.

Properties:

- deterministic
- timeless
- side‑effect free

Typical outputs:


explicit
inferable
not_entailed

---

## Layer 2 — Temporal Semantics

Adds time-aware reasoning.

Components:

- filtration
- temporal valuation
- structural evolution

---

## Layer 3 — Modal Semantics

High-level reasoning layer.

Capabilities:

- modal reasoning
- entailment evaluation
- reasoning APIs

---

# Project Structure


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

---

# Installation

Clone repository:


git clone https://github.com/pourmoslemy/VeriLogos.git
cd VeriLogos

Install package:


pip install -e .

---

# Quick Start

Run tests:


pytest tests/ -v

Example imports:


from verilogos.core import SimplicialComplex
from verilogos.core import Subcomplex
from verilogos.core import TemporalFiltration
from verilogos.core.persistence import PersistenceEngine

---

# Testing

Run the full test suite:


pytest tests/ -v

Verbose mode:


pytest tests/ -vv

---

# Research Motivation

VeriLogos explores the idea that **truth and system states can be modeled as geometric structures**.

Research directions include:

- topological AI
- geometric reasoning systems
- structural truth modeling
- interpretable topology-based machine learning

---

# Roadmap

Planned improvements:

- visualization tools
- persistence diagrams
- Betti curve plotting
- expanded datasets
- improved experiments
- research pipelines for truth geometry

---

# License

MIT License

---

# Author

Alireza Pourmoslemi

Email: apmath99@gmail.com

---

# Citation

If you use VeriLogos in research:


@software{pourmoslemi_verilogos_2026,
  author = {Pourmoslemi, Alireza},
  title = {VeriLogos: Topological Market Regime Detection Framework},
  year = {2026},
  license = {MIT}
}
