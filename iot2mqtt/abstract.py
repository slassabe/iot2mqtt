# coding=utf-8

"""
Re-export facade for abstract device classes.

Provides backward compatibility by re-exporting device state classes from their
protocol-specific modules. New code should import directly from the specific modules.
"""

from iot2mqtt.devices.common_abstract import (
    ADC,
    POWER_OFF,
    POWER_ON,
    SWITCH_OFF,
    SWITCH_ON,
    Availability,
    DeviceState,
    Registry,
    Switch,
    Switch2Channels,
)
from iot2mqtt.devices.ring_abstract import (
    BatteryAttributes,
    Camera,
    Chime,
    DingAttributes,
    EventSelectAttributes,
    MotionAttributes,
    MotionInfo,
    RingAlarm,
    RingDeviceState,
    RingInfo,
    SnapshotAttributes,
    StreamAttributes,
    WirelessAttributes,
)
from iot2mqtt.devices.somfy_abstract import (
    SomfyBool,
    SomfyDevice,
    SomfyGroup,
    SomfyInt,
    SomfyShade,
)
from iot2mqtt.devices.zigbee_abstract import (
    AirSensor,
    Alarm,
    AlarmButton,
    AlarmButtonlValues,
    Button,
    ButtonValues,
    DoorSensor,
    MagicCube,
    Motion,
    SmokeSensor,
    SoilSensor,
    SrtsA01,
    WaterLevel,
)

__all__ = [
    # Common
    "DeviceState",
    "Availability",
    "Registry",
    "Switch",
    "Switch2Channels",
    "ADC",
    "POWER_ON",
    "POWER_OFF",
    "SWITCH_ON",
    "SWITCH_OFF",
    # Zigbee
    "AirSensor",
    "Alarm",
    "AlarmButton",
    "AlarmButtonlValues",
    "Button",
    "ButtonValues",
    "DoorSensor",
    "MagicCube",
    "Motion",
    "SmokeSensor",
    "SoilSensor",
    "SrtsA01",
    "WaterLevel",
    # Ring
    "RingDeviceState",
    "MotionInfo",
    "StreamAttributes",
    "MotionAttributes",
    "BatteryAttributes",
    "WirelessAttributes",
    "EventSelectAttributes",
    "DingAttributes",
    "SnapshotAttributes",
    "RingInfo",
    "Camera",
    "Chime",
    "RingAlarm",
    # Somfy
    "SomfyDevice",
    "SomfyGroup",
    "SomfyShade",
    "SomfyInt",
    "SomfyBool",
]
