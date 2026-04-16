"""Constants for the Panasonic Aquarea integration."""

DOMAIN = "panasonic_aquarea"
DEFAULT_NAME = "Panasonic Aquarea"
MANUFACTURER = "Panasonic"

# ─── API backend (accsmart.panasonic.com) ────────────────────────────────────
API_BASE_URL = "https://accsmart.panasonic.com"
API_DEVICES_PATH = "/device/group"
API_TRANSFER_PATH = "/remote/v1/app/common/transfer"

# Aquarea device-level sub-API called through the transfer proxy
API_DEVICE_STATUS_APINAME = "/remote/v1/api/devices?gwid={device_guid}&deviceDirect={direct}"
API_DEVICE_CONTROL_APINAME = "/remote/v1/api/devices/{device_guid}/status"

# ─── OAuth2 / Auth0 ───────────────────────────────────────────────────────────
AUTH_BASE_URL = "https://authglb.digital.panasonic.com"
AUTH_AUTHORIZE_PATH = "/authorize"
AUTH_LOGIN_PATH = "/usernamepassword/login"
AUTH_CALLBACK_PATH = "/login/callback"
AUTH_TOKEN_PATH = "/oauth/token"

APP_CLIENT_ID = "Xmy6xIYIitMxngjB2rHvlm6HSDNnaMJx"
APP_REDIRECT_URI = (
    "panasonic-iot-cfc://authglb.digital.panasonic.com"
    "/android/com.panasonic.ACCsmart/callback"
)
AUTH0_CLIENT_B64 = (
    "eyJuYW1lIjoiQXV0aDAuQW5kcm9pZCIsImVudiI6eyJhbmRyb2lkIjoiMzAifSwidmVyc2lvbiI6IjIuOS4zIn0="
)
OAUTH_SCOPE = "openid offline_access comfortcloud.control a2w.control"
OAUTH_AUDIENCE = "https://digital.panasonic.com/api/v2/"
OAUTH_TENANT = "pdpauthglb-a1"

# Panasonic client-ID endpoint (returns clientId after auth)
API_ACC_LOGIN_PATH = "/auth/v2/login"

# ─── HTTP Client ─────────────────────────────────────────────────────────────
API_USER_AGENT = "okhttp/4.10.0"
AUTH_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; K) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Mobile Safari/537.36"
)
API_APP_TYPE = "1"
API_APP_VERSION = "4.1.0"

# ─── Integration settings ────────────────────────────────────────────────────
DEFAULT_SCAN_INTERVAL = 60  # seconds

CONF_DEVICE_GUID = "device_guid"
CONF_DEVICE_NAME = "device_name"

COORDINATOR = "coordinator"
DEVICE_INFO = "device_info"

PLATFORMS = ["climate", "water_heater", "sensor", "switch"]

# ─── Operation Status ────────────────────────────────────────────────────────
OPERATION_STATUS_OFF = 0
OPERATION_STATUS_ON = 1

# ─── Operation Modes ─────────────────────────────────────────────────────────
OPERATION_MODE_HEAT = 0
OPERATION_MODE_COOL = 1
OPERATION_MODE_AUTO = 2
OPERATION_MODE_DHW = 3
OPERATION_MODE_HEAT_DHW = 4
OPERATION_MODE_COOL_DHW = 5
OPERATION_MODE_AUTO_DHW = 6

# ─── Zone Control Modes ───────────────────────────────────────────────────────
ZONE_CTRL_WATER_TEMP = 0
ZONE_CTRL_ROOM_TEMP = 1
ZONE_CTRL_COMPENSATION = 2

# ─── Tank / Switch flags ──────────────────────────────────────────────────────
TANK_BOOST_OFF = 0
TANK_BOOST_ON = 1
HOLIDAY_MODE_OFF = 0
HOLIDAY_MODE_ON = 1
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

# ─── Sensor keys ─────────────────────────────────────────────────────────────
ATTR_OUTDOOR_TEMP = "outdoor_temperature"
ATTR_OPERATION_MODE = "operation_mode"
ATTR_ERROR_STATUS = "error_status"
ATTR_ZONE_WATER_TEMP = "water_temperature"
ATTR_ZONE_ROOM_TEMP = "room_temperature"
ATTR_TANK_TEMP = "tank_temperature"
ATTR_FORCE_HEATER = "force_heater"
ATTR_HOLIDAY_MODE = "holiday_mode"
ATTR_TANK_BOOST = "tank_boost"
