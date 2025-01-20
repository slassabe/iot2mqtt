#!/usr/local/bin/python3
# coding=utf-8

"""
This module defines various abstract representations of IoT device states and attributes.
It provides a set of Pydantic models and enumerations to represent the state and configuration
of different types of IoT devices, such as switches, sensors, and alarms.

Constants
---------

- POWER_ON: String constant representing the "ON" state.
- POWER_OFF: String constant representing the "OFF" state.

"""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional, Union

from pydantic import (AliasChoices, BaseModel, BeforeValidator, Field,
                      computed_field, confloat)
from typing_extensions import Annotated

from iot2mqtt import exceptions

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
DIRECTION = "direction"
DURATION = "duration"
EXTERNAL_TEMPERATURE_INPUT = "external_temperature_input"
HUMIDITY = "humidity"
INTERNAL_HEATING_SETPOINT = "internal_heating_setpoint"
LINKQUALITY = "linkquality"
LOCAL_TEMPERATURE = "local_temperature"
MELODY = "melody"
MYPOS = "mypos"
MYTILTPOS = "myTiltPos"
OCCUPIED_HEATING_SETPOINT = "occupied_heating_setpoint"
OCCUPANCY = "occupancy"
POSITION = "position"
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
SUNFLAG = "sunFlag"
SUNNY = "sunny"
SYSTEM_MODE = "system_mode"
TARGET = "target"
TAMPER = "tamper"
TEMPERATURE = "temperature"
TILTPOSITION = "tiltPosition"
TILTTARGET = "tiltTarget"
UPDATE = "update"
VALVE_ALARM = "valve_alarm"
VALVE_DETECTION = "valve_detection"
VOLTAGE = "voltage"
VOLUME = "volume"
WINDOW_DETECTION = "window_detection"
WINDOW_OPEN = "window_open"
WINDY = "windy"


class Availability(BaseModel):
    """
    Represents the availability status of a device.

    Attributes:
        is_online (bool): Indicates whether the device is online. This field is immutable.
    """

    is_online: bool = Field(frozen=True)


class Registry(BaseModel):
    """
    Represents a registry of dicovered devices.

    Attributes:
        device_ids (List[str]): A list of device ids.
    """

    device_ids: List[str] = []


class DeviceState(BaseModel):
    """
    Root class for all device state classes.

    This class serves as the base for various device state representations,
    providing common attributes and functionality.

    Attributes:
        last_seen (Optional[datetime]): The timestamp of when the device was
                                        last seen. This field can be accessed
                                        using aliases "last_seen" or "Time".
    """

    last_seen: Optional[datetime] = Field(
        default=None, validation_alias=AliasChoices("last_seen", "Time")
    )


class AirSensor(DeviceState):
    """
    Represents the state of an air sensor device.

    Attributes:
        humidity (Optional[float]): The humidity level measured by the sensor.
        temperature (Optional[float]): The temperature measured by the sensor.
    """

    humidity: Optional[float] = None
    temperature: Optional[float] = None


POWER_ON = "ON"
POWER_OFF = "OFF"


class Switch(DeviceState):
    """
    Represents the state of a switch device.

    Attributes:
        power_on_behavior (Optional[str]): The behavior of the switch when power is restored.
        power (str): The current power state of the switch: "ON" or "OFF"
            This field can be accessed using aliases "power", "state", or "POWER".
    """

    power_on_behavior: Optional[str] = None
    power: Optional[Literal["ON", "OFF"]] = Field(
        validation_alias=AliasChoices("power", "state", "POWER")
    )


SWITCH_ON = Switch(power=POWER_ON)
SWITCH_OFF = Switch(power=POWER_OFF)


class Switch2Channels(DeviceState):
    """
    Represents the state of a switch device with two channels.

    Attributes:
        power1 (str): The current power state of the first channel: "ON" or "OFF"
            This field can be accessed using aliases "power1" or "POWER1".
        power2 (str): The current power state of the second channel: "ON" or "OFF"
            This field can be accessed using aliases "power2" or "POWER2".
    """

    power1: Optional[Literal["ON", "OFF"]] = Field(
        default=None, validation_alias=AliasChoices("power1", "POWER1")
    )
    power2: Optional[Literal["ON", "OFF"]] = Field(
        default=None, validation_alias=AliasChoices("power2", "POWER2")
    )


class Motion(DeviceState):
    """
    Represents the state of a motion sensor device.

    Attributes:
        occupancy (Optional[bool]): Indicates whether motion is detected.
        tamper (Optional[bool]): Indicates whether the device has been tampered with.
    """

    occupancy: Optional[bool] = None
    tamper: Optional[bool] = None


