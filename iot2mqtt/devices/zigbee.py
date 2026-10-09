# coding=utf-8

"""
Zigbee device registrations (Z2M protocol).

Registers Zigbee devices via zigbee2mqtt bridge for sensors, controls, and input
devices with bidirectional MQTT communication.
"""

from iot2mqtt import dev, registry
from iot2mqtt.devices import fields
from iot2mqtt.devices.common_abstract import Switch
from iot2mqtt.devices.zigbee_abstract import (
    AirSensor,
    Alarm,
    AlarmButton,
    Button,
    DoorSensor,
    MagicCube,
    Motion,
    SmokeSensor,
    SoilSensor,
    SrtsA01,
    WaterLevel,
)

#
# https://www.zigbee2mqtt.io/devices/CTP-R01.html
#
CTP_R01_TAG = "CTP-R01"
CTP_R01_MODEL = registry.DeviceRegistry.register_state(
    model_tag=CTP_R01_TAG, device_state_class=MagicCube, protocol=dev.Protocol.Z2M
)

#
# https://www.zigbee2mqtt.io/devices/HM1RC-2-E.html
#
HM_ALARM_BUTTON_TAG = "HM1RC-2-E"
HM_ALARM_BUTTON_MODEL = registry.DeviceRegistry.register_state(
    model_tag=HM_ALARM_BUTTON_TAG,
    device_state_class=AlarmButton,
    protocol=dev.Protocol.Z2M,
)

#
# https://www.zigbee2mqtt.io/devices/HS1SA.html
#
HS1SA_TAG = "HS1SA"
HS1SA_MODEL = registry.DeviceRegistry.register_state(
    model_tag=HS1SA_TAG, device_state_class=SmokeSensor, protocol=dev.Protocol.Z2M
)

#
# https://www.zigbee2mqtt.io/devices/NAS-AB02B2.html
#
NEO_ALARM_TAG = "NAS-AB02B2"
NEO_ALARM_MODEL = registry.DeviceRegistry.register_state(
    NEO_ALARM_TAG, device_state_class=Alarm, protocol=dev.Protocol.Z2M
)
registry.DeviceRegistry.register_encoder(
    NEO_ALARM_TAG,
    settable_fields=[
        fields.ALARM,
        fields.DURATION,
        fields.MELODY,
        fields.VOLUME,
    ],
    gettable_fields=[],
)

#
# https://www.zigbee2mqtt.io/devices/E3.html
#
NOUS_DOOR_CONTACT_TAG = "E3"
NOUS_DOOR_CONTACT_MODEL = registry.DeviceRegistry.register_state(
    model_tag=NOUS_DOOR_CONTACT_TAG,
    device_state_class=DoorSensor,
    protocol=dev.Protocol.Z2M,
)

#
# https://www.zigbee2mqtt.io/devices/SNZB-02.html
# https://www.zigbee2mqtt.io/devices/SNZB-02D.html
# https://www.zigbee2mqtt.io/devices/SNZB-02P.html
#
SN_AIRSENSOR_TAG = "SNZB-02"
SN_AIRSENSOR_2D_TAG = "SNZB-02D"
SN_AIRSENSOR_2P_TAG = "SNZB-02P"

SN_AIRSENSOR_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_AIRSENSOR_TAG, device_state_class=AirSensor, protocol=dev.Protocol.Z2M
)
SN_AIRSENSOR_2D_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_AIRSENSOR_2D_TAG, device_state_class=AirSensor, protocol=dev.Protocol.Z2M
)
SN_AIRSENSOR_2P_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_AIRSENSOR_2P_TAG, device_state_class=AirSensor, protocol=dev.Protocol.Z2M
)

#
# https://www.zigbee2mqtt.io/devices/SNZB-01.html
#
SN_BUTTON_TAG = "SNZB-01"
SN_BUTTON_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_BUTTON_TAG, device_state_class=Button, protocol=dev.Protocol.Z2M
)

