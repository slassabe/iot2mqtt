#!/usr/local/bin/python3
# coding=utf-8

"""
This module defines the default configuration values for the iot2mqtt application. It includes
the initialization of supported device models and the setup of state normalizers and encoder
registries.

"""

from iot2mqtt import abstract, dev, encoder, processor, utils

# Supported model names
CTP_R01 = "CTP-R01"  # https://www.zigbee2mqtt.io/devices/CTP-R01.html
HM_ALARM_BUTTON = "HM1RC-2-E"  # https://www.zigbee2mqtt.io/devices/HM1RC-2-E.html 
HS1SA = "HS1SA"  # https://www.zigbee2mqtt.io/devices/HS1SA.html
MIFLORA = "Miflora"
NEO_ALARM = "NAS-AB02B2"  # https://www.zigbee2mqtt.io/devices/NAS-AB02B2.html
NOUS_DOOR_CONTACT = "E3"  # https://www.zigbee2mqtt.io/devices/E3.html
RING_ALARM = "alarm"
RING_CAMERA = "camera"
RING_CHIME = "chime"
SHELLY_PLUGS = "Shelly Plug S"  # Shelly Plug S WiFi smart plug
SHELLY_UNI = "Shelly Uni"  # Shelly Uni WiFi relay/dimmer
SN_AIRSENSOR = "SNZB-02"  # https://www.zigbee2mqtt.io/devices/SNZB-02.html
SN_BUTTON = "SNZB-01"  # https://www.zigbee2mqtt.io/devices/SNZB-01.html
SN_DOOR_CONTACT_P = "SNZB-04P"  # https://www.zigbee2mqtt.io/devices/SNZB-04P.html
SN_MINI = "ZBMINI-L"  # https://www.zigbee2mqtt.io/devices/ZBMINI.html
SN_MINI_L2 = "ZBMINIL2"  # https://www.zigbee2mqtt.io/devices/ZBMINIL2.html
SN_MOTION = "SNZB-03"  # https://www.zigbee2mqtt.io/devices/SNZB-03.html
SN_MOTION_P = "SNZB-03P"  # https://www.zigbee2mqtt.io/devices/SNZB-03P.html
SN_SMART_PLUG = "S26R2ZB"  # https://www.zigbee2mqtt.io/devices/S26R2ZB.html
SN_ZBBRIDGE = "Sonoff ZbBridge"  # Tasmota signature for Sonoff ZbBridge
SOMFY_SHADES = "ESPSomfy-RTS MQTT"
SRTS_A01 = "SRTS-A01"  # https://www.zigbee2mqtt.io/devices/SRTS-A01.html
TUYA_SOIL = "TS0601_soil"  # https://www.zigbee2mqtt.io/devices/TS0601_soil.html