class DoorSensor(DeviceState):
    """
    Represents the state of a door sensor device.

    This class models the state information for door/window contact sensors, including
    contact status, battery information, tamper detection, and signal quality.

    Attributes:
        contact (Optional[bool]): Contact state of the sensor.
            - True: Contact is closed (door/window closed)
            - False: Contact is open (door/window open)
            - None: Contact state unknown
        battery (Optional[int]): Remaining battery percentage (0-100).
        voltage (Optional[int]): Battery voltage in millivolts.
        tamper (Optional[bool]): Tamper detection status.
            - True: Device has been tampered
            - False: No tampering detected
            - None: Tamper status unknown
        battery_low (Optional[bool]): Low battery warning indicator.
            - True: Battery is critically low
            - False: Battery level is okay
            - None: Battery status unknown
        linkquality (Optional[int]): Signal strength/link quality indicator (0-255).
    """

    contact: Optional[bool] = None
    battery: Optional[int] = None
    voltage: Optional[int] = None
    tamper: Optional[bool] = None
    battery_low: Optional[bool] = None
    linkquality: Optional[int] = None


class AlarmButtonlValues(str, Enum):
    """
    Enumeration representing possible alarm controler actions.

    Attributes:
        EMERGENCY_ACTION: Represents an emergency alarm action.
        DISARM_ACTION: Represents a disarm action.
        ARM_DAYZONES_ACTION: Represents an arm day zones action.
        ARM_ALL_ACTION: Represents an arm all zones action.
    """

    EMERGENCY_ACTION = "emergency"
    DISARM_ACTION = "disarm"
    ARM_DAYZONES_ACTION = "arm_day_zones"
    ARM_ALL_ACTION = "arm_all_zones"


class AlarmButton(DeviceState):
    """
    Represents the state of a alarm controler device.

    Attributes:
    battery (Optional[int]): The battery level of the device.
    action (AlarmButtonlValues): The action performed by the alarm controler.
    linkquality (Optional[int]): The link quality of the device.
    """

    battery: Optional[int] = None
    action: AlarmButtonlValues = None
    linkquality: Optional[int] = None


class ButtonValues(str, Enum):
    """
    Enumeration representing possible button actions.

    Attributes:
        SINGLE_ACTION: Represents a single button press action.
        DOUBLE_ACTION: Represents a double button press action.
        LONG_ACTION: Represents a long button press action.
    """

    SINGLE_ACTION = "single"
    DOUBLE_ACTION = "double"
    LONG_ACTION = "long"


class Button(DeviceState):
    """
    Represents the state of a button device.

    Attributes:
        action (ButtonValues): The action performed by the button.
    """

    action: ButtonValues = None


class ADC(DeviceState):
    """
    Represents the state of an ADC (Analog-to-Digital Converter) device.

    Attributes:
        Range (Optional[float]): The range value of the ADC.
        voltage (float): The computed voltage based on the range value.
    """

    Range: Optional[float] = Field(default=None)

    @computed_field
    @property
    def voltage(self) -> float:
        """
        Calculate the voltage based on the range.

        Returns:
            float: The calculated voltage in volts.
        """
        return self.Range / 100


class SrtsA01(DeviceState):
    """
    Represents the state of a Smart radiator thermostat AQARA SRTS-A01.
    """

    # Température d'absence pré-définie
    away_preset_temperature: Optional[confloat(gt=-10.0, lt=35.0)] = None
    # Batterie restante en %, peut prendre jusqu'à 24 heures avant d'être signalée.
    battery: Optional[int] = None
    # Indique si cette vanne est calibrée, utilisez l'option calibrer
    # pour calibrer.
    calibrated: Optional[bool] = None
    # Indique si cette vanne est calibrée, utilisez l'option calibrer pour calibrer.
    child_lock: Optional[bool] = None
    # Température de l'appareil
    device_temperature: Optional[float] = None
    # Entrée pour le capteur de température à distance
    # (lorsque le capteur est réglé sur externe)
    external_temperature_input: Optional[confloat(gt=0, lt=55)] = None
    internal_heating_setpoint: Optional[float] = None
    # Qualité du lien (force du signal)
    linkquality: Optional[int] = None
    # Température actuelle mesurée par le capteur interne ou externe
    local_temperature: Optional[float] = None
    # Consigne de température
    occupied_heating_setpoint: Optional[confloat(gt=5, lt=30)] = None
    # Nombre de pannes de courant (depuis le dernier couplage)
    power_outage_count: Optional[int] = None
    # Mode de l'appareil (similaire à system_mode): 'manual', 'away', 'auto'
    preset: Optional[Literal["manual", "away", "auto"]] = None
    # Lorsqu'il est activé, l'appareil change d'état en fonction de vos
    # paramètres de programmation.
    schedule: Optional[bool] = None
    # Configuration intelligente de l'horaire (par défaut :
    # lun, mar, mer, jeu, ven|8:00,24.0|18:00,17.0|23:00,22.0|8:00,22.0)
    schedule_settings: Optional[str] = None
    # Sélectionnez le détecteur température à utiliser
    sensor: Optional[Literal["internal", "external"]] = None
    # Indique si l'appareil est en mode configuration (E11)
    setup: Optional[bool] = None
    # Mode de l'appareil
    system_mode: Optional[Literal["off", "heat"]] = None
    update: Optional[dict] = None
    # Avertit d'une anomalie de contrôle de la température si la détection
    # de la vanne est activée (par exemple, thermostat mal installé,
    # défaillance de la vanne ou étalonnage incorrect, lien incorrect
    # avec le capteur de température externe)
    valve_alarm: Optional[bool] = None
    # Détermine si des anomalies de contrôle de la température
    # doivent être détectées
    valve_detection: Optional[bool] = None
    # Tension de la batterie en millivolts
    voltage: Optional[int] = None
    # Active/désactive la détection de fenêtre de l'appareil
    window_detection: Optional[bool] = None
    # Indique si la fenêtre est ouverte
    window_open: Optional[bool] = None


