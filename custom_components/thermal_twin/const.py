DOMAIN = "thermal_twin"

# Primary sensors
DEFAULT_CH_BINARY = "binary_sensor.opentherm_gateway_otgw_otgw_central_heating"
DEFAULT_MAIN_ROOM_SENSOR = "sensor.opentherm_gateway_otgw_otgw_room_temperature"

DEFAULT_ALL_ROOM_SENSORS = [
    "sensor.opentherm_gateway_otgw_otgw_room_temperature",
    "sensor.atc_4148_temperature",
    "sensor.atc_721a_temperature",
    "sensor.atc_6886_temperature",
    "sensor.atc_69ba_temperature",
    "sensor.atc_7954_temperature",
    "sensor.atc_a8e9_temperature",
]

# Calibration constants and time thresholds
DEFAULT_TARGET_RETOUR = 29.0
DEFAULT_K_WARM = 0.007
DEFAULT_K_KOEL = 0.005
DEFAULT_K_RAD = 0.018

DEFAULT_AANVOER_OFFSET = 10.0           # °C above return during active heating
DEFAULT_RAMP_SECONDS = 60.0             # Dead time / ramp duration on start & stop (s)
DEFAULT_COOLDOWN_ROOM_SECONDS = 3600.0  # Threshold before cooling toward t_min_room (s)

# Gas consumption and energy constants
DEFAULT_GAS_M3_PER_MIN = 0.0165         # Average gas consumption while firing (m³/min)
DEFAULT_GAS_START_M3 = 0.00833            # Extra gas consumption per burner start (m³)
DEFAULT_GAS_KWH_PER_M3 = 9.77           # 9.77 kWh/m³ (GCV / bovenwaarde) or 8.8 (NCV / onderwaarde)

# Alle 7 ruimtes met exacte nominale vermogens (incl. leidingen) en exponenten
DEFAULT_RADIATORS = [
    {
        "id": "woonkamer",
        "name": "Woonkamer",
        "q_nom_kw": 5.178,  # Achter (2.061) + Voor (2.717) + Leiding 10m (0.400)
        "room_sensor": "sensor.opentherm_gateway_otgw_otgw_room_temperature",
        "exponent": 1.29,
        "bubble_factor": 0.16,
    },
    {
        "id": "gang",
        "name": "Gang",
        "q_nom_kw": 1.797,  # Radiator (1.749) + Leiding 1.2m (0.048)
        "room_sensor": "sensor.atc_4148_temperature",
        "exponent": 1.29,
        "bubble_factor": 0.05,
    },
    {
        "id": "babykamer",
        "name": "Babykamer",
        "q_nom_kw": 1.070,  # Radiator (0.830) + Leiding 6m (0.240)
        "room_sensor": "sensor.atc_721a_temperature",
        "exponent": 1.26,
        "bubble_factor": 0.22,
    },
    {
        "id": "slaapkamer",
        "name": "Slaapkamer",
        "q_nom_kw": 1.257,  # Radiator (1.245) + Leiding 0.3m (0.012)
        "room_sensor": "sensor.atc_6886_temperature",
        "exponent": 1.26,
        "bubble_factor": 0.22,
    },
    {
        "id": "kantoor",
        "name": "Kantoor",
        "q_nom_kw": 1.900,  # Radiator (1.660) + Leiding 6m (0.240)
        "room_sensor": "sensor.atc_69ba_temperature",
        "exponent": 1.26,
        "bubble_factor": 0.22,
    },
    {
        "id": "badkamer",
        "name": "Badkamer",
        "q_nom_kw": 0.816,  # Radiator (0.800) + Leiding 0.4m (0.016)
        "room_sensor": "sensor.atc_7954_temperature",
        "exponent": 1.24,
        "bubble_factor": 0.32,
    },
    {
        "id": "voorzolder",
        "name": "Voorzolder",
        "q_nom_kw": 0.365,  # Leiding 2m ongeïsoleerd (0.080) + 26m geïsoleerd (0.195) + Ketel (0.090)
        "room_sensor": "sensor.atc_a8e9_temperature",
        "exponent": 1.08,
        "bubble_factor": 0.00,
    },
]
