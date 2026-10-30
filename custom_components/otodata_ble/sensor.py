"""Sensors for Otodata tank monitors."""

from dataclasses import replace

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_CAPACITY, DOMAIN, MANUFACTURER
from .coordinator import OtodataConfigEntry, OtodataUpdate

_LEVEL = SensorEntityDescription(
    key="tank_level",
    translation_key="tank_level",
    native_unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=2,
)
_SIGNAL_STRENGTH = SensorEntityDescription(
    key="signal_strength",
    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
    native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
)
# The unit comes from the options.
_FUEL_REMAINING = SensorEntityDescription(
    key="fuel_remaining",
    translation_key="fuel_remaining",
    device_class=SensorDeviceClass.VOLUME_STORAGE,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=1,
)

_LEVEL_KEY = PassiveBluetoothEntityKey(_LEVEL.key, None)
_SIGNAL_STRENGTH_KEY = PassiveBluetoothEntityKey(_SIGNAL_STRENGTH.key, None)

type _Processor = PassiveBluetoothDataProcessor[float, OtodataUpdate | None]


def _to_data_update(
    device_info: DeviceInfo, update: OtodataUpdate | None
) -> PassiveBluetoothDataUpdate[float]:
    """Map an Otodata update to sensor values."""
    if update is None:
        return PassiveBluetoothDataUpdate()
    data_update = PassiveBluetoothDataUpdate(
        devices={None: device_info},
        entity_descriptions={_SIGNAL_STRENGTH_KEY: _SIGNAL_STRENGTH},
        entity_data={_SIGNAL_STRENGTH_KEY: update.rssi},
    )
    if update.telemetry is not None:
        data_update.entity_descriptions[_LEVEL_KEY] = _LEVEL
        data_update.entity_data[_LEVEL_KEY] = update.telemetry.level
    return data_update


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OtodataConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Otodata sensors."""
    # The model and serial are added to the device separately; see
    # async_update_device_info.
    device_info = DeviceInfo(name=entry.title, manufacturer=MANUFACTURER)
    processor: _Processor = PassiveBluetoothDataProcessor(
        lambda update: _to_data_update(device_info, update)
    )
    entry.async_on_unload(
        processor.async_add_entities_listener(OtodataSensor, async_add_entities)
    )
    _async_setup_fuel_remaining(hass, entry, processor, async_add_entities)
    # Restores the last values, so the sensors aren't empty until the next
    # broadcast after a restart or reload.
    entry.async_on_unload(
        entry.runtime_data.async_register_processor(processor, SensorEntityDescription)
    )


def _async_setup_fuel_remaining(
    hass: HomeAssistant,
    entry: OtodataConfigEntry,
    processor: _Processor,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the fuel remaining sensor along with the level, if a capacity is set."""
    if (capacity := entry.options.get(CONF_CAPACITY)) is None:
        # Remove the sensor left over from when a capacity was set.
        registry = er.async_get(hass)
        unique_id = f"{entry.unique_id}-{_FUEL_REMAINING.key}"
        if entity_id := registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, unique_id
        ):
            registry.async_remove(entity_id)
        return

    description = replace(
        _FUEL_REMAINING,
        native_unit_of_measurement=entry.options[CONF_UNIT_OF_MEASUREMENT],
    )
    added = False

    @callback
    def _async_add(_data: PassiveBluetoothDataUpdate[float] | None) -> None:
        nonlocal added
        if added or _LEVEL_KEY not in processor.entity_descriptions:
            return
        added = True
        async_add_entities([OtodataFuelSensor(processor, description, capacity)])

    entry.async_on_unload(processor.async_add_listener(_async_add))


class OtodataSensor(PassiveBluetoothProcessorEntity[_Processor], SensorEntity):
    """An Otodata sensor."""

    @property
    def native_value(self) -> float | None:
        """Return the latest value."""
        return self.processor.entity_data.get(self.entity_key)


class OtodataFuelSensor(OtodataSensor):
    """Fuel remaining, worked out from the tank level and capacity."""

    def __init__(
        self,
        processor: _Processor,
        description: SensorEntityDescription,
        capacity: float,
    ) -> None:
        """Follow the level sensor's data under this sensor's own unique ID."""
        super().__init__(processor, _LEVEL_KEY, description)
        self._attr_unique_id = f"{processor.coordinator.address}-{description.key}"
        self._capacity = capacity

    @property
    def native_value(self) -> float:
        """Return the fuel remaining."""
        # Only added once there is a level.
        return self._capacity * self.processor.entity_data[_LEVEL_KEY] / 100
