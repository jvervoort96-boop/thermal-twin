from __future__ import annotations
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower, UnitOfTemperature, UnitOfVolume
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    model = hass.data[DOMAIN]
    entities = [
        VirtueleRetourSensor(model),
        VirtueleAanvoerSensor(model),
        VirtueleRadSensor(model),
        GewogenWarmtebelSensor(model),
        TotaalVermogenSensor(model),
        BufferWarmteSensor(model),
        CumulatieveWarmteSensor(model),
        CumulatiefGasKwhSensor(model),
        CumulatiefGasM3Sensor(model),
        SysteemRendementSensor(model),
        ActueelStookrendementSensor(model),
    ]
    for rad in model.radiators:
        entities.append(KamerVermogenSensor(model, rad))

    async_add_entities(entities)


class BaseModelSensor(SensorEntity):
    def __init__(self, model):
        self.model = model
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "thermal_twin_device")},
            name="Thermal Twin",
            manufacturer="Custom",
            model="EN 442 Dynamic Model",
        )

    async def async_added_to_hass(self):
        self.model.register_listener(self.async_write_ha_state)


class BaseRestoreModelSensor(RestoreSensor):
    def __init__(self, model, model_attr: str):
        self.model = model
        self.model_attr = model_attr
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "thermal_twin_device")},
            name="Thermal Twin",
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) and last_data.native_value is not None:
            try:
                setattr(self.model, self.model_attr, float(last_data.native_value))
            except ValueError:
                pass
        self.model.register_listener(self.async_write_ha_state)


class VirtueleRetourSensor(BaseModelSensor):
    _attr_name = "Virtuele Retourtemperatuur"
    _attr_unique_id = "thermal_twin_virtuele_retourtemperatuur"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return round(self.model.t_retour_virt, 3)


class VirtueleAanvoerSensor(BaseModelSensor):
    _attr_name = "Virtuele Aanvoertemperatuur"
    _attr_unique_id = "thermal_twin_virtuele_aanvoertemperatuur"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return round(self.model.t_aanvoer_virt, 3)


class VirtueleRadSensor(BaseModelSensor):
    _attr_name = "Virtuele Radiatortemperatuur"
    _attr_unique_id = "thermal_twin_virtuele_radiator_temperatuur"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return round(self.model.t_rad_virt, 3)

    @property
    def extra_state_attributes(self):
        return {"offset": round(self.model.t_rad_offset, 4)}


class GewogenWarmtebelSensor(BaseModelSensor):
    _attr_name = "Gewogen Warmtebelfactor"
    _attr_unique_id = "thermal_twin_gewogen_warmtebelfactor"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.model.get_weighted_bubble_factor()


class TotaalVermogenSensor(BaseModelSensor):
    _attr_name = "Totaal Radiatorvermogen"
    _attr_unique_id = "thermal_twin_totaal_radiatorvermogen"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.model.get_total_power_kw()


class KamerVermogenSensor(BaseModelSensor):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, model, rad: dict):
        super().__init__(model)
        self.rad = rad
        self._attr_name = f"{rad['name']} Radiatorvermogen"
        self._attr_unique_id = f"thermal_twin_{rad['id']}_radiatorvermogen"

    @property
    def native_value(self):
        return self.model.get_radiator_power_kw(self.rad)


class BufferWarmteSensor(BaseModelSensor):
    _attr_name = "CV Bufferwarmte"
    _attr_unique_id = "thermal_twin_cv_bufferwarmte"
    _attr_device_class = SensorDeviceClass.ENERGY_STORAGE
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.model.get_buffer_heat_kwh()


class CumulatieveWarmteSensor(BaseRestoreModelSensor):
    _attr_name = "Totaal Afgegeven Warmte"
    _attr_unique_id = "thermal_twin_totaal_afgegeven_warmte"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, model):
        super().__init__(model, "total_heat_output_kwh")

    @property
    def native_value(self):
        return round(self.model.total_heat_output_kwh, 3)


class CumulatiefGasKwhSensor(BaseRestoreModelSensor):
    _attr_name = "Totaal Gasenergie Input"
    _attr_unique_id = "thermal_twin_totaal_gasenergie_input"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, model):
        super().__init__(model, "total_gas_input_kwh")

    @property
    def native_value(self):
        return round(self.model.total_gas_input_kwh, 3)


class CumulatiefGasM3Sensor(BaseRestoreModelSensor):
    _attr_name = "Totaal Virtueel Gasverbruik"
    _attr_unique_id = "thermal_twin_totaal_virtueel_gasverbruik"
    _attr_device_class = SensorDeviceClass.GAS
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, model):
        super().__init__(model, "total_gas_m3")

    @property
    def native_value(self):
        return round(self.model.total_gas_m3, 3)

    @property
    def extra_state_attributes(self):
        return {"aantal_starts": self.model.ch_starts}


class SysteemRendementSensor(BaseModelSensor):
    _attr_name = "CV Systeemrendement"
    _attr_unique_id = "thermal_twin_cv_systeemrendement"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.model.get_system_efficiency_pct()


class ActueelStookrendementSensor(BaseRestoreModelSensor):
    _attr_name = "CV Actueel Stookrendement"
    _attr_unique_id = "thermal_twin_cv_actueel_stookrendement"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, model):
        super().__init__(model, "instant_efficiency_pct")

    @property
    def native_value(self):
        return self.model.instant_efficiency_pct
