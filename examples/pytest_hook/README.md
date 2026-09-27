# Jev Harness - Pytest Failure Interceptor Hook

This hook provides transparent, zero-token failure triage for `pytest`.

## Quick Setup

1. Install `jev-harness`:
```bash
pip install jev-harness
```

2. Copy `conftest.py` into your repository root or `tests/` directory:
```bash
cp examples/pytest_hook/conftest.py ./conftest.py
```

3. Run pytest normally:
```bash
pytest
```

If a missing dependency (e.g. `ModuleNotFoundError`) or a transient port/network error occurs during test execution, `jev-harness` intercepts the traceback locally in < 500µs and prints the exact shell fix, preventing AI coding agents from burning 50,000 frontier tokens on an environment issue.
