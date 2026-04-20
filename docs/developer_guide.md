# VeriLogos Developer Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Testing Strategy](#testing-strategy)
4. [Code Style](#code-style)
5. [Architecture Contracts](#architecture-contracts)
6. [Contribution Guidelines](#contribution-guidelines)

---

## Getting Started

### Prerequisites
- Python 3.10 or higher
- pip or conda package manager
- Git

### Installation

#### 1. Clone the repository
```bash
git clone https://github.com/your-org/verilogos.git
cd verilogos
```

#### 2. Create virtual environment
```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Using conda
conda create -n verilogos python=3.10
conda activate verilogos
```

#### 3. Install dependencies
```bash
# Development installation (editable mode)
pip install -e .

# Install development dependencies
pip install pytest pytest-cov mypy black isort sphinx sphinx-rtd-theme
```

#### 4. Verify installation
```bash
pytest tests/ -v
# Expected: 202/202 tests passing
```

---

## Development Workflow

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: New features
- `fix/*`: Bug fixes
- `docs/*`: Documentation updates

### Typical Workflow
```bash
# 1. Create feature branch
git checkout -b feature/add-new-metric

# 2. Make changes
# ... edit files ...

# 3. Run tests
pytest tests/ -v

# 4. Run type checker
mypy verilogos/

# 5. Format code
black verilogos/ tests/
isort verilogos/ tests/

# 6. Commit changes
git add .
git commit -m "feat: add new topological metric"

# 7. Push and create PR
git push origin feature/add-new-metric
```

---

## Testing Strategy

### Test Organization

```
tests/
├── topology/           # Layer 0-3 tests
│   ├── test_layer0_imports.py
│   ├── test_layer1_sclogic.py
│   ├── test_layer2_temporal.py
│   └── test_layer3_persistence.py
├── application/        # Layer 4 tests
│   ├── test_layer4_engines.py
│   └── test_layer4_integration.py
└── test_persistence_barcode.py
```

### Running Tests

#### Run all tests
```bash
pytest tests/ -v
```

#### Run specific layer
```bash
pytest tests/topology/test_layer1_sclogic.py -v
```

#### Run with coverage
```bash
pytest tests/ --cov=verilogos --cov-report=html
```

### Writing Tests

#### Example: Testing SC-Logic Operations
```python
import pytest
from verilogos.core.topology.complexes.complex import SimplicialComplex
from verilogos.core.topology.complexes.subcomplex import Subcomplex
from verilogos.core.operators.sclogic_ops import SCLogicOperations

def test_conjunction_preserves_closure():
    """Test that conjunction of closed subcomplexes is closed."""
    K = SimplicialComplex([(0, 1), (1, 2), (0, 2)])
    ops = SCLogicOperations(K)
    
    p = Subcomplex(simplices={(0,), (1,), (0, 1)}, ambient=K)
    q = Subcomplex(simplices={(1,), (2,), (1, 2)}, ambient=K)
    
    result = ops.conjunction(p, q)
    
    assert result.is_face_closed()
    assert (1,) in result.simplices[0]  # Intersection
```

---

## Code Style

### Type Hints (Mandatory)
```python
# ✅ Good
def compute_betti_numbers(
    complex: SimplicialComplex, 
    max_dim: int = 2
) -> Dict[int, int]:
    """Compute Betti numbers up to max_dim."""
    ...

# ❌ Bad
def compute_betti_numbers(complex, max_dim=2):
    """Compute Betti numbers up to max_dim."""
    ...
```

### Docstrings (Google Style)
```python
def emerges_at(self, proposition: str) -> Optional[int]:
    """Find the first time step where proposition becomes true.
    
    Args:
        proposition: Name of the proposition to check.
    
    Returns:
        The first time index where proposition is satisfied, or None if never.
    
    Raises:
        ValueError: If proposition is not registered in valuation.
    
    Example:
        >>> filtration = Filtration([K0, K1, K2])
        >>> valuation = TemporalValuation(filtration, {"p": [V0, V1, V2]})
        >>> t = valuation.emerges_at("p")
        >>> print(t)
        1
    """
    ...
```

### Import Organization
```python
# Standard library
import os
from typing import Dict, List, Optional

# Third-party
import numpy as np

# Local
from verilogos.core.topology.complexes.complex import SimplicialComplex
from verilogos.core.operators.sclogic_ops import SCLogicOperations
```

### Formatting
- **Line length:** 100 characters (configured in `pyproject.toml`)
- **Indentation:** 4 spaces
- **Quotes:** Double quotes for strings
- **Trailing commas:** Yes for multi-line collections

---

## Architecture Contracts

### Layer Dependency Rules

#### ✅ Allowed
```python
# Layer 3 can import from Layer 2, 1, 0
from verilogos.core.topology.complexes.temporal_filtration import Filtration
from verilogos.core.operators.sclogic_ops import SCLogicOperations
```

#### ❌ Forbidden
```python
# Layer 1 CANNOT import from Layer 2
# This will fail architecture contract tests
from verilogos.core.topology.complexes.temporal_filtration import Filtration
```

### Frozen APIs

#### Layer 1: SCLogicOperations
**DO NOT:**
- Change method signatures
- Add temporal parameters
- Import from `temporal_filtration` or `modal/`
- Change `query()` return type from `str`

**DO:**
- Add new methods with default parameters
- Optimize internal implementation
- Add helper functions (private, prefixed with `_`)

---

## Contribution Guidelines

### Before Submitting PR

#### 1. Run full test suite
```bash
pytest tests/ -v
```

#### 2. Run type checker
```bash
mypy verilogos/ --strict
```

#### 3. Format code
```bash
black verilogos/ tests/
isort verilogos/ tests/
```

#### 4. Update documentation
- Add docstrings to new functions/classes
- Update `ARCHITECTURE.md` if adding new layers/modules
- Add examples to `docs/examples/`

### PR Checklist
- [ ] All tests pass (202/202)
- [ ] Type hints added to all public APIs
- [ ] Docstrings follow Google style
- [ ] No upward layer dependencies introduced
- [ ] Code formatted with Black + isort
- [ ] CHANGELOG.md updated (if applicable)

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests
- `chore`: Maintenance

**Example:**

```
feat(persistence): add barcode visualization

- Add matplotlib-based barcode plotting
- Support both finite and infinite intervals
- Include dimension coloring

Closes #42
```

---

## Troubleshooting

### Common Issues

#### Issue: Import errors after installation
```bash
# Solution: Reinstall in editable mode
pip install -e .
```

#### Issue: Tests fail with "ModuleNotFoundError"
```bash
# Solution: Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## Resources

### Documentation
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)

### Papers
- "Truth as Geometry" (Definition 2.13 for SC-logic)
- "Computing Persistent Homology" (Zomorodian & Carlsson)

### Tools
- [mypy](https://mypy.readthedocs.io/) – Static type checker
- [Black](https://black.readthedocs.io/) – Code formatter
- [pytest](https://docs.pytest.org/) – Testing framework

---

## Contact
- **Maintainer:** VeriLogos Team
- **Issues:** https://github.com/your-org/verilogos/issues
