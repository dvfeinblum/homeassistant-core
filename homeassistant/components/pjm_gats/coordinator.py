"""Coordinator for PJM GATS devices."""

from datetime import timedelta
import logging
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PjmGatsApiError, PjmGatsClient
from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


type PjmGatsConfigEntry = ConfigEntry[PjmGatsDataUpdateCoordinator]


class PjmGatsDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Class to manage fetching PJM GATS data."""

    def __init__(self, hass: HomeAssistant, client: PjmGatsClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),
        )
        self.client = client

    @override
    async def _async_update_data(self) -> dict:
        """Fetch data from PJM GATS."""
        try:
            return await self.hass.async_add_executor_job(
                self.client.get_home_page_data
            )
        except PjmGatsApiError as err:
            raise UpdateFailed(f"Error communicating with PJM GATS: {err}") from err
