"""Constants for Indego integration."""
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

DOMAIN = "indego"
DATA_UPDATED = f"{DOMAIN}_data_updated"
CONF_ATTR = "attributes"
CONF_DOWNLAD_MAP = "filename"

CONF_SEND_COMMAND = "command"
CONF_SMARTMOWING = "enable"
DEFAULT_NAME = "Indego"
DEFAULT_NAME_COMMANDS = None
DEFAULT_MAP_NAME = "indego_map"

SERVICE_NAME_COMMAND = "command"
SERVICE_NAME_SMARTMOW = "smartmowing"
SERVICE_NAME_DOWNLOAD_MAP = "download_map"

PLATFORMS = [SENSOR_DOMAIN]

ATTR_STATE_ID = "state_id"
ATTR_DISCHARGE = "discharge"
ATTR_CYCLES = "cycles"
ATTR_BATTERY_TEMP = "battery_temp"
ATTR_AMBIENT_TEMP = "ambient_temp"
ATTR_LAST_SESSION_OPERATION_MIN = "last_session_operation_min"
ATTR_LAST_SESSION_CUT_MIN = "last_session_cut_min"
ATTR_LAST_SESSION_CHARGE_MIN = "last_session_charge_min"
ATTR_TOTAL_OPERATION_TIME = "total_operation_time_h"
ATTR_TOTAL_CHARGING_TIME = "total_charging_time_h"
ATTR_SVG_X_POS = "svg_xpos"
ATTR_SVG_Y_POS = "svg_ypos"
ATTR_MAP_UPDATE_AVAILABLE = "map_update_available"
