#!/usr/local/bin/python3
# coding=utf-8
"""
This module defines various enumerations and classes related to IoT device models, protocols, 
and actions. It also includes custom exceptions for handling specific error cases.

Classes and Enums
-----------------

- Model: Represents a model of an IoT device.
- ModelFactory: Singleton class responsible for managing instances of Model objects.
- Protocol: Enumeration representing different communication protocols used by IoT devices.
- Device: Represents a generic IoT device in the system.
- ButtonAction: Enumeration defining button action values.

"""

from enum import Enum
from threading import Lock
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel, frozen=True):
    """
    Represents a model of an IoT device.

    Args:
        tag (str): The tag associated with the device model.
    """

    tag: str = Field(frozen=True)


class ModelFactory:
    """
    ModelFactory is a singleton class responsible for managing instances of Model objects.

    This class ensures that only one instance of each Model is created and provides a thread-safe
    mechanism for accessing these instances.
    """

    _model_instances: Dict[str, Model] = {}
    _lock: Lock = Lock()
    UNKNOWN: Model = Model(tag="UNKNOWN")

    @classmethod
    def get(cls, tag: str) -> Model:
        """
        Retrieve a Model instance by its tag. If the tag does not exist, create a new Model
        instance with the given tag.

        Args:
            tag (str): The tag associated with the Model instance.

        Returns:
            Model: The Model instance associated with the given tag, or a new instance if the
            tag does not exist.
        """

        with cls._lock:
            if tag in cls._model_instances:
                return cls._model_instances[tag]
            _model_instance = Model(tag=tag)
            cls._model_instances[tag] = _model_instance
            return _model_instance


class Protocol(Enum):
    """
    Enumeration for different communication protocols used by IoT devices.

    This enum class represents various communication protocols that IoT devices can use to interact
    with each other and with central systems. Each protocol is represented as a string constant.

    Attributes:
        DEFAULT (str): Default protocol, used as a fallback.
        ESPSOMFY (str): The protocol used by ESPHome Somfy RTS devices.
        HOMIE (str): The Homie IoT convention for MQTT.
        RING (str): The protocol used by Ring devices.
        SHELLY (str): The protocol used by Shelly smart home devices.
        TASMOTA (str): The protocol used by Tasmota firmware for ESP8266/ESP32 boards.
        Z2M (str): The Zigbee2MQTT protocol for Zigbee devices.
        Z2T (str): The Zigbee2Tasmota protocol for Zigbee devices using Tasmota firmware.
    """

    DEFAULT = "default"
    ESPSOMFY = "ESPSomfy"
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

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = (Field(frozen=True),)
    protocol: Protocol = (Field(frozen=True),)
    address: Optional[str] = (None,)
    model: Optional[Model] = (None,)


class RingDevice(Device):
    """
    Represents a Ring device in the system.
    """

    location_id: str = (Field(frozen=True),)


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
