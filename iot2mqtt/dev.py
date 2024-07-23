#!/usr/local/bin/python3
# coding=utf-8
"""
iot2mqtt.dev
============

This module defines various enumerations and classes related to IoT device models, protocols, 
and actions.
It also includes custom exceptions for handling specific error cases.

Classes and Enums
-----------------

- Model: Enumeration representing different models of IoT devices.
- Protocol: Enumeration representing different communication protocols used by IoT devices.
- Device: Represents a generic IoT device in the system.
- ButtonAction: Enumeration defining button action values.
- DecodingException: Exception raised for errors in the decoding process.

Examples
--------

Here is an example of how to use the `Device` class:

.. code-block:: python

    from iot2mqtt.dev import Device, Protocol, Model

    device = Device(
        name="Living Room Light",
        protocol=Protocol.Z2M,
        model=Model.SN_MINI
    )
    print(device)
    # Output: name='Living Room Light' protocol=<Protocol.Z2M: 'Zigbee2MQTT'> model=<Model.SN_MINI: 'ZBMINI-L'>


"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from iot2mqtt import utils


class Model(str, Enum):
    """
    This enum is used to represent the different models of devices that can be discovered.

    Attributes:
        MIFLORA (str): Xiaomi Mi Flora plant sensor.
        NEO_ALARM (str): Neo NAS-AB02B2 Zigbee Siren.
        RING_CAMERA (str): Ring Camera.
        SHELLY_PLUGS (str): Shelly Plug S WiFi smart plug.
        SHELLY_UNI (str): Shelly Uni WiFi relay/dimmer.
        SRTS_A01 (str): SRTS-A01 Zigbee device.
        TUYA_SOIL (str): Tuya TS0601_soil Zigbee soil moisture sensor.
        SN_AIRSENSOR (str): Sonoff Zigbee air temperature/humidity sensor.
        SN_BUTTON (str): Sonoff SNZB-01 Zigbee wireless button.
        SN_MOTION (str): Sonoff SNZB-03 Zigbee motion sensor.
        SN_MINI (str): Sonoff ZBMINI-L Zigbee wireless switch module.
        SN_MINI_L2 (str): Sonoff ZBMINIL2 Zigbee wireless switch module.
        SN_SMART_PLUG (str): Sonoff S26R2ZB Zigbee smart plug.
        SN_ZBBRIDGE (str): Sonoff ZbBridge Tasmota signature.
        NONE (str): No model, used in discovery messages.
        UNKNOWN (str): Unknown model.
    """

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
    NONE = "None"  # No model
    UNKNOWN = "Unknown"  # Unknown model

    @staticmethod
    def from_str(label: str):
        """
        Returns the Model enum value corresponding to the given label.

        This method takes a label as input and returns the corresponding Model enum value.
        If the label does not correspond to any Model enum value, it returns Model.UNKNOWN.

        Args:
            label (str): The label to get the Model enum value for.

        Returns:
            Model: The Model enum value corresponding to the label, or Model.UNKNOWN if
            the label does not correspond to any Model enum value.

        Examples
        --------

        Here is an example of how to use the `Model` enum:

        .. code-block:: python

            from iot2mqtt.dev import Model

            model = Model.from_str("SRTS-A01")
            print(model)  # Output: Model.SRTS_A01
        """
        if label is None:
            return Model.NONE
        for model in Model:
            if model.value == label:
                return model
        utils.i2m_log.warning("Unknown model: %s", label)
        return Model.UNKNOWN


class Protocol(Enum):
    """
    Enumeration for different communication protocols used by IoT devices.

    This enum class represents various communication protocols that IoT devices can use to interact
    with each other and with central systems. Each protocol is represented as a string constant.

    Attributes:
        DEFAULT (str): Default protocol, used as a fallback.
        HOMIE (str): The Homie IoT convention for MQTT.
        RING (str): The protocol used by Ring devices.
        SHELLY (str): The protocol used by Shelly smart home devices.
        TASMOTA (str): The protocol used by Tasmota firmware for ESP8266/ESP32 boards.
        Z2M (str): The Zigbee2MQTT protocol for Zigbee devices.
        Z2T (str): The Zigbee2Tasmota protocol for Zigbee devices using Tasmota firmware.
    """

    DEFAULT = "default"
    HOMIE = "Homie"
    RING = "Ring"
    SHELLY = "Shelly"
    TASMOTA = "Tasmota"
    Z2M = "Zigbee2MQTT"
    Z2T = "Zigbee2Tasmota"


class Device(BaseModel):
    """
    Represents a generic IoT device in the system.

    This class serves as a base model for all types of IoT devices. It defines common properties
    and methods that all devices should have. Specific device types should inherit from this class
    and add their own unique properties and methods.

    Attributes:
        name (str): The human-readable name of the device. This field is immutable.
        protocol (Protocol): The communication protocol used by the device. This field is immutable.
        address (Optional[str]): The network address of the device. Defaults to None.
        model (Optional[Model]): The model of the device. Defaults to None.
    """

    name: str = (Field(frozen=True),)
    protocol: Protocol = (Field(frozen=True),)
    address: Optional[str] = (None,)
    model: Optional[Model] = (None,)


class ButtonAction(Enum):
    """
    Enumeration defining button action values.

    This enum defines string constants for possible button actions
    like single press, double press, long press, etc.

    Attributes:
        SINGLE_ACTION (str): Represents a single button press action.
        DOUBLE_ACTION (str): Represents a double button press action.
        LONG_ACTION (str): Represents a long button press action.
    """

    SINGLE_ACTION = "single"
    DOUBLE_ACTION = "double"
    LONG_ACTION = "long"


