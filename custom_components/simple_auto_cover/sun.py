"""Fetch sun data."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_location


class SunData:
    """Access local sun data."""

    def __init__(self, timezone, hass: HomeAssistant) -> None:  # noqa: D107
        self.hass = hass
        location, elevation = get_astral_location(self.hass)
        self.location = location  # astral.location.Location
        self.elevation = elevation
        self.timezone = ZoneInfo(str(timezone))

    @property
    def times(self) -> list[datetime]:
        """Return 5 minute intervals from midnight today to tomorrow."""
        start_date = date.today()
        end_date = start_date + timedelta(days=1)
        start_time = datetime.combine(
            start_date, datetime.min.time(), tzinfo=self.timezone
        )
        end_time = datetime.combine(end_date, datetime.min.time(), tzinfo=self.timezone)

        times = []
        current_time = start_time
        while current_time <= end_time:
            times.append(current_time)
            current_time += timedelta(minutes=5)
        return times

    @property
    def solar_azimuth(self) -> list:
        """Create list with solar azimuth data per 5 minutes."""
        return [
            self.location.solar_azimuth(time, self.elevation) for time in self.times
        ]

    @property
    def solar_elevation(self) -> list:
        """Create list with solar elevation data per 5 minutes."""
        return [
            self.location.solar_elevation(time, self.elevation) for time in self.times
        ]

    def sunset(self) -> datetime:
        """Fetch sunset time."""
        return self.location.sunset(date.today(), local=False)

    def sunrise(self) -> datetime:
        """Fetch sunrise time."""
        return self.location.sunrise(date.today(), local=False)

    # def df_today(self)-> pd.DataFrame:
    #     """Create dataframe with azimuth and elevation data"""
    #     df_today = pd.DataFrame({"azimuth":self.solar_azimuth, "elevation":self.solar_elevation})
    #     df_today = df_today.set_index(self.times)
    #     return df_today
