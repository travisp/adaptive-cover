import importlib
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for mod in ["numpy", "pandas", "pytz", "dateutil", "dateutil.parser"]:
    sys.modules.pop(mod, None)
importlib.invalidate_caches()

try:
    import custom_components.simple_auto_cover.config_flow as cf
except Exception as exc:
    pytest.fail(f"Failed to import config flow: {exc}")


@pytest.mark.asyncio
async def test_vertical_schema_callable():
    handler = cf.ConfigFlowHandler()
    result = await handler.async_step_vertical(None)
    schema = result["data_schema"]
    assert callable(schema)
    assert isinstance(schema({}), dict)