#
# https://www.zigbee2mqtt.io/devices/SNZB-04P.html
#
SN_DOOR_CONTACT_P_TAG = "SNZB-04P"
SN_DOOR_CONTACT_P_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_DOOR_CONTACT_P_TAG,
    device_state_class=DoorSensor,
    protocol=dev.Protocol.Z2M,
)

#
# https://www.zigbee2mqtt.io/devices/ZBMINI.html
# https://www.zigbee2mqtt.io/devices/ZBMINIL2.html
# https://www.zigbee2mqtt.io/devices/S26R2ZB.html
#
SN_MINI_TAG = "ZBMINI-L"
SN_MINI_L2_TAG = "ZBMINIL2"
SN_SMART_PLUG_TAG = "S26R2ZB"

SN_MINI_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_MINI_TAG, device_state_class=Switch, protocol=dev.Protocol.Z2M
)
SN_MINI_L2_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_MINI_L2_TAG, device_state_class=Switch, protocol=dev.Protocol.Z2M
)
SN_SMART_PLUG_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_SMART_PLUG_TAG, device_state_class=Switch, protocol=dev.Protocol.Z2M
)

registry.DeviceRegistry.register_encoder(
    SN_MINI_TAG,
    settable_fields=[fields.STATE],
    gettable_fields=[fields.STATE],
    field_aliases={fields.POWER: fields.STATE},
)
registry.DeviceRegistry.register_encoder(
    SN_MINI_L2_TAG,
    settable_fields=[fields.STATE],
    gettable_fields=[fields.STATE],
    field_aliases={fields.POWER: fields.STATE},
)
registry.DeviceRegistry.register_encoder(
    SN_SMART_PLUG_TAG,
    settable_fields=[fields.STATE],
    gettable_fields=[fields.STATE],
    field_aliases={fields.POWER: fields.STATE},
)

#
# https://www.zigbee2mqtt.io/devices/SNZB-03.html
# https://www.zigbee2mqtt.io/devices/SNZB-03P.html
#
SN_MOTION_TAG = "SNZB-03"
SN_MOTION_P_TAG = "SNZB-03P"

SN_MOTION_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_MOTION_TAG, device_state_class=Motion, protocol=dev.Protocol.Z2M
)
SN_MOTION_P_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SN_MOTION_P_TAG, device_state_class=Motion, protocol=dev.Protocol.Z2M
)

#
# https://www.zigbee2mqtt.io/devices/SRTS-A01.html
#
SRTS_A01_TAG = "SRTS-A01"
SRTS_A01_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SRTS_A01_TAG, device_state_class=SrtsA01, protocol=dev.Protocol.Z2M
)
registry.DeviceRegistry.register_encoder(
    SRTS_A01_TAG,
    settable_fields=[
        fields.CHILD_LOCK,
        fields.EXTERNAL_TEMPERATURE_INPUT,
        fields.OCCUPIED_HEATING_SETPOINT,
        fields.PRESET,
        fields.SCHEDULE_SETTING,
        fields.SCHEDULE,
        fields.SENSOR,
        fields.SYSTEM_MODE,
        fields.VALVE_DETECTION,
        fields.WINDOW_DETECTION,
    ],
    gettable_fields=[
        fields.CHILD_LOCK,  # Just one field request get all fields
    ],
)

#
# https://www.zigbee2mqtt.io/devices/TS0601_soil.html
#
TUYA_SOIL_TAG = "TS0601_soil"
TUYA_SOIL_MODEL = registry.DeviceRegistry.register_state(
    model_tag=TUYA_SOIL_TAG, device_state_class=SoilSensor, protocol=dev.Protocol.Z2M
)

#
# https://www.zigbee2mqtt.io/devices/ME201WZ.html
#
TUYA_WATER_TAG = "ME201WZ"
TUYA_WATER_MODEL = registry.DeviceRegistry.register_state(
    model_tag=TUYA_WATER_TAG, device_state_class=WaterLevel, protocol=dev.Protocol.Z2M
)


# Misc
SN_ZBBRIDGE_TAG = "Sonoff ZbBridge"
SN_ZBBRIDGE_MODEL = dev.ModelFactory.get(SN_ZBBRIDGE_TAG)  # Tasmota signature for Sonoff ZbBridge