def _validate_somfy_value(value: any, expected_type) -> any:
    if value != "":
        return expected_type(value)
    else:
        raise exceptions.NoValueException(expected_type)


SomfyInt = Annotated[
    Union[int, str, None], BeforeValidator(lambda v: _validate_somfy_value(v, int))
]
SomfyBool = Annotated[
    Union[bool, str, None], BeforeValidator(lambda v: _validate_somfy_value(v, bool))
]


class SomfyDevice(DeviceState):
    """
    Represents the state of a Somfy RTS device.
    """

    name: Optional[str] = None
    remoteAddress: Optional[str] = None
    # The current direction of the motor movement. This will be one of the following values :
    # -1 = The shade is moving up, 0 = The shade is stopped, 1 = The shade is moving down
    direction: SomfyInt = None
    # The last rolling code that was used to send the last command from ESPSomfy RTS
    lastRollingCode: SomfyInt = None
    # Indicates the existence of a sun sensor. Valid values are true or false
    sunSensor: SomfyBool = None
    # Indicates whether the sun sensor is enabled or not. Valid values are 0 or 1
    sunFlag: SomfyInt = None
    # Indicates whether the shade thinks it is sunny or not. Valid values are 0 or 1
    sunny: SomfyInt = None
    # Indicates whether the shade thinks it is windy or calm. Valid values are 0 or 1
    windy: SomfyInt = None


class SomfyGroup(SomfyDevice):
    groupId: Optional[int] = None


class SomfyShade(SomfyDevice):
    # shadeId: Optional[int] = None
    shadeId: SomfyInt = None
    shadeType: SomfyInt = None
    # The tilt type if the shade type is blind :
    # 0 = None, 1 = Tilt Motor, 2 = Integrated Tilt, 3 = Tilt Only
    tiltType: SomfyInt = None
    # Indicates whether up is down and down is up.
    flipCommands: SomfyBool = None
    # Indicates whether 100% is open or closed. Valid values are true or false
    flipPosition: SomfyBool = None
    # The current lift position in percentage of the motor.
    position: SomfyInt = None
    # The current tilt position in percentage of the motor.
    tiltPosition: SomfyInt = None
    # The lift position that the shade is seeking
    target: SomfyInt = None
    # The tilt position that the shade is seeking
    tiltTarget: SomfyInt = None
    # The current favorite lift position. -1 is unset
    mypos: SomfyInt = None
    # The current favorite tilt position. -1 is unset
    myTiltPos: SomfyInt = None

    # Undocumented
    cmd: Optional[str] = None
    cmdAddress: Optional[str] = None
    cmdSource: Optional[str] = None


class MagicCube(DeviceState):
    """
    Represents the state of a Cube T1 Pro device from Aquara.
    """

    # Batterie restante en %
    battery: Optional[int] = None
    # Tension de la batterie en millivolts
    voltage: Optional[int] = None
    # Nombre de pannes de courant (depuis le dernier couplage)
    power_outage_count: Optional[int] = None

    operation_mode: Optional[Literal["action_mode", "scene_mode"]] = None
    # Face du cube
    side: Optional[int] = None
    # Action depuis face du cube
    action_from_side: Optional[int] = None
    # Angle en degrès
    action_angle: Optional[float] = None
    # Action déclenchée (par ex : un clic sur un bouton)
    action: Optional[
        Literal[
            "shake",
            "throw",
            "tap",
            "slide",
            "flip180",
            "flip90",
            "hold",
            "side_up",
            "rotate_left",
            "rotate_right",
            "1_min_inactivity",
            "flip_to_side",
        ]
    ] = None
    # Qualité du lien (force du signal)
    linkquality: Optional[int] = None


class AlarmVolumes(str, Enum):
    """
    Enumeration representing possible alarm volume levels.

    Attributes:
        LOW: Low volume level.
        MEDIUM: Medium volume level.
        HIGH: High volume level.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Alarm(DeviceState):
    """
    Represents the state of an alarm device.

    Attributes:
        alarm (Optional[bool]): Indicates whether the alarm is active.
        battery_low (Optional[bool]): Indicates whether the battery is low.
        duration (Optional[int]): Duration of the alarm.
        melody (Optional[int]): Melody of the alarm.
        volume (Optional[Literal["low", "medium", "high"]]): Volume level of the alarm.
    """

    alarm: Optional[bool] = None
    battery_low: Optional[bool] = None
    duration: Optional[int] = None
    melody: Optional[int] = None
    volume: Optional[Literal["low", "medium", "high"]] = None
