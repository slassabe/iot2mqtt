#!/usr/local/bin/python3
# coding=utf-8

"""
iot2mqtt.abstract
=================

This module defines various abstract representations of IoT device states and attributes.
It provides a set of Pydantic models and enumerations to represent the state and configuration
of different types of IoT devices, such as switches, sensors, and alarms.

Classes
-------

- ADC: Represents the state of an ADC (Analog-to-Digital Converter) device.
- AirSensor: Represents the state of an air sensor device.
- Alarm: Represents the state of an alarm device.
- AlarmVolumes: Enumeration representing possible alarm volume levels.
- Availability: Represents the availability status of a device.
- Button: Represents the state of a button device.
- ButtonValues: Enumeration representing possible button actions.
- DeviceState: Root class for all device state classes.
- Motion: Represents the state of a motion sensor device.
- SrtsA01: Represents the state of a specific Zigbee thermostat device.
- Switch: Represents the state of a switch device.
- Switch2Channels: Represents the state of a switch device with two channels.


Enums
-----

- ButtonValues: Enumeration representing possible button actions.
- AlarmVolumes: Enumeration representing possible alarm volume levels.

Constants
---------

- POWER_ON: String constant representing the "ON" state.
- POWER_OFF: String constant representing the "OFF" state.
- SWITCH_ON: Switch instance representing the "ON" state.
- SWITCH_OFF: Switch instance representing the "OFF" state.

Examples
--------

Here is an example of how to use the `Switch` class:

.. code-block:: python

    from iot2mqtt.abstract import Switch, POWER_ON, POWER_OFF

    switch = Switch(power=POWER_ON)
    print(switch.power)  # Output: ON

    switch.power = POWER_OFF
    print(switch.power)  # Output: OFF

"""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, computed_field, confloat

# Abstract IOT device properties

ACTION = "action"
ALARM = "alarm"
AWAY_PRESET_TEMPERATURE = "away_preset_temperature"
BATTERY = "battery"
BATTERY_LOW = "battery_low"
CALIBRATED = "calibrated"
CHILD_LOCK = "child_lock"
DEVICE_TEMPERATURE = "device_temperature"
DURATION = "duration"
EXTERNAL_TEMPERATURE_INPUT = "external_temperature_input"
HUMIDITY = "humidity"
INTERNAL_HEATING_SETPOINT = "internal_heating_setpoint"
LINKQUALITY = "linkquality"
LOCAL_TEMPERATURE = "local_temperature"
MELODY = "melody"
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
        device_names (List[str]): A list of device names.
    """

    device_names: List[str] = []


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
        return self.Range / 100


class SrtsA01(DeviceState):
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
