#!/usr/local/bin/python3
# coding=utf-8

"""
This module defines the default configuration values for the iot2mqtt application. It includes
the initialization of supported device models and the setup of state normalizers and encoder
registries.

"""

from iot2mqtt import abstract, dev, encoder, processor, utils

# Supported model names
MIFLORA = "Miflora"
NEO_ALARM = "NAS-AB02B2"  # https://www.zigbee2mqtt.io/devices/NAS-AB02B2.html
RING_CAMERA = "RingCamera"
SHELLY_PLUGS = "Shelly Plug S"  # Shelly Plug S WiFi smart plug
SHELLY_UNI = "Shelly Uni"  # Shelly Uni WiFi relay/dimmer
SRTS_A01 = "SRTS-A01"  # https://www.zigbee2mqtt.io/devices/SRTS-A01.html
TUYA_SOIL = "TS0601_soil"  # https://www.zigbee2mqtt.io/devices/TS0601_soil.html
SN_AIRSENSOR = "SNZB-02"  # https://www.zigbee2mqtt.io/devices/SNZB-02.html
SN_BUTTON = "SNZB-01"  # https://www.zigbee2mqtt.io/devices/SNZB-01.html
SN_MOTION = "SNZB-03"  # https://www.zigbee2mqtt.io/devices/SNZB-03.html
SN_MINI = "ZBMINI-L"  # https://www.zigbee2mqtt.io/devices/ZBMINI.html
SN_MINI_L2 = "ZBMINIL2"  # https://www.zigbee2mqtt.io/devices/ZBMINIL2.html
SN_SMART_PLUG = "S26R2ZB"  # https://www.zigbee2mqtt.io/devices/S26R2ZB.html
SN_ZBBRIDGE = "Sonoff ZbBridge"  # Tasmota signature for Sonoff ZbBridge


class Models(metaclass=utils.Singleton):
    """
    Default configuration values for the iot2mqtt application.
    """

    MIFLORA = dev.ModelFactory.get(MIFLORA)
    NEO_ALARM = dev.ModelFactory.get(NEO_ALARM)
    RING_CAMERA = dev.ModelFactory.get(RING_CAMERA)
    SHELLY_PLUGS = dev.ModelFactory.get(SHELLY_PLUGS)
    SHELLY_UNI = dev.ModelFactory.get(SHELLY_UNI)
    SRTS_A01 = dev.ModelFactory.get(SRTS_A01)
    TUYA_SOIL = dev.ModelFactory.get(TUYA_SOIL)
    SN_AIRSENSOR = dev.ModelFactory.get(SN_AIRSENSOR)
    SN_BUTTON = dev.ModelFactory.get(SN_BUTTON)
    SN_MOTION = dev.ModelFactory.get(SN_MOTION)
    SN_MINI = dev.ModelFactory.get(SN_MINI)
    SN_MINI_L2 = dev.ModelFactory.get(SN_MINI_L2)
    SN_SMART_PLUG = dev.ModelFactory.get(SN_SMART_PLUG)
    SN_ZBBRIDGE = dev.ModelFactory.get(SN_ZBBRIDGE)

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
                cls.SN_AIRSENSOR: abstract.AirSensor,
                cls.SN_MINI: abstract.Switch,
                cls.SN_MINI_L2: abstract.Switch,
                cls.SN_SMART_PLUG: abstract.Switch,
                cls.SHELLY_PLUGS: abstract.Switch,
                cls.SHELLY_UNI: abstract.Switch2Channels,
                cls.SN_MOTION: abstract.Motion,
                cls.SN_BUTTON: abstract.Button,
                cls.SRTS_A01: abstract.SrtsA01,
                cls.NEO_ALARM: abstract.Alarm,
            }
        )

    @classmethod
    def _initialize_encoder_registries(cls) -> None:
        """
        Initialize the encoders according to the models
        """
        encoder.EncoderRegistry(
            models=[cls.SN_MINI, cls.SN_MINI_L2, cls.SN_SMART_PLUG],
            settable_fields=["state"],
            gettable_fields=["state"],
            field_aliases={"power": "state"},
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
            settable_fields=["alarm", "duration", "melody", "volume"],
            gettable_fields=[],
        )

        encoder.EncoderRegistry(
            models=[cls.SRTS_A01],
            settable_fields=[
                "child_lock",
                "external_temperature_input",
                "occupied_heating_setpoint",
                "preset",
                "schedule_settings",
                "schedule",
                "schedule_settings",
                "sensor",
                "system_mode",
                "valve_detection",
                "window_detection",
            ],
            gettable_fields=[
                "child_lock",  # Just one field request get all fields
            ],
        )


Models()
