from enum import Enum
from typing import Literal, Optional

from pydantic import (
    AliasChoices,
    Field,
    confloat,
)

from iot2mqtt.devices.common_abstract import DeviceState


class AirSensor(DeviceState):
    """Air sensor with humidity and temperature measurements."""

    humidity: Optional[float] = None
    temperature: Optional[float] = None


class Alarm(DeviceState):
    """Alarm device with volume, melody, duration, and battery status."""

    alarm: Optional[bool] = None
    battery_low: Optional[bool] = None
    duration: Optional[int] = None
    melody: Optional[int] = None
    volume: Optional[Literal["low", "medium", "high"]] = None


class AlarmVolumes(str, Enum):
    """Possible alarm volume levels: low, medium, high."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlarmButtonlValues(str, Enum):
    """Alarm controller actions: emergency, disarm, arm day zones, or arm all zones."""

    EMERGENCY_ACTION = "emergency"
    DISARM_ACTION = "disarm"
    ARM_DAYZONES_ACTION = "arm_day_zones"
    ARM_ALL_ACTION = "arm_all_zones"


class AlarmButton(DeviceState):
    """Alarm controller device with battery, link quality, and action state."""

    battery: Optional[float] = None
    action: Optional[AlarmButtonlValues] = None
    linkquality: Optional[int] = None


class ButtonValues(str, Enum):
    """Button press actions: single, double, or long press."""

    SINGLE_ACTION = "single"
    DOUBLE_ACTION = "double"
    LONG_ACTION = "long"


class Button(DeviceState):
    """Button device with action state (single, double, or long press)."""

    action: Optional[ButtonValues] = None


class DoorSensor(DeviceState):
    """Door/window contact sensor with battery, tamper detection, and link quality.

    Contact state indicates door/window open (False) or closed (True).
    """

    contact: Optional[bool] = None
    battery: Optional[int] = None
    voltage: Optional[int] = None
    tamper: Optional[bool] = None
    battery_low: Optional[bool] = None
    linkquality: Optional[int] = None


class MagicCube(DeviceState):
    """Aquara Cube T1 Pro device with motion, orientation, and action detection."""

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
    """Motion sensor with occupancy detection and battery status."""

    battery: Optional[int] = None
    occupancy: Optional[bool] = None


class SmokeSensor(DeviceState):
    """Smoke sensor with test mode and battery status."""

    smoke: Optional[bool] = None
    battery_low: Optional[bool] = None
    battery: Optional[int] = None
    test: Optional[bool] = None


class SoilSensor(DeviceState):
    """Soil sensor with moisture and temperature measurements."""

    moisture: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("moisture", "soil_moisture")
    )
    temperature: Optional[float] = None


class SrtsA01(DeviceState):
    """Aquara SRTS-A01 smart radiator thermostat with temperature and valve control.

    Supports remote temperature input, scheduling, child lock, and window detection.
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
    """Water level sensor with installation height and liquid depth measurements.

    Requires installation_height and liquid_depth_max to be configured via Z2M.
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
