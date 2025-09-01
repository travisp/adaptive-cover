"""Config flow for Simple Auto Cover integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from homeassistant.const import CONF_NAME
from .const import (
    CONF_AWNING_ANGLE,
    CONF_AZIMUTH,
    CONF_BLIND_SPOT_ELEVATION,
    CONF_BLIND_SPOT_LEFT,
    CONF_BLIND_SPOT_RIGHT,
    CONF_DEFAULT_HEIGHT,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_DISTANCE,
    CONF_ENABLE_BLIND_SPOT,
    CONF_END_ENTITY,
    CONF_END_TIME,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_INTERP,
    CONF_INTERP_END,
    CONF_INTERP_LIST,
    CONF_INTERP_LIST_NEW,
    CONF_INTERP_START,
    CONF_INVERSE_STATE,
    CONF_LENGTH_AWNING,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_RESET,
    CONF_MANUAL_THRESHOLD,
    CONF_MAX_ELEVATION,
    CONF_MAX_POSITION,
    CONF_MIN_ELEVATION,
    CONF_MODE,
    CONF_RETURN_SUNSET,
    CONF_SENSOR_TYPE,
    CONF_START_ENTITY,
    CONF_START_TIME,
    CONF_SUNRISE_OFFSET,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    DOMAIN,
    COVER_TYPE_DISPLAY,
    STRATEGY_MODE_BASIC,
    SensorType,
    CONF_MIN_POSITION,
    CONF_ENABLE_MAX_POSITION,
    CONF_ENABLE_MIN_POSITION,
)

# DEFAULT_NAME = "Simple Auto Cover"

SENSOR_TYPE_MENU = [SensorType.BLIND, SensorType.AWNING, SensorType.TILT]


CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=SENSOR_TYPE_MENU, translation_key="mode"
            )
        ),
    }
)


def _get_options_schema(options: dict | None = None) -> vol.Schema:
    """Return the base options schema."""
    options = options or {}
    schema: dict = {
        vol.Required(CONF_AZIMUTH, default=options.get(CONF_AZIMUTH, 180)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=359, mode="slider", unit_of_measurement="°")
        ),
        vol.Required(CONF_DEFAULT_HEIGHT, default=options.get(CONF_DEFAULT_HEIGHT, 60)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode="slider", unit_of_measurement="%")
        ),
        vol.Optional(CONF_ENABLE_MAX_POSITION, default=options.get(CONF_ENABLE_MAX_POSITION, False)): bool,
        vol.Optional(CONF_ENABLE_MIN_POSITION, default=options.get(CONF_ENABLE_MIN_POSITION, False)): bool,
        vol.Required(CONF_FOV_LEFT, default=options.get(CONF_FOV_LEFT, 90)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=90, step=1, mode="slider", unit_of_measurement="°")
        ),
        vol.Required(CONF_FOV_RIGHT, default=options.get(CONF_FOV_RIGHT, 90)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=90, step=1, mode="slider", unit_of_measurement="°")
        ),
        vol.Required(CONF_SUNSET_POS, default=options.get(CONF_SUNSET_POS, 0)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode="slider", unit_of_measurement="%")
        ),
        vol.Required(CONF_SUNSET_OFFSET, default=options.get(CONF_SUNSET_OFFSET, 0)): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="box", unit_of_measurement="minutes")
        ),
        vol.Required(CONF_SUNRISE_OFFSET, default=options.get(CONF_SUNRISE_OFFSET, 0)): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="box", unit_of_measurement="minutes")
        ),
        vol.Required(CONF_INVERSE_STATE, default=options.get(CONF_INVERSE_STATE, False)): bool,
        vol.Required(CONF_ENABLE_BLIND_SPOT, default=options.get(CONF_ENABLE_BLIND_SPOT, False)): bool,
        vol.Required(CONF_INTERP, default=options.get(CONF_INTERP, False)): bool,
    }
    if (val := options.get(CONF_MAX_POSITION)) is not None:
        schema[vol.Optional(CONF_MAX_POSITION, default=val)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=100, mode="slider")
        )
    else:
        schema[vol.Optional(CONF_MAX_POSITION)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=100, mode="slider")
        )
    if (val := options.get(CONF_MIN_POSITION)) is not None:
        schema[vol.Optional(CONF_MIN_POSITION, default=val)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=99, mode="slider")
        )
    else:
        schema[vol.Optional(CONF_MIN_POSITION)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=99, mode="slider")
        )
    if (val := options.get(CONF_MIN_ELEVATION)) is not None:
        schema[vol.Optional(CONF_MIN_ELEVATION, default=val)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=90, mode="slider")
        )
    else:
        schema[vol.Optional(CONF_MIN_ELEVATION)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=90, mode="slider")
        )
    if (val := options.get(CONF_MAX_ELEVATION)) is not None:
        schema[vol.Optional(CONF_MAX_ELEVATION, default=val)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=90, mode="slider")
        )
    else:
        schema[vol.Optional(CONF_MAX_ELEVATION)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=90, mode="slider")
        )
    return vol.Schema(schema)

OPTIONS = _get_options_schema()

def _get_vertical_options_schema(options: dict | None = None) -> vol.Schema:
    """Return the schema for vertical blinds."""
    options = options or {}
    vertical = vol.Schema(
        {
            vol.Optional(CONF_ENTITIES, default=options.get(CONF_ENTITIES, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    multiple=True,
                    filter=selector.EntityFilterSelectorConfig(
                        domain="cover",
                        supported_features=["cover.CoverEntityFeature.SET_POSITION"],
                    ),
                )
            ),
            vol.Required(CONF_HEIGHT_WIN, default=options.get(CONF_HEIGHT_WIN, 2.1)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1, max=6, step=0.01, mode="slider", unit_of_measurement="m"
                )
            ),
            vol.Required(CONF_DISTANCE, default=options.get(CONF_DISTANCE, 0.5)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1, max=2, step=0.1, mode="slider", unit_of_measurement="m"
                )
            ),
        }
    )
    return vertical.extend(_get_options_schema(options).schema)

VERTICAL_OPTIONS = _get_vertical_options_schema()


def _get_horizontal_options_schema(options: dict | None = None) -> vol.Schema:
    """Return the schema for awnings."""
    options = options or {}
    horizontal = vol.Schema(
        {
            vol.Required(CONF_LENGTH_AWNING, default=options.get(CONF_LENGTH_AWNING, 2.1)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.3, max=6, step=0.01, mode="slider", unit_of_measurement="m"
                )
            ),
            vol.Required(CONF_AWNING_ANGLE, default=options.get(CONF_AWNING_ANGLE, 0)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=45, mode="slider", unit_of_measurement="°"
                )
            ),
        }
    )
    return horizontal.extend(_get_vertical_options_schema(options).schema)

HORIZONTAL_OPTIONS = _get_horizontal_options_schema()

def _get_tilt_options_schema(options: dict | None = None) -> vol.Schema:
    """Return the schema for tilt mode."""
    options = options or {}
    tilt = vol.Schema(
        {
            vol.Optional(CONF_ENTITIES, default=options.get(CONF_ENTITIES, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    multiple=True,
                    filter=selector.EntityFilterSelectorConfig(
                        domain="cover",
                        supported_features=["cover.CoverEntityFeature.SET_TILT_POSITION"],
                    ),
                )
            ),
            vol.Required(CONF_TILT_DEPTH, default=options.get(CONF_TILT_DEPTH, 3)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1, max=15, step=0.1, mode="slider", unit_of_measurement="cm"
                )
            ),
            vol.Required(CONF_TILT_DISTANCE, default=options.get(CONF_TILT_DISTANCE, 2)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1, max=15, step=0.1, mode="slider", unit_of_measurement="cm"
                )
            ),
            vol.Required(CONF_TILT_MODE, default=options.get(CONF_TILT_MODE, "mode2")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["mode1", "mode2"], translation_key="tilt_mode"
                )
            ),
        }
    )
    return tilt.extend(_get_options_schema(options).schema)

TILT_OPTIONS = _get_tilt_options_schema()


def _get_automation_config_schema(options: dict | None = None) -> vol.Schema:
    """Return the automation configuration schema."""
    options = options or {}
    return vol.Schema(
        {
            vol.Required(CONF_DELTA_POSITION, default=options.get(CONF_DELTA_POSITION, 1)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=90, step=1, mode="slider", unit_of_measurement="%"
                )
            ),
            vol.Optional(CONF_DELTA_TIME, default=options.get(CONF_DELTA_TIME, 2)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=2, mode="box", unit_of_measurement="minutes"
                )
            ),
            vol.Optional(CONF_START_TIME, default=options.get(CONF_START_TIME, "00:00:00")): selector.TimeSelector(),
            vol.Optional(CONF_START_ENTITY, default=options.get(CONF_START_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
            ),
            vol.Required(
                CONF_MANUAL_OVERRIDE_DURATION, default=options.get(CONF_MANUAL_OVERRIDE_DURATION, {"minutes": 15})
            ): selector.DurationSelector(),
            vol.Required(CONF_MANUAL_OVERRIDE_RESET, default=options.get(CONF_MANUAL_OVERRIDE_RESET, False)): bool,
            vol.Optional(CONF_MANUAL_THRESHOLD, default=options.get(CONF_MANUAL_THRESHOLD)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=99, mode="slider")
            ),
            vol.Optional(CONF_MANUAL_IGNORE_INTERMEDIATE, default=options.get(CONF_MANUAL_IGNORE_INTERMEDIATE, False)): bool,
            vol.Optional(CONF_END_TIME, default=options.get(CONF_END_TIME, "00:00:00")): selector.TimeSelector(),
            vol.Optional(CONF_END_ENTITY, default=options.get(CONF_END_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
            ),
            vol.Optional(CONF_RETURN_SUNSET, default=options.get(CONF_RETURN_SUNSET, False)): bool,
        }
    )

AUTOMATION_CONFIG = _get_automation_config_schema()

def _get_interpolation_options_schema(options: dict | None = None) -> vol.Schema:
    """Return the interpolation options schema."""
    options = options or {}
    return vol.Schema(
        {
            vol.Optional(CONF_INTERP_START, default=options.get(CONF_INTERP_START)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, mode="slider")
            ),
            vol.Optional(CONF_INTERP_END, default=options.get(CONF_INTERP_END)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, mode="slider")
            ),
            vol.Optional(CONF_INTERP_LIST, default=options.get(CONF_INTERP_LIST, [])): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    multiple=True, custom_value=True, options=["0", "50", "100"]
                )
            ),
            vol.Optional(CONF_INTERP_LIST_NEW, default=options.get(CONF_INTERP_LIST_NEW, [])): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    multiple=True, custom_value=True, options=["0", "50", "100"]
                )
            ),
        }
    )

INTERPOLATION_OPTIONS = _get_interpolation_options_schema()


def _get_azimuth_edges(data) -> tuple[int, int]:
    """Calculate azimuth edges."""
    return data[CONF_FOV_LEFT] + data[CONF_FOV_RIGHT]


def _validate_elevation_range(user_input: dict[str, Any]) -> bool:
    """Return True if max elevation is greater than min elevation."""
    return not (
        user_input.get(CONF_MAX_ELEVATION) is not None
        and user_input.get(CONF_MIN_ELEVATION) is not None
        and user_input[CONF_MAX_ELEVATION] <= user_input[CONF_MIN_ELEVATION]
    )


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle ConfigFlow."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__()
        self.type_blind: str | None = None
        self.config: dict[str, Any] = {}
        self.mode: str = STRATEGY_MODE_BASIC

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def _handle_blind_step(
        self,
        user_input: dict[str, Any] | None,
        schema: vol.Schema,
        sensor_type: SensorType,
        step_id: str,
    ) -> FlowResult:
        """Process shared validation and branching logic for blind steps."""
        self.type_blind = sensor_type

        if user_input is not None:
            if not _validate_elevation_range(user_input):
                return self.async_show_form(
                    step_id=step_id,
                    data_schema=schema,
                    errors={
                        CONF_MAX_ELEVATION: "Must be greater than 'Minimal Elevation'"
                    },
                )

            self.config.update(user_input)

            if self.config[CONF_INTERP]:
                return await self.async_step_interp()
            if self.config[CONF_ENABLE_BLIND_SPOT]:
                return await self.async_step_blind_spot()

            return await self.async_step_automation()

        return self.async_show_form(step_id=step_id, data_schema=schema)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        # errors = {}
        if user_input:
            self.config = user_input
            if self.config[CONF_MODE] == SensorType.BLIND:
                return await self.async_step_vertical()
            if self.config[CONF_MODE] == SensorType.AWNING:
                return await self.async_step_horizontal()
            if self.config[CONF_MODE] == SensorType.TILT:
                return await self.async_step_tilt()
        return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA)

    async def async_step_vertical(self, user_input: dict[str, Any] | None = None):
        """Show basic config for vertical blinds."""
        return await self._handle_blind_step(
            user_input,
            _get_vertical_options_schema(),
            SensorType.BLIND,
            "vertical",
        )

    async def async_step_horizontal(self, user_input: dict[str, Any] | None = None):
        """Show basic config for horizontal blinds."""
        return await self._handle_blind_step(
            user_input,
            _get_horizontal_options_schema(),
            SensorType.AWNING,
            "horizontal",
        )

    async def async_step_tilt(self, user_input: dict[str, Any] | None = None):
        """Show basic config for tilted blinds."""
        return await self._handle_blind_step(
            user_input,
            _get_tilt_options_schema(),
            SensorType.TILT,
            "tilt",
        )

    async def async_step_interp(self, user_input: dict[str, Any] | None = None):
        """Show interpolation options."""
        if user_input is not None:
            if len(user_input[CONF_INTERP_LIST]) != len(
                user_input[CONF_INTERP_LIST_NEW]
            ):
                return self.async_show_form(
                    step_id="interp",
                    data_schema=INTERPOLATION_OPTIONS,
                    errors={
                        CONF_INTERP_LIST_NEW: "Must have same length as 'Interpolation' list"
                    },
                )
            self.config.update(user_input)
            if self.config[CONF_ENABLE_BLIND_SPOT]:
                return await self.async_step_blind_spot()
            return await self.async_step_automation()
        return self.async_show_form(step_id="interp", data_schema=INTERPOLATION_OPTIONS)

    async def async_step_blind_spot(self, user_input: dict[str, Any] | None = None):
        """Add blindspot to data."""
        edges = _get_azimuth_edges(self.config)
        schema = vol.Schema(
            {
                vol.Required(CONF_BLIND_SPOT_LEFT, default=0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode="slider", unit_of_measurement="°", min=0, max=edges - 1
                    )
                ),
                vol.Required(CONF_BLIND_SPOT_RIGHT, default=1): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode="slider", unit_of_measurement="°", min=1, max=edges
                    )
                ),
                vol.Optional(CONF_BLIND_SPOT_ELEVATION): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=90, mode="slider")
                ),
            }
        )
        if user_input is not None:
            if user_input[CONF_BLIND_SPOT_RIGHT] <= user_input[CONF_BLIND_SPOT_LEFT]:
                return self.async_show_form(
                    step_id="blind_spot",
                    data_schema=schema,
                    errors={
                        CONF_BLIND_SPOT_RIGHT: "Must be greater than 'Blind Spot Left Edge'"
                    },
                )
            self.config.update(user_input)
            return await self.async_step_automation()

        return self.async_show_form(step_id="blind_spot", data_schema=schema)

    async def async_step_automation(self, user_input: dict[str, Any] | None = None):
        """Manage automation options."""
        if user_input is not None:
            self.config.update(user_input)
            return await self.async_step_update()
        return self.async_show_form(step_id="automation", data_schema=AUTOMATION_CONFIG)

    async def async_step_update(self, user_input: dict[str, Any] | None = None):
        """Create entry."""
        return self.async_create_entry(
            title=f"{COVER_TYPE_DISPLAY[self.type_blind]} {self.config[CONF_NAME]}",
            data={
                CONF_NAME: self.config[CONF_NAME],
                CONF_SENSOR_TYPE: self.type_blind,
            },
            options={
                CONF_MODE: self.mode,
                CONF_AZIMUTH: self.config.get(CONF_AZIMUTH),
                CONF_HEIGHT_WIN: self.config.get(CONF_HEIGHT_WIN),
                CONF_DISTANCE: self.config.get(CONF_DISTANCE),
                CONF_DEFAULT_HEIGHT: self.config.get(CONF_DEFAULT_HEIGHT),
                CONF_MAX_POSITION: self.config.get(CONF_MAX_POSITION),
                CONF_MIN_POSITION: self.config.get(CONF_MIN_POSITION),
                CONF_FOV_LEFT: self.config.get(CONF_FOV_LEFT),
                CONF_FOV_RIGHT: self.config.get(CONF_FOV_RIGHT),
                CONF_ENTITIES: self.config.get(CONF_ENTITIES),
                CONF_INVERSE_STATE: self.config.get(CONF_INVERSE_STATE),
                CONF_SUNSET_POS: self.config.get(CONF_SUNSET_POS),
                CONF_SUNSET_OFFSET: self.config.get(CONF_SUNSET_OFFSET),
                CONF_SUNRISE_OFFSET: self.config.get(CONF_SUNRISE_OFFSET),
                CONF_LENGTH_AWNING: self.config.get(CONF_LENGTH_AWNING),
                CONF_AWNING_ANGLE: self.config.get(CONF_AWNING_ANGLE),
                CONF_TILT_DISTANCE: self.config.get(CONF_TILT_DISTANCE),
                CONF_TILT_DEPTH: self.config.get(CONF_TILT_DEPTH),
                CONF_TILT_MODE: self.config.get(CONF_TILT_MODE),
                CONF_DELTA_POSITION: self.config.get(CONF_DELTA_POSITION),
                CONF_DELTA_TIME: self.config.get(CONF_DELTA_TIME),
                CONF_START_TIME: self.config.get(CONF_START_TIME),
                CONF_START_ENTITY: self.config.get(CONF_START_ENTITY),
                CONF_MANUAL_OVERRIDE_DURATION: self.config.get(
                    CONF_MANUAL_OVERRIDE_DURATION
                ),
                CONF_MANUAL_OVERRIDE_RESET: self.config.get(CONF_MANUAL_OVERRIDE_RESET),
                CONF_MANUAL_THRESHOLD: self.config.get(CONF_MANUAL_THRESHOLD),
                CONF_MANUAL_IGNORE_INTERMEDIATE: self.config.get(
                    CONF_MANUAL_IGNORE_INTERMEDIATE
                ),
                CONF_BLIND_SPOT_RIGHT: self.config.get(CONF_BLIND_SPOT_RIGHT, None),
                CONF_BLIND_SPOT_LEFT: self.config.get(CONF_BLIND_SPOT_LEFT, None),
                CONF_BLIND_SPOT_ELEVATION: self.config.get(
                    CONF_BLIND_SPOT_ELEVATION, None
                ),
                CONF_ENABLE_BLIND_SPOT: self.config.get(CONF_ENABLE_BLIND_SPOT),
                CONF_MIN_ELEVATION: self.config.get(CONF_MIN_ELEVATION, None),
                CONF_MAX_ELEVATION: self.config.get(CONF_MAX_ELEVATION, None),
                CONF_INTERP: self.config.get(CONF_INTERP),
                CONF_INTERP_START: self.config.get(CONF_INTERP_START, None),
                CONF_INTERP_END: self.config.get(CONF_INTERP_END, None),
                CONF_INTERP_LIST: self.config.get(CONF_INTERP_LIST, []),
                CONF_INTERP_LIST_NEW: self.config.get(CONF_INTERP_LIST_NEW, []),
            },
        )


class OptionsFlowHandler(OptionsFlow):
    """Options to adjust parameters."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        # super().__init__(config_entry)
        self.config_entry = config_entry
        self.current_config: dict = dict(config_entry.data)
        self.options = dict(config_entry.options)
        self.sensor_type: SensorType = (
            self.current_config.get(CONF_SENSOR_TYPE) or SensorType.BLIND
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        options = ["automation", "blind"]
        if self.options.get(CONF_ENABLE_BLIND_SPOT):
            options.append("blind_spot")
        if self.options.get(CONF_INTERP):
            options.append("interp")
        return self.async_show_menu(step_id="init", menu_options=options)

    async def async_step_automation(self, user_input: dict[str, Any] | None = None):
        """Manage automation options."""
        if user_input is not None:
            entities = [CONF_START_ENTITY, CONF_END_ENTITY, CONF_MANUAL_THRESHOLD]
            self.optional_entities(entities, user_input)
            self.options.update(user_input)
            return await self._update_options()
        return self.async_show_form(
            step_id="automation",
            data_schema=_get_automation_config_schema(self.options),
        )

    async def async_step_blind(self, user_input: dict[str, Any] | None = None):
        """Adjust blind parameters."""
        if self.sensor_type == SensorType.BLIND:
            return await self.async_step_vertical()
        if self.sensor_type == SensorType.AWNING:
            return await self.async_step_horizontal()
        if self.sensor_type == SensorType.TILT:
            return await self.async_step_tilt()

    async def async_step_vertical(self, user_input: dict[str, Any] | None = None):
        """Show basic config for vertical blinds."""
        self.type_blind = SensorType.BLIND
        schema = _get_vertical_options_schema(self.options)
        if user_input is not None:
            keys = [
                CONF_MIN_ELEVATION,
                CONF_MAX_ELEVATION,
            ]
            self.optional_entities(keys, user_input)
            if not _validate_elevation_range(user_input):
                return self.async_show_form(
                    step_id="vertical",
                    data_schema=VERTICAL_OPTIONS.schema,
                    errors={
                        CONF_MAX_ELEVATION: "Must be greater than 'Minimal Elevation'"
                    },
                )
            self.options.update(user_input)
            if self.options.get(CONF_INTERP, False):
                return await self.async_step_interp()
            if self.options[CONF_ENABLE_BLIND_SPOT]:
                return await self.async_step_blind_spot()
            return await self._update_options()
        return self.async_show_form(
            step_id="vertical",
            data_schema=schema,
        )

    async def async_step_horizontal(self, user_input: dict[str, Any] | None = None):
        """Show basic config for horizontal blinds."""
        self.type_blind = SensorType.AWNING
        schema = _get_horizontal_options_schema(self.options)
        if user_input is not None:
            keys = [
                CONF_MIN_ELEVATION,
                CONF_MAX_ELEVATION,
            ]
            self.optional_entities(keys, user_input)
            if not _validate_elevation_range(user_input):
                return self.async_show_form(
                    step_id="horizontal",
                    data_schema=HORIZONTAL_OPTIONS.schema,
                    errors={
                        CONF_MAX_ELEVATION: "Must be greater than 'Minimal Elevation'"
                    },
                )
            self.options.update(user_input)
            return await self._update_options()
        return self.async_show_form(
            step_id="horizontal",
            data_schema=schema,
        )

    async def async_step_tilt(self, user_input: dict[str, Any] | None = None):
        """Show basic config for tilted blinds."""
        self.type_blind = SensorType.TILT
        schema = _get_tilt_options_schema(self.options)
        if user_input is not None:
            keys = [
                CONF_MIN_ELEVATION,
                CONF_MAX_ELEVATION,
            ]
            self.optional_entities(keys, user_input)
            if not _validate_elevation_range(user_input):
                return self.async_show_form(
                    step_id="tilt",
                    data_schema=TILT_OPTIONS.schema,
                    errors={
                        CONF_MAX_ELEVATION: "Must be greater than 'Minimal Elevation'"
                    },
                )
            self.options.update(user_input)
            return await self._update_options()
        return self.async_show_form(
            step_id="tilt",
            data_schema=schema,
        )

    async def async_step_interp(self, user_input: dict[str, Any] | None = None):
        """Show interpolation options."""
        if user_input is not None:
            if len(user_input[CONF_INTERP_LIST]) != len(
                user_input[CONF_INTERP_LIST_NEW]
            ):
                return self.async_show_form(
                    step_id="interp",
                    data_schema=INTERPOLATION_OPTIONS,
                    errors={
                        CONF_INTERP_LIST_NEW: "Must have same length as 'Interpolation' list"
                    },
                )
            self.options.update(user_input)
            return await self._update_options()
        return self.async_show_form(
            step_id="interp",
            data_schema=_get_interpolation_options_schema(self.options),
        )

    async def async_step_blind_spot(self, user_input: dict[str, Any] | None = None):
        """Add blindspot to data."""
        edges = _get_azimuth_edges(self.options)
        schema = vol.Schema(
            {
                vol.Required(CONF_BLIND_SPOT_LEFT, default=0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode="slider", unit_of_measurement="°", min=0, max=edges - 1
                    )
                ),
                vol.Required(CONF_BLIND_SPOT_RIGHT, default=1): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode="slider", unit_of_measurement="°", min=1, max=edges
                    )
                ),
                vol.Optional(CONF_BLIND_SPOT_ELEVATION): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=90, mode="slider")
                ),
            }
        )
        if user_input is not None:
            if user_input[CONF_BLIND_SPOT_RIGHT] <= user_input[CONF_BLIND_SPOT_LEFT]:
                return self.async_show_form(
                    step_id="blind_spot",
                    data_schema=schema,
                    errors={
                        CONF_BLIND_SPOT_RIGHT: "Must be greater than 'Blind Spot Left Edge'"
                    },
                )
            self.options.update(user_input)
            return await self._update_options()
        return self.async_show_form(
            step_id="blind_spot",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or self.options
            ),
        )

    async def _update_options(self) -> FlowResult:
        """Update config entry options."""
        return self.async_create_entry(title="", data=self.options)

    def optional_entities(self, keys: list, user_input: dict[str, Any] | None = None):
        """Set value to None if key does not exist."""
        for key in keys:
            if key not in user_input:
                user_input[key] = None
