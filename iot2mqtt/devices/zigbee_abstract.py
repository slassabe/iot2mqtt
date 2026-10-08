from enum import Enum
from typing import Literal, Optional

from pydantic import (
    AliasChoices,
    Field,
    confloat,
)

from iot2mqtt.devices.common_abstract import DeviceState


class AirSensor(DeviceState):
    """
    Represents the state of an air sensor device.

    Attributes:
        humidity (Optional[float]): The humidity level measured by the sensor.
        temperature (Optional[float]): The temperature measured by the sensor.
    """

    humidity: Optional[float] = None
    temperature: Optional[float] = None


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

    battery: Optional[float] = None
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


class Motion(DeviceState):
    """
    Represents the generic states of a motion sensor device.

    Attributes:
        battery (Optional[int]): Remaining battery percentage (0-100).
        occupancy (Optional[bool]): Indicates whether motion is detected.
    """

    battery: Optional[int] = None
    occupancy: Optional[bool] = None


class SmokeSensor(DeviceState):
    """
    Represents the state of a smoke sensor device.
    """

    smoke: Optional[bool] = None
    battery_low: Optional[bool] = None
    battery: Optional[int] = None
    test: Optional[bool] = None


class SoilSensor(DeviceState):
    """
    Represents the state of an soil sensor device.

    Attributes:
        moisture (Optional[float]): The moisture level measured by the sensor.
        temperature (Optional[float]): The temperature measured by the sensor.
    """

    moisture: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("moisture", "soil_moisture")
    )
    temperature: Optional[float] = None


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
    child_lock: Optional[Literal["LOCK", "UNLOCK"]] = None
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


class WaterLevel(DeviceState):
    """
    Represents the state of a Water level sensor (subset of ME201WZ capabilities)
    assuming installation_height and liquid_depth_max should be set via Z2M or CLI
    command:
    $ CONTROLLER_ID=0xa4c138cc15efc8de
    $ mosquitto_pub -m "{\"installation_height\":1.3\", \"liquid_depth_max\":1.1\", \
        \"max_set\":90, \"mini_set\":20\"}" -t "zigbee2mqtt/$CONTROLLER_ID/set"

    """

    installation_height: Optional[float] = None
    liquid_depth: Optional[float] = None
    liquid_depth_max: Optional[float] = None
    liquid_level_percent: Optional[int] = None


__all__ = [
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
]
