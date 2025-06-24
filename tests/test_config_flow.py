"""Tests for the config flow helpers."""

import pytest

try:
    import custom_components.simple_auto_cover.config_flow as cf
except Exception as exc:  # pragma: no cover - import failure should fail test
    pytest.fail(f"Failed to import config flow: {exc}")


@pytest.mark.asyncio
async def test_vertical_schema_callable():
    """Ensure the vertical step returns a callable schema."""

    handler = cf.ConfigFlowHandler()
    result = await handler.async_step_vertical(None)
    schema = result["data_schema"]
    assert callable(schema)
    assert isinstance(schema({}), dict)


@pytest.mark.asyncio
async def test_blind_step_sets_type():
    """Ensure each blind step assigns the correct sensor type."""
    handler = cf.ConfigFlowHandler()

    await handler.async_step_vertical(None)
    assert handler.type_blind == cf.SensorType.BLIND

    handler = cf.ConfigFlowHandler()
    await handler.async_step_horizontal(None)
    assert handler.type_blind == cf.SensorType.AWNING

    handler = cf.ConfigFlowHandler()
    await handler.async_step_tilt(None)
    assert handler.type_blind == cf.SensorType.TILT


class DummyFlow(cf.ConfigFlowHandler):
    """Expose next step calls for testing."""

    def __init__(self):
        """Initialize with a record of called steps."""
        super().__init__()
        self.called: list[str] = []

    async def async_step_interp(self):
        """Handle the interpolation step."""
        self.called.append("interp")
        return self.async_show_form(
            step_id="interp", data_schema=cf.INTERPOLATION_OPTIONS
        )

    async def async_step_blind_spot(self):
        """Handle the blind spot configuration step."""
        self.called.append("blind_spot")
        return self.async_show_form(
            step_id="blind_spot", data_schema=cf.AUTOMATION_CONFIG
        )

    async def async_step_automation(self):
        """Handle the automation configuration step."""
        self.called.append("automation")
        return self.async_show_form(
            step_id="automation", data_schema=cf.AUTOMATION_CONFIG
        )


@pytest.mark.asyncio
async def test_blind_step_branches():
    """Validate branching logic of the blind setup helper."""
    handler = DummyFlow()
    data = {cf.CONF_INTERP: True, cf.CONF_ENABLE_BLIND_SPOT: False}
    result = await handler.async_step_vertical(data)
    assert handler.called == ["interp"]
    assert result["step_id"] == "interp"

    handler = DummyFlow()
    data = {cf.CONF_INTERP: False, cf.CONF_ENABLE_BLIND_SPOT: True}
    result = await handler.async_step_vertical(data)
    assert handler.called == ["blind_spot"]
    assert result["step_id"] == "blind_spot"

    handler = DummyFlow()
    data = {cf.CONF_INTERP: False, cf.CONF_ENABLE_BLIND_SPOT: False}
    result = await handler.async_step_vertical(data)
    assert handler.called == ["automation"]
    assert result["step_id"] == "automation"


@pytest.mark.asyncio
async def test_blind_step_validation():
    """Check validation of min/max elevation in the helper."""
    handler = cf.ConfigFlowHandler()
    data = {
        cf.CONF_MIN_ELEVATION: 10,
        cf.CONF_MAX_ELEVATION: 5,
        cf.CONF_INTERP: False,
        cf.CONF_ENABLE_BLIND_SPOT: False,
    }
    result = await handler.async_step_vertical(data)
    assert result["type"] == "form"
    assert result["errors"] == {
        cf.CONF_MAX_ELEVATION: "Must be greater than 'Minimal Elevation'"
    }


def test_validate_elevation_range():
    """Verify the helper correctly compares min and max elevation."""
    params = {
        (10, 5): True,
        (5, 10): False,
        (None, 5): True,
        (10, None): True,
    }
    for (max_elev, min_elev), expected in params.items():
        data = {}
        if max_elev is not None:
            data[cf.CONF_MAX_ELEVATION] = max_elev
        if min_elev is not None:
            data[cf.CONF_MIN_ELEVATION] = min_elev
        assert cf._validate_elevation_range(data) is expected
