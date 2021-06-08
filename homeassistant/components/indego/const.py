"""Constants for Indego integration."""
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

DOMAIN = "indego"
DATA_UPDATED = f"{DOMAIN}_data_updated"
CONF_ATTR = "attributes"
ATTR_SEND_COMMAND = "command"
ATTR_SMARTMOWING = "enable"
DEFAULT_NAME = "Indego"
DEFAULT_NAME_COMMANDS = None
SERVICE_NAME_COMMAND = "command"
SERVICE_NAME_SMARTMOW = "smartmowing"
PLATFORMS = [SENSOR_DOMAIN]

ATTR_STATE_NUMBER = "state_number"
ATTR_DISCHARGE = "discharge"
ATTR_CYCLES = "cycles"
ATTR_BATTERY_TEMP = "battery_temp"
ATTR_AMBIENT_TEMP = "ambient_temp"
ATTR_LAST_SESSION_OPERATION_MIN = "last_session_operation_min"
ATTR_LAST_SESSION_CUT_MIN = "last_session_cut_min"
ATTR_LAST_SESSION_CHARGE_MIN = "last_session_charge_min"
ATTR_TOTAL_OPERATION_TIME = "total_operation_time_h"
ATTR_TOTAL_CHARGING_TIME = "total_charging_time_h"
