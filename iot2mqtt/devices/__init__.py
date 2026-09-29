"""Device protocol handlers for various IoT platforms.

This package contains device-specific registrations for supported protocols:
  - zigbee.py: Zigbee2MQTT bridge devices
  - shelly.py: Shelly WiFi devices
  - ring.py: Ring security devices
  - somfy.py: Somfy RTS motorized shades

All devices register with the DeviceRegistry when their modules are imported.
Use load_devices_for_protocol() or load_devices_for_protocols() to dynamically
import device modules based on required protocols.
"""

import logging
from typing import List, Optional

from iot2mqtt import dev
from iot2mqtt.core import utils

logger = logging.getLogger(__name__)


# Map Protocol enum to device module name
PROTOCOL_MODULES = {
    dev.Protocol.ESPSOMFY: "iot2mqtt.devices.somfy",
    dev.Protocol.RING: "iot2mqtt.devices.ring",
    dev.Protocol.SHELLY: "iot2mqtt.devices.shelly",
    dev.Protocol.TASMOTA: "iot2mqtt.devices.tasmota",
    dev.Protocol.Z2M: "iot2mqtt.devices.zigbee",
}


def _load_devices_for_protocol(protocol: dev.Protocol) -> bool:
    """Dynamically import device module for specified protocol."""
    if protocol not in PROTOCOL_MODULES:
        raise ValueError(
            f"No device module for protocol: {protocol}. "
            f"Supported protocols: {list(PROTOCOL_MODULES.keys())}"
        )

    _module_name = PROTOCOL_MODULES[protocol]

    try:
        __import__(_module_name)
        return True

    except ImportError as e:
        _error_msg = (
            f"Failed to load devices for protocol {protocol.value}: "
            f"Could not import module '{_module_name}'. {str(e)}"
        )
        utils.i2m_log.error(_error_msg)
        raise ImportError(_error_msg) from e

    except Exception as e:
        _error_msg = f"Unexpected error loading devices for protocol {protocol.value}: " f"{str(e)}"
        utils.i2m_log.error(_error_msg)
        raise RuntimeError(_error_msg) from e


def load_devices_for_protocols(protocols: Optional[List[dev.Protocol]] = None) -> list[str]:
    """Load device modules for multiple protocols.

    Attempts to load device modules for each protocol in the list. By default,
    continues loading remaining protocols even if one fails. Individual protocol
    failures are logged as warnings.

    Args:
        protocols (List[dev.Protocol]): List of Protocol enum values to load.
            If None, loads all supported protocols in PROTOCOL_MODULES.

    Returns:
        int: Number of protocols successfully loaded.

    Raises:
        ValueError: Unsupported protocol is encountered.
        ImportError: Module import fails.
        RuntimeError: Unexpected error occurs.

    Examples:
        Load specific protocols:
        >>> from iot2mqtt import dev
        >>> from iot2mqtt.devices import load_devices_for_protocols
        >>> _proto = load_devices_for_protocols([dev.Protocol.Z2M, dev.Protocol.RING])
        >>> print(f"Loaded {_proto}")
        Loaded [<Protocol.Z2M: 'Zigbee2MQTT'>, , <Protocol.RING: 'Ring'>]

        Load all supported protocols:
        >>> _proto = load_devices_for_protocols()
        >>> print(f"Loaded {_proto}")
        Loaded [<Protocol.ESPSOMFY: 'ESPSomfy'>, <Protocol.RING: 'Ring'>,
        <Protocol.SHELLY: 'Shelly'>, <Protocol.TASMOTA: 'Tasmota'>, <Protocol.Z2M: 'Zigbee2MQTT'>]

        Error handling:
        >>> try:
        ...     load_devices_for_protocols([dev.Protocol.Z2M])
        ... except ImportError as e:
        ...     print(f"Error: {e}")
    """
    # Use all supported protocols if none specified
    if protocols is None:
        protocols = list(PROTOCOL_MODULES.keys())

    _loaded_protocols = []
    for protocol in protocols:
        _load_devices_for_protocol(protocol)
        _loaded_protocols.append(protocol)

    # Log summary
    utils.i2m_log.debug(f"Loaded successfully protocols: {_loaded_protocols}")
    return _loaded_protocols


__all__ = [
    "PROTOCOL_MODULES",
    "load_devices_for_protocols",
]
