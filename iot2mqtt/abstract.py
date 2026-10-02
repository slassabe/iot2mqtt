# coding=utf-8

"""
Re-export facade for backward compatibility.

This module re-exports all abstract device classes from their protocol-specific
modules. Internal code should prefer importing directly from:
  - iot2mqtt.devices.common_abstract
  - iot2mqtt.devices.zigbee_abstract
  - iot2mqtt.devices.ring_abstract
  - iot2mqtt.devices.somfy_abstract
  - iot2mqtt.devices.tasmota_abstract

External consumers can continue using: from iot2mqtt import abstract
"""

# Explicitly re-export all __all__ entries to ensure complete API coverage
from iot2mqtt.devices import (
    common_abstract,
    ring_abstract,
    somfy_abstract,
    tasmota_abstract,
    zigbee_abstract,
)
from iot2mqtt.devices.common_abstract import *  # noqa: F401, F403
from iot2mqtt.devices.ring_abstract import *  # noqa: F401, F403
from iot2mqtt.devices.somfy_abstract import *  # noqa: F401, F403
from iot2mqtt.devices.tasmota_abstract import *  # noqa: F401, F403
from iot2mqtt.devices.zigbee_abstract import *  # noqa: F401, F403

__all__ = (
    common_abstract.__all__
    + zigbee_abstract.__all__
    + ring_abstract.__all__
    + somfy_abstract.__all__
    + tasmota_abstract.__all__
)
