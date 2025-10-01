"""Renogy sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)

OUTPUT_MODES = {
    0: "Eco",
    1: "Normal",
    2: "Eco",
}
BATTERY_TYPE = {
    0: "User Defined",
    1: "Flooded",
    2: "Gel",
    3: "AGM",
    4: "Lithium",
}
FILTER_UNITS = ["℃", "KWh", "AH"]
CONNECTION_TYPE = {
    "Bluetooth": "mdi:bluetooth",
    "Zigbee": "mdi:zigbee",
    "RVC": "mdi:cable-data",
    "RS485": "mdi:serial-port",
    "RS232": "mdi:serial-port",
    "Ethernet": "mdi:ethernet-cable",
    "Wifi": "mdi:wifi",
    "CANBUS": "mdi:cable-data",
    "Mesh": "mdi:hubspot",
    "Hub": "mdi:hub",
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the OpenEVSE sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    sensors = []
    for device_id, device in coordinator.data.items():
        for sensor in SENSOR_TYPES:  # pylint: disable=consider-using-dict-items
            if sensor in device.keys():  # pylint: disable=consider-using-dict-items
                sensors.append(
                    RenogySensor(SENSOR_TYPES[sensor], device_id, coordinator, entry)
                )
            if sensor in device["data"].keys():
                sensors.append(
                    RenogySensor(SENSOR_TYPES[sensor], device_id, coordinator, entry)
                )

    async_add_entities(sensors, False)


class RenogySensor(CoordinatorEntity, SensorEntity):
    """Implementation of an OpenEVSE sensor."""

    def __init__(
        self,
        sensor_description: SensorEntityDescription,
        device_id: str,
        coordinator: str,
        config: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._config = config
        self.entity_description = sensor_description
        self._name = sensor_description.name
        self._type = sensor_description.key
        self.unit = sensor_description.native_unit_of_measurement
        self._data = coordinator.data
        self.coordinator = coordinator
        self._state = None

        self._attr_icon = sensor_description.icon
        self._attr_name = f"{coordinator.data[device_id]["name"]} {self._name}"
        self._attr_unique_id = f"{self._name}_{device_id}"

    @property
    def device_info(self) -> dict:
        """Return a port description for device registry."""
        info = {
            "identifiers": {(DOMAIN, self._device_id)},
        }
        return info

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self._type in self.coordinator.data[self._device_id]:
            self.update_icon()
            return self.coordinator.data[self._device_id][self._type]

        data = self.coordinator.data[self._device_id]["data"]
        if data is None:
            self._state = None
        if self._type in data.keys():
            if self._type == "output":
                try:
                    value = OUTPUT_MODES[data[self._type][0]]
                except KeyError:
                    value = None
            elif self._type == "batteryType" and isinstance(data[self._type][0], int):
                try:
                    value = BATTERY_TYPE[data[self._type][0]]
                except KeyError:
                    value = None
            else:
                value = data[self._type][0]
            self._state = value
        _LOGGER.debug("Sensor [%s] updated value: %s", self._type, self._state)
        return self._state

    @property
    def native_unit_of_measurement(self) -> Any:
        """Return the unit of measurement."""
        data = self.coordinator.data[self._device_id]["data"]
        if not data or self._type not in data:
            return self.unit

        if not isinstance(data[self._type], tuple):
            return self.unit

        if data[self._type][1] in FILTER_UNITS:
            return self.unit

        if data[self._type][1] == "":
            if self.unit is None:
                return None
            return self.unit

        return data[self._type][1]

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        data = self.coordinator.data[self._device_id]
        return self._type not in data or (
            self._type in data and data[self._type] is not None
        )

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    def update_icon(self) -> None:
        """Update connection type icon."""
        connection = self.coordinator.data[self._device_id][self._type]
        self._attr_icon = CONNECTION_TYPE[connection]
