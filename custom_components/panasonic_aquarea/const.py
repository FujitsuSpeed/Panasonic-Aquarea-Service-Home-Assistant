"""Constants for the Panasonic Aquarea integration."""

DOMAIN = "panasonic_aquarea"
DEFAULT_NAME = "Panasonic Aquarea"
MANUFACTURER = "Panasonic"

# API
API_BASE_URL = "https://aquarea-service.panasonic.com"
API_LOGIN_PATH = "/remote/v1/api/auth/login"
API_DEVICES_PATH = "/remote/v1/api/devices"
API_DEVICE_STATUS_PATH = "/remote/v1/api/devices/{device_guid}/status"

# Headers
API_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
API_APP_TYPE = "2"

# Update interval in seconds
DEFAULT_SCAN_INTERVAL = 60

# Config / entry keys
CONF_DEVICE_GUID = "device_guid"
CONF_DEVICE_NAME = "device_name"

# Coordinator key
COORDINATOR = "coordinator"
DEVICE_INFO = "device_info"

# Platforms
PLATFORMS = ["climate", "water_heater", "sensor", "switch"]

# ─── Operation Status ───────────────────────────────────────────────────────
OPERATION_STATUS_OFF = 0
OPERATION_STATUS_ON = 1

# ─── Operation Modes ────────────────────────────────────────────────────────
OPERATION_MODE_HEAT = 0
OPERATION_MODE_COOL = 1
OPERATION_MODE_AUTO = 2
OPERATION_MODE_DHW = 3       # Hot water only
OPERATION_MODE_HEAT_DHW = 4  # Heat + hot water
OPERATION_MODE_COOL_DHW = 5  # Cool + hot water
OPERATION_MODE_AUTO_DHW = 6  # Auto + hot water

HA_MODE_TO_AQUAREA = {
    "heat": OPERATION_MODE_HEAT,
    "cool": OPERATION_MODE_COOL,
    "auto": OPERATION_MODE_AUTO,
    "heat_dhw": OPERATION_MODE_HEAT_DHW,
    "cool_dhw": OPERATION_MODE_COOL_DHW,
    "auto_dhw": OPERATION_MODE_AUTO_DHW,
}

AQUAREA_MODE_TO_HA = {v: k for k, v in HA_MODE_TO_AQUAREA.items()}

# ─── Zone Heat/Cool Control Mode ────────────────────────────────────────────
ZONE_CTRL_WATER_TEMP = 0     # Water temperature setpoint
ZONE_CTRL_ROOM_TEMP = 1      # Room temperature setpoint
ZONE_CTRL_COMPENSATION = 2   # Compensation curve

# ─── Tank Boost ──────────────────────────────────────────────────────────────
TANK_BOOST_OFF = 0
TANK_BOOST_ON = 1

# ─── Holiday / Away Mode ─────────────────────────────────────────────────────
HOLIDAY_MODE_OFF = 0
HOLIDAY_MODE_ON = 1

# ─── Force Heater ────────────────────────────────────────────────────────────
FORCE_HEATER_OFF = 0
FORCE_HEATER_ON = 1

# ─── Temperature limits (°C) ─────────────────────────────────────────────────
ZONE_HEAT_TEMP_MIN = 20.0
ZONE_HEAT_TEMP_MAX = 60.0
ZONE_COOL_TEMP_MIN = 5.0
ZONE_COOL_TEMP_MAX = 25.0
ZONE_ROOM_HEAT_TEMP_MIN = 10.0
ZONE_ROOM_HEAT_TEMP_MAX = 30.0
ZONE_ROOM_COOL_TEMP_MIN = 15.0
ZONE_ROOM_COOL_TEMP_MAX = 35.0
TANK_TEMP_MIN = 40.0
TANK_TEMP_MAX = 75.0

# ─── Sensor / entity attribute keys ──────────────────────────────────────────
ATTR_OUTDOOR_TEMP = "outdoor_temperature"
ATTR_OPERATION_MODE = "operation_mode"
ATTR_ERROR_STATUS = "error_status"
ATTR_ZONE_WATER_TEMP = "water_temperature"
ATTR_ZONE_ROOM_TEMP = "room_temperature"
ATTR_TANK_TEMP = "tank_temperature"
ATTR_FORCE_HEATER = "force_heater"
ATTR_HOLIDAY_MODE = "holiday_mode"
ATTR_TANK_BOOST = "tank_boost"
