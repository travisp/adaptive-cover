import sys
import types
import math
import datetime as dt
from pathlib import Path
from importlib import util
import pytest

# ---------------------------------------------------------------------------
# Minimal stubs for third party dependencies (numpy, pandas, pytz, dateutil)
# ---------------------------------------------------------------------------

numpy_stub = types.ModuleType("numpy")
numpy_stub.interp = (
    lambda x, xp, fp: fp[0] + (fp[1] - fp[0]) * (x - xp[0]) / (xp[1] - xp[0]) if xp[1] - xp[0] else fp[0]
)
numpy_stub.cos = math.cos
numpy_stub.sin = math.sin
numpy_stub.tan = math.tan
numpy_stub.clip = lambda x, low, high: max(min(x, high), low)
numpy_stub.radians = math.radians
numpy_stub.rad2deg = math.degrees
numpy_stub.arctan = math.atan
numpy_stub.sqrt = math.sqrt
numpy_stub.where = lambda cond, a, b: a if cond else b
numpy_stub.isscalar = lambda obj: isinstance(obj, (int, float, complex))
sys.modules.setdefault("numpy", numpy_stub)

pandas_stub = types.ModuleType("pandas")
pandas_stub.DatetimeIndex = list
sys.modules.setdefault("pandas", pandas_stub)

pytz_stub = types.ModuleType("pytz")
pytz_stub.UTC = dt.UTC
sys.modules.setdefault("pytz", pytz_stub)

dateutil = types.ModuleType("dateutil")
parser_stub = types.ModuleType("dateutil.parser")
parser_stub.parse = lambda *a, **k: dt.datetime.now(dt.UTC)
dateutil.parser = parser_stub
sys.modules.setdefault("dateutil", dateutil)
sys.modules.setdefault("dateutil.parser", parser_stub)

# ---------------------------------------------------------------------------
# Helper to load integration modules from file paths
# ---------------------------------------------------------------------------

def import_module(path: str, name: str):
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
    return import_module(
        "custom_components/simple_auto_cover/calculation.py",
        "custom_components.simple_auto_cover.calculation",
    )


@pytest.fixture
def coordinator():
    return import_module(
        "custom_components/simple_auto_cover/coordinator.py",
        "custom_components.simple_auto_cover.coordinator",
    )
