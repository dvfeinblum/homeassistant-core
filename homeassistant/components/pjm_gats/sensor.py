"""PJM GATS sensor platform."""

from dataclasses import dataclass
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import PjmGatsConfigEntry, PjmGatsDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class PjmGatsSensorDescription(SensorEntityDescription):
    """Describes a PJM GATS sensor."""

    data_key: str


SENSORS: tuple[PjmGatsSensorDescription, ...] = (
    PjmGatsSensorDescription(
        key="generation_mwh",
        data_key="generation_mwh",
        name="Generation",
        native_unit_of_measurement=UnitOfEnergy.MEGA_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    PjmGatsSensorDescription(
        key="certificates_active",
        data_key="certificates_active",
        name="Certificates Active",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PjmGatsSensorDescription(
        key="certificates_ceps",
        data_key="certificates_ceps",
        name="Certificates CEPS",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PjmGatsSensorDescription(
        key="certificates_on_bb",
        data_key="certificates_on_bb",
        name="Certificates On Bulletin Board",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PjmGatsSensorDescription(
        key="certificates_reserved",
        data_key="certificates_reserved",
        name="Certificates Reserved",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PjmGatsSensorDescription(
        key="certificates_total",
        data_key="certificates_total",
        name="Certificates Total",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PjmGatsSensorDescription(
        key="certificates_active_hourly",
        data_key="certificates_active_hourly",
        name="Certificates Active Hourly",
        native_unit_of_measurement=UnitOfEnergy.MEGA_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PjmGatsSensorDescription(
        key="certificates_ceps_hourly",
        data_key="certificates_ceps_hourly",
        name="Certificates CEPS Hourly",
        native_unit_of_measurement=UnitOfEnergy.MEGA_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PjmGatsSensorDescription(
        key="certificates_reserved_hourly",
        data_key="certificates_reserved_hourly",
        name="Certificates Reserved Hourly",
        native_unit_of_measurement=UnitOfEnergy.MEGA_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PjmGatsSensorDescription(
        key="generator_id",
        data_key="generator_id",
        name="Generator ID",
    ),
    PjmGatsSensorDescription(
        key="generator_plant",
        data_key="generator_plant",
        name="Generator Plant",
    ),
    PjmGatsSensorDescription(
        key="generator_status",
        data_key="generator_status",
        name="Generator Status",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PjmGatsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up PJM GATS sensors."""
    coordinator = entry.runtime_data

    entities = [PjmGatsSensor(coordinator, description) for description in SENSORS]
    async_add_entities(entities)


class PjmGatsSensor(CoordinatorEntity, SensorEntity):
    """Representation of a PJM GATS sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PjmGatsDataUpdateCoordinator,
        description: PjmGatsSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        # No clue why this type hint is required here
        self.entity_description: PjmGatsSensorDescription = description
        self._attr_unique_id = f"{coordinator.client.username}_{description.key}"

    @property
    @override
    def native_value(self) -> StateType:
        """Return the state of the sensor."""

        return self.coordinator.data.get(self.entity_description.data_key)
