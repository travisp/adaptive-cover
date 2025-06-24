"""Fixtures and helper utilities for the test suite."""

import sys
from pathlib import Path
from importlib import util

import pytest


# ---------------------------------------------------------------------------
# Helper to load integration modules from file paths
# ---------------------------------------------------------------------------


def import_module(path: str, name: str):
    """Load ``name`` from the specified ``path``."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    package = name.rpartition(".")[0]
    if package and package not in sys.modules:
        __import__(package)
    spec = util.spec_from_file_location(name, root / path)
    module = util.module_from_spec(spec)
    assert spec.loader is not None

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def calculation():
    """Provide the calculation module used in tests."""
    return import_module(
        "custom_components/simple_auto_cover/calculation.py",
        "custom_components.simple_auto_cover.calculation",
    )


@pytest.fixture
def coordinator():
    """Provide the coordinator module used in tests."""
    return import_module(
        "custom_components/simple_auto_cover/coordinator.py",
        "custom_components.simple_auto_cover.coordinator",
    )
