# coding=utf-8
"""
Canonical field identifiers for device attributes across all protocols and types.

Provides protocol-agnostic constants for device properties (e.g., ACTION, ALARM,
BATTERY, STATE, TEMPERATURE) used by Tasmota, Shelly, Ring, Somfy, and other
device integrations.
"""

# Abstract IOT device properties

ACTION = "action"
ALARM = "alarm"
AWAY_PRESET_TEMPERATURE = "away_preset_temperature"
BATTERY = "battery"
BATTERY_LOW = "battery_low"
CALIBRATED = "calibrated"
CHILD_LOCK = "child_lock"
CONTACT = "contact"
DEVICE_TEMPERATURE = "device_temperature"
DURATION = "duration"
EXTERNAL_TEMPERATURE_INPUT = "external_temperature_input"
HUMIDITY = "humidity"
INSTALLATION_HEIGHT = "installation_height"
INTERNAL_HEATING_SETPOINT = "internal_heating_setpoint"
LINKQUALITY = "linkquality"
LIQUID_DEPTH = "liquid_depth"
LIQUID_DEPTH_MAX = "liquid_depth_max"
LIQUID_LEVEL_PERCENT = "liquid_level_percent"
LOCAL_TEMPERATURE = "local_temperature"
MELODY = "melody"
MOISTURE = "moisture"
OCCUPIED_HEATING_SETPOINT = "occupied_heating_setpoint"
OCCUPANCY = "occupancy"
POWER = "power"
POWER1 = "power1"
POWER2 = "power2"
POWER_ON_BEHAVIOUR = "power_on_behavior"
POWER_OUTAGE_COUNT = "power_outage_count"
PRESET = "preset"
RANGE = "Range"
SCHEDULE = "schedule"
SCHEDULE_SETTING = "schedule_setting"
SENSOR = "sensor"
SETUP = "setup"
STATE = "state"
SYSTEM_MODE = "system_mode"
TAMPER = "tamper"
TEMPERATURE = "temperature"
UPDATE = "update"
VALVE_ALARM = "valve_alarm"
VALVE_DETECTION = "valve_detection"
VOLTAGE = "voltage"
VOLUME = "volume"
WINDOW_DETECTION = "window_detection"
WINDOW_OPEN = "window_open"

# RING

LIGHT = "light"  # Ring Camera
MODE = "mode"
MOTION_DETECTION = "motion_detection"  # Ring Camera
MOTION_WARNING = "motion_warning"  # Ring Camera
PLAY_DING_SOUND = "play_ding_sound"  # Ring Chime
PLAY_MOTION_SOUND = "play_motion_sound"  # Ring Chime
SIREN = "siren"  # Ring Camera
SNAPSHOT_INTERVAL = "snapshot_interval"  # Ring Camera
SNOOZE = "snooze"  # Ring Chime
SNOOZE_MINUTES = "snooze_minutes"  # Ring Chime
STREAM = "stream"  # Ring Camera

# SOMFY

DIRECTION = "direction"
MYPOS = "mypos"
MYTILTPOS = "myTiltPos"
POSITION = "position"
SUNFLAG = "sunFlag"
SUNNY = "sunny"
TARGET = "target"
TILTPOSITION = "tiltPosition"
TILTTARGET = "tiltTarget"
WINDY = "windy"