class Models(metaclass=utils.Singleton):
    """
    Default configuration values for the iot2mqtt application.
    """

    CTP_R01 = dev.ModelFactory.get(CTP_R01)
    HM_ALARM_BUTTON = dev.ModelFactory.get(HM_ALARM_BUTTON)
    HS1SA = dev.ModelFactory.get(HS1SA)
    MIFLORA = dev.ModelFactory.get(MIFLORA)
    NEO_ALARM = dev.ModelFactory.get(NEO_ALARM)
    NOUS_DOOR_CONTACT = dev.ModelFactory.get(NOUS_DOOR_CONTACT)
    RING_ALARM = dev.ModelFactory.get(RING_ALARM)
    RING_CAMERA = dev.ModelFactory.get(RING_CAMERA)
    RING_CHIME = dev.ModelFactory.get(RING_CHIME)
    SHELLY_PLUGS = dev.ModelFactory.get(SHELLY_PLUGS)
    SHELLY_UNI = dev.ModelFactory.get(SHELLY_UNI)
    SN_AIRSENSOR = dev.ModelFactory.get(SN_AIRSENSOR)
    SN_BUTTON = dev.ModelFactory.get(SN_BUTTON)
    SN_DOOR_CONTACT_P = dev.ModelFactory.get(SN_DOOR_CONTACT_P)
    SN_MINI = dev.ModelFactory.get(SN_MINI)
    SN_MINI_L2 = dev.ModelFactory.get(SN_MINI_L2)
    SN_MOTION = dev.ModelFactory.get(SN_MOTION)
    SN_MOTION_P = dev.ModelFactory.get(SN_MOTION_P)
    SN_SMART_PLUG = dev.ModelFactory.get(SN_SMART_PLUG)
    SN_ZBBRIDGE = dev.ModelFactory.get(SN_ZBBRIDGE)
    SOMFY_SHADES = dev.ModelFactory.get(SOMFY_SHADES)
    SRTS_A01 = dev.ModelFactory.get(SRTS_A01)
    TUYA_SOIL = dev.ModelFactory.get(TUYA_SOIL)

    def __init__(self) -> None:
        try:
            utils.i2m_log.info("Loading default configuration")
            Models._initialize_state_normalizer()
            Models._initialize_encoder_registries()
        except Exception as e:
            # Handle initialization errors
            utils.i2m_log.error("Initialization error: %s", e)

    @classmethod
    def _initialize_state_normalizer(cls) -> None:
        """
        Initialize the state normalizer with the initial registry.
        """
        processor.StateNormalizerFactory(
            initial_registry={
                cls.CTP_R01: abstract.MagicCube,
                cls.HM_ALARM_BUTTON: abstract.AlarmButton,
                cls.HS1SA: abstract.SmokeSensor,
                cls.NEO_ALARM: abstract.Alarm,
                cls.NOUS_DOOR_CONTACT: abstract.DoorSensor,
                cls.RING_ALARM: abstract.RingAlarm,
                cls.RING_CAMERA: abstract.Camera,
                cls.RING_CHIME: abstract.Chime,
                cls.SHELLY_PLUGS: abstract.Switch,
                cls.SHELLY_UNI: abstract.Switch2Channels,
                cls.SN_AIRSENSOR: abstract.AirSensor,
                cls.SN_BUTTON: abstract.Button,
                cls.SN_DOOR_CONTACT_P: abstract.DoorSensor,
                cls.SN_MINI: abstract.Switch,
                cls.SN_MINI_L2: abstract.Switch,
                cls.SN_MOTION: abstract.Motion,
                cls.SN_MOTION_P: abstract.Motion,
                cls.SN_SMART_PLUG: abstract.Switch,
                cls.SOMFY_SHADES: abstract.SomfyShade,
                cls.SRTS_A01: abstract.SrtsA01,
            }
        )

    @classmethod
    def _initialize_encoder_registries(cls) -> None:
        """
        Initialize the encoders according to the models
        """
        encoder.EncoderRegistry(
            models=[cls.SN_MINI, cls.SN_MINI_L2, cls.SN_SMART_PLUG],
            settable_fields=[abstract.STATE],
            gettable_fields=[abstract.STATE],
            field_aliases={abstract.POWER: abstract.STATE},
        )

        encoder.EncoderRegistry(
            models=[cls.SHELLY_PLUGS],
            settable_fields=["Power"],
            gettable_fields=["Power"],
            field_aliases={"power": "Power"},
        )

        encoder.EncoderRegistry(
            models=[cls.SHELLY_UNI],
            settable_fields=["Power1", "Power2"],
            gettable_fields=["Power1", "Power2"],
            field_aliases={"power1": "Power1", "power2": "Power2"},
        )

        encoder.EncoderRegistry(
            models=[cls.NEO_ALARM],
            settable_fields=[
                abstract.ALARM,
                abstract.DURATION,
                abstract.MELODY,
                abstract.VOLUME,
            ],
            gettable_fields=[],
        )

        encoder.EncoderRegistry(
            models=[cls.SRTS_A01],
            settable_fields=[
                abstract.CHILD_LOCK,
                abstract.EXTERNAL_TEMPERATURE_INPUT,
                abstract.OCCUPIED_HEATING_SETPOINT,
                abstract.PRESET,
                abstract.SCHEDULE_SETTING,
                abstract.SCHEDULE,
                abstract.SENSOR,
                abstract.SYSTEM_MODE,
                abstract.VALVE_DETECTION,
                abstract.WINDOW_DETECTION,
            ],
            gettable_fields=[
                abstract.CHILD_LOCK,  # Just one field request get all fields
            ],
        )

        encoder.EncoderRegistry(
            models=[cls.SOMFY_SHADES],
            settable_fields=[
                abstract.DIRECTION,
                abstract.MYPOS,
                abstract.MYTILTPOS,
                abstract.POSITION,
                abstract.SUNFLAG,
                abstract.SUNNY,
                abstract.TARGET,
                abstract.TILTPOSITION,
                abstract.TILTTARGET,
                abstract.WINDY,
            ],
            gettable_fields=[],
        )

        encoder.EncoderRegistry(
            models=[cls.RING_ALARM],
            settable_fields=[
                abstract.MODE,
            ],
            gettable_fields=[],
        )

        encoder.EncoderRegistry(
            models=[cls.RING_CAMERA],
            settable_fields=[
                abstract.LIGHT,
                abstract.MOTION_DETECTION,
                abstract.MOTION_WARNING,
                abstract.SIREN,
                abstract.SNAPSHOT_INTERVAL,
                abstract.STREAM,
            ],
            gettable_fields=[],
        )

        encoder.EncoderRegistry(
            models=[cls.RING_CHIME],
            settable_fields=[
                abstract.PLAY_MOTION_SOUND,
                abstract.PLAY_MOTION_SOUND,
                abstract.SNOOZE,
                abstract.SNOOZE_MINUTES,
            ],
            gettable_fields=[],
        )
