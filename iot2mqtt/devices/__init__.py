"""Device protocol handlers for various IoT platforms.

This package contains device-specific registrations for supported protocols and
provides functions to dynamically load device modules for specified protocols.
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
    """Load device module for a specific protocol.

    Raises:
        ValueError: Protocol not in PROTOCOL_MODULES.
        ImportError: Module import fails.
        RuntimeError: Unexpected error during import.
    """
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
    """Load device modules for specified protocols.

    Loads device modules for each protocol. By default, continues loading
    remaining protocols even if one fails; failures are logged as warnings.

    Args:
        protocols: List of Protocol enum values to load. If None, loads all
            supported protocols in PROTOCOL_MODULES.

    Returns:
        List of protocol names successfully loaded.

    Raises:
        ValueError: Unsupported protocol encountered.
        ImportError: Module import fails.
        RuntimeError: Unexpected error occurs during load.

    Examples:
        Load specific protocols:
        >>> from iot2mqtt import dev
        >>> from iot2mqtt.devices import load_devices_for_protocols
        >>> loaded = load_devices_for_protocols([dev.Protocol.Z2M, dev.Protocol.RING])
        >>> print(f"Loaded {len(loaded)} protocols")
        Loaded 2 protocols

        Load all supported protocols:
        >>> loaded = load_devices_for_protocols()
        >>> print(f"Loaded {len(loaded)} protocols")
        Loaded 5 protocols
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
