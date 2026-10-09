# coding=utf-8
"""
IoT device models, protocols, and device definitions.

Provides model management with singleton factory, protocol enumeration for various
IoT platforms, and base device classes for representing IoT devices in the system.
"""

from enum import Enum
from threading import Lock
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel, frozen=True):
    """Frozen model representing an IoT device model identified by tag."""

    tag: str = Field(frozen=True)


class ModelFactory:
    """Thread-safe singleton factory for Model instances.
    
    Ensures only one Model instance exists per tag and provides thread-safe access
    with an UNKNOWN model constant for unrecognized models.
    """

    _model_instances: Dict[str, Model] = {}
    _lock: Lock = Lock()
    UNKNOWN: Model = Model(tag="UNKNOWN")

    @classmethod
    def get(cls, tag: str) -> Model:
        """Retrieve or create a Model instance by tag.

        Returns existing instance if tag exists, otherwise creates and caches new instance.

        Args:
            tag: Model identifier.

        Returns:
            Model instance associated with the tag.
        """

        with cls._lock:
            if tag in cls._model_instances:
                return cls._model_instances[tag]
            _model_instance = Model(tag=tag)
            cls._model_instances[tag] = _model_instance
            return _model_instance


class Protocol(Enum):
    """IoT device communication protocols.
    
    Enumeration of protocols supported by the system: ESPSomfy, Ring, Shelly, Tasmota,
    and Zigbee2MQTT.
    """

    ESPSOMFY = "ESPSomfy"
    RING = "Ring"
    SHELLY = "Shelly"
    TASMOTA = "Tasmota"
    Z2M = "Zigbee2MQTT"

    @classmethod
    def supported(cls) -> list["Protocol"]:
        """Return all supported protocols."""
        return [cls.ESPSOMFY, cls.RING, cls.SHELLY, cls.TASMOTA, cls.Z2M]


class Device(BaseModel):
    """Base model for IoT devices with protocol and addressing information.
    
    Common properties for all device types: immutable name and protocol, plus optional
    network address and model information.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(frozen=True)
    protocol: Protocol = Field(frozen=True)
    address: Optional[str] = None
    model: Optional[Model] = None


class RingDevice(Device):
    """Ring device with location identifier."""

    location_id: str = Field(frozen=True)


class ButtonAction(Enum):
    """Button press action types: single, double, or long press."""

    SINGLE_ACTION = "single"
    DOUBLE_ACTION = "double"
    LONG_ACTION = "long"
