#!/usr/local/bin/python3
# coding=utf-8
"""
IoT to MQTT bridge framework for integrating IoT devices with MQTT-based smart homes.

Provides device registry, protocol handlers, message processing, and MQTT client
management for devices across multiple protocols (Zigbee, Ring, Shelly, Somfy, Tasmota).
"""

# Core modules
from iot2mqtt import abstract, central, dev, messenger, processor, registry

# Core modules (backward compatibility)
from iot2mqtt.core import exceptions, mqtthelper, utils
from iot2mqtt.version import __version__

__all__ = [
    "exceptions",
    "mqtthelper",
    "utils",
    "abstract",
    "central",
    "dev",
    "messenger",
    "processor",
    "registry",
    "devices",
    "__version__",
]
