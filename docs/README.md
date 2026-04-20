# VeriLogos Documentation

This directory contains the complete documentation for VeriLogos.

## Building Documentation

### Prerequisites

Install documentation dependencies:

```bash
pip install -r requirements.txt
```

### Build HTML Documentation

```bash
cd docs
make html
```

The generated documentation will be in `_build/html/`.

### View Documentation Locally

```bash
python -m http.server 8000 --directory _build/html
```

Then open http://localhost:8000 in your browser.

### Clean Build

```bash
make clean
make html
```

## Documentation Structure

```
docs/
├── index.rst                    # Main documentation index
├── introduction.md              # Introduction to VeriLogos
├── architecture.md              # Architecture overview (links to ../ARCHITECTURE.md)
├── developer_guide.md           # Developer guide
├── migration_notes.md           # Migration history
├── api/                         # API reference
│   ├── index.rst               # API index
│   ├── layer0_topology.rst     # Layer 0 API
│   ├── layer1_sclogic.rst      # Layer 1 API
│   ├── layer2_temporal.rst     # Layer 2 API
│   ├── layer3_persistence.rst  # Layer 3 API
│   └── layer4_application.rst  # Layer 4 API
├── conf.py                      # Sphinx configuration
├── Makefile                     # Build automation
└── requirements.txt             # Documentation dependencies
```

## Updating Documentation

### Adding New Modules

1. Add module to appropriate layer file in `api/`
2. Use `.. automodule::` directive
3. Rebuild documentation

Example:
```rst
.. automodule:: verilogos.new.module
   :members:
   :undoc-members:
   :show-inheritance:
```

### Adding New Pages

1. Create `.md` or `.rst` file in `docs/`
2. Add to `toctree` in `index.rst`
3. Rebuild documentation

### Updating API Reference

API documentation is auto-generated from docstrings. To update:

1. Edit docstrings in source code
2. Rebuild documentation
3. Verify changes in browser

## Troubleshooting

### Issue: "Module not found" errors

**Solution:** Ensure VeriLogos is installed in editable mode:
```bash
pip install -e .
```

### Issue: Documentation not updating

**Solution:** Clean build and rebuild:
```bash
make clean
make html
```

### Issue: Math rendering not working

**Solution:** Ensure `sphinx.ext.mathjax` is in `extensions` list in `conf.py`.

## Contributing

When adding new features:

1. Add docstrings to all public functions/classes
2. Follow Google docstring style
3. Include type hints
4. Add examples where appropriate
5. Update relevant API reference file
6. Rebuild and verify documentation

## Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [MyST Parser](https://myst-parser.readthedocs.io/)
- [Read the Docs Theme](https://sphinx-rtd-theme.readthedocs.io/)
