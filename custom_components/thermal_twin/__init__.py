from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.util import dt as dt_util

from .const import *

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]
TICK_SECONDS = 15.0


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    conf = config.get(DOMAIN, {})
    model = ThermalTwinModel(hass, conf)
    hass.data[DOMAIN] = model

    await model.async_init()

    for platform in PLATFORMS:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, config)
        )
    return True


class ThermalTwinModel:
    def __init__(self, hass: HomeAssistant, conf: dict) -> None:
        self.hass = hass
        self.ch_entity = conf.get("ch_entity", DEFAULT_CH_BINARY)
        self.main_room_sensor = conf.get("main_room_sensor", DEFAULT_MAIN_ROOM_SENSOR)
        self.all_room_sensors = conf.get("all_room_sensors", DEFAULT_ALL_ROOM_SENSORS)

        self.target_retour: float = conf.get("target_retour", DEFAULT_TARGET_RETOUR)
        self.k_warm: float = conf.get("k_warm", DEFAULT_K_WARM)
        self.k_koel: float = conf.get("k_koel", DEFAULT_K_KOEL)
        self.k_rad: float = conf.get("k_rad", DEFAULT_K_RAD)

        self.aanvoer_offset: float = conf.get("aanvoer_offset", DEFAULT_AANVOER_OFFSET)
        self.ramp_seconds: float = conf.get("ramp_seconds", DEFAULT_RAMP_SECONDS)
        self.cooldown_room_seconds: float = conf.get(
            "cooldown_room_seconds", DEFAULT_COOLDOWN_ROOM_SECONDS
        )

        self.gas_m3_per_min: float = conf.get("gas_m3_per_min", DEFAULT_GAS_M3_PER_MIN)
        self.gas_start_m3: float = conf.get("gas_start_m3", DEFAULT_GAS_START_M3)
        self.gas_kwh_per_m3: float = conf.get("gas_kwh_per_m3", DEFAULT_GAS_KWH_PER_M3)

        self.radiators: list[dict] = [
            dict(r) for r in conf.get("radiators", DEFAULT_RADIATORS)
        ]

        self.t_retour_virt: float | None = None
        self.t_aanvoer_virt: float | None = None
        self.t_rad_offset: float = 0.0
        self.t_rad_virt: float | None = None
        self._prev_t_rad_virt: float | None = None
        self._initialized: bool = False
        self._prev_ch_actief: bool = False

        self.instant_efficiency_pct: float = 0.0
        self.boiler_output_kw: float = 0.0
        self.gas_input_kw: float = 0.0

        self.total_heat_output_kwh: float = 0.0
        self.total_gas_input_kwh: float = 0.0
        self.total_gas_m3: float = 0.0
        self.ch_starts: int = 0

        self._listeners = []

    async def async_init(self) -> None:
        async_track_time_interval(
            self.hass, self._async_tick, timedelta(seconds=TICK_SECONDS)
        )

    def register_listener(self, cb) -> None:
        self._listeners.append(cb)

    def sync_buffer_baseline(self) -> None:
        self._prev_t_rad_virt = self.t_rad_virt

    def _get_float(self, entity_id: str, default: float = 20.0) -> float:
        state = self.hass.states.get(entity_id)
        if state and state.state not in ("unknown", "unavailable", "none"):
            try:
                return float(state.state)
            except ValueError:
                pass
        return default

    @callback
    def _async_tick(self, now=None) -> None:
        self.recalculate()
        for cb in self._listeners:
            cb()

    def get_system_capacitance(self) -> float:
        """Constante thermische capaciteit C_systeem (kWh/°C)."""
        if self.k_koel <= 0:
            return 0.0
        som_q_nom = sum(r.get("q_nom_kw", 0.0) for r in self.radiators)
        ticks_per_hour = 3600.0 / TICK_SECONDS
        return som_q_nom / (50.0 * self.k_koel * ticks_per_hour)

    def recalculate(self) -> None:
        t_room = self._get_float(self.main_room_sensor, 20.0)
        ch_state = self.hass.states.get(self.ch_entity)
        ch_actief = ch_state is not None and ch_state.state == "on"

        if self.t_retour_virt is None:
            self.t_retour_virt = t_room
        if self.t_aanvoer_virt is None:
            self.t_aanvoer_virt = t_room
        if self.t_rad_virt is None:
            self.t_rad_virt = t_room
        if self._prev_t_rad_virt is None:
            self._prev_t_rad_virt = self.t_rad_virt

        if not self._initialized:
            self._prev_ch_actief = ch_actief
            self._prev_t_rad_virt = self.t_rad_virt
            self._initialized = True

        if ch_actief and not self._prev_ch_actief:
            self.ch_starts += 1
            self.total_gas_m3 += self.gas_start_m3
            self.total_gas_input_kwh += self.gas_start_m3 * self.gas_kwh_per_m3
        self._prev_ch_actief = ch_actief

        kamer_temps = [self._get_float(s, t_room) for s in self.all_room_sensors]
        t_min_room = min(kamer_temps) if kamer_temps else t_room

        if ch_state and ch_state.last_changed:
            t_sinds_wissel = (dt_util.utcnow() - ch_state.last_changed).total_seconds()
        else:
            t_sinds_wissel = 9999.0

        weighted_bubble = self.get_weighted_bubble_factor()
        bubble_retour_shift = max(0.0, self.t_rad_virt - t_room) * weighted_bubble * 0.5
        effective_target = self.target_retour + bubble_retour_shift
        ramp = self.ramp_seconds

        # 1. VIRTUELE RETOURTEMPERATUUR
        curr = self.t_retour_virt
        if ch_actief and t_sinds_wissel <= ramp:
            self.t_retour_virt = curr - (curr - t_room) * self.k_koel
        elif ch_actief:
            self.t_retour_virt = curr + (effective_target + t_room - curr) * self.k_warm
        elif not ch_actief and t_sinds_wissel <= ramp:
            self.t_retour_virt = curr + (effective_target + t_room - curr) * self.k_warm
        elif not ch_actief and t_sinds_wissel <= self.cooldown_room_seconds:
            self.t_retour_virt = curr - (curr - t_room) * self.k_koel
        else:
            self.t_retour_virt = curr - (curr - t_min_room) * self.k_koel

        # 2. VIRTUELE AANVOERTEMPERATUUR
        if ch_actief and t_sinds_wissel <= ramp:
            offset_aanvoer = self.aanvoer_offset * (t_sinds_wissel / ramp)
            self.t_aanvoer_virt = self.t_retour_virt + offset_aanvoer
        elif ch_actief:
            self.t_aanvoer_virt = self.t_retour_virt + self.aanvoer_offset
        elif not ch_actief and t_sinds_wissel <= ramp:
            offset_aanvoer = self.aanvoer_offset * (1.0 - (t_sinds_wissel / ramp))
            self.t_aanvoer_virt = self.t_retour_virt + offset_aanvoer
        else:
            self.t_aanvoer_virt = self.t_retour_virt

        # 3. VIRTUELE RADIATORTEMPERATUUR
        offset_doel = (self.t_aanvoer_virt - self.t_retour_virt) / 2.0
        self.t_rad_offset = self.t_rad_offset + (offset_doel - self.t_rad_offset) * self.k_rad
        self.t_rad_virt = self.t_retour_virt + self.t_rad_offset

        # 4. BUFFER HEAT, POWER, GAS & EFFICIENCY
        hours_per_tick = TICK_SECONDS / 3600.0
        ticks_per_hour = 3600.0 / TICK_SECONDS
        p_rad_kw = self.get_total_power_kw()

        self.total_heat_output_kwh += p_rad_kw * hours_per_tick

        if ch_actief:
            gas_m3_tick = self.gas_m3_per_min * (TICK_SECONDS / 60.0)
            self.total_gas_m3 += gas_m3_tick
            self.total_gas_input_kwh += gas_m3_tick * self.gas_kwh_per_m3

            p_gas_kw = self.gas_m3_per_min * 60.0 * self.gas_kwh_per_m3
            c_systeem = self.get_system_capacitance()
            dt_rad = self.t_rad_virt - self._prev_t_rad_virt
            p_buffer_kw = c_systeem * dt_rad * ticks_per_hour
            p_boiler_kw = max(0.0, p_rad_kw + p_buffer_kw)

            self.gas_input_kw = round(p_gas_kw, 3)
            self.boiler_output_kw = round(p_boiler_kw, 3)

            if p_gas_kw > 0:
                eff = (p_boiler_kw / p_gas_kw) * 100.0
                self.instant_efficiency_pct = round(max(0.0, eff), 1)
        else:
            self.gas_input_kw = 0.0
            self.boiler_output_kw = 0.0

        self._prev_t_rad_virt = self.t_rad_virt

    def get_weighted_bubble_factor(self) -> float:
        som_gewogen = 0.0
        som_q = 0.0
        for rad in self.radiators:
            q = rad.get("q_nom_kw", 0.0)
            f = rad.get("bubble_factor", 0.15)
            som_gewogen += q * f
            som_q += q
        return round(som_gewogen / som_q, 3) if som_q > 0 else 0.15

    def get_radiator_power_kw(self, rad: dict) -> float:
        if self.t_rad_virt is None:
            return 0.0
        t_room = self._get_float(rad["room_sensor"], 20.0)
        if self.t_rad_virt <= t_room:
            return 0.0

        bubble_factor = rad.get("bubble_factor", 0.15)
        t_room_eff = t_room + ((self.t_rad_virt - t_room) * bubble_factor)
        dt = max(0.0, self.t_rad_virt - t_room_eff)

        q_nom = rad.get("q_nom_kw", 1.0)
        exp = rad.get("exponent", 1.30)
        return round(q_nom * ((dt / 50.0) ** exp), 4)

    def get_total_power_kw(self) -> float:
        return round(sum(self.get_radiator_power_kw(r) for r in self.radiators), 4)

    def get_buffer_heat_kwh(self) -> float:
        if self.t_rad_virt is None:
            return 0.0
        t_room = self._get_float(self.main_room_sensor, 20.0)
        dt_systeem = self.t_rad_virt - t_room
        if dt_systeem <= 0.0:
            return 0.0
        return round(self.get_system_capacitance() * dt_systeem, 4)

    def get_system_efficiency_pct(self) -> float:
        if self.total_gas_input_kwh <= 0.01:
            return 0.0
        nuttige_warmte = self.total_heat_output_kwh + self.get_buffer_heat_kwh()
        return round((nuttige_warmte / self.total_gas_input_kwh) * 100.0, 1)
