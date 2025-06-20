"""Basic integration test for Simple Auto Cover."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for mod in ["numpy", "pandas", "pytz", "dateutil", "dateutil.parser"]:
    sys.modules.pop(mod, None)
importlib.invalidate_caches()

try:
    import custom_components.simple_auto_cover as sac
except Exception as exc:
    pytest.fail(f"Integration failed to load: {exc}")


def test_import_success():
    """Ensure the integration imports without errors."""
    assert sac.DOMAIN == "simple_auto_cover"
