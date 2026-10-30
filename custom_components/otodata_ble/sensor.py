"""Sensors for Otodata tank monitors."""

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
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MANUFACTURER
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
    hass: HomeAssistant,  # noqa: ARG001
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
    entry.async_on_unload(entry.runtime_data.async_register_processor(processor))


class OtodataSensor(PassiveBluetoothProcessorEntity[_Processor], SensorEntity):
    """An Otodata sensor."""

    @property
    def native_value(self) -> float | None:
        """Return the latest value."""
        return self.processor.entity_data.get(self.entity_key)
