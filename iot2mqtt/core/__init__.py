"""
mqttcore: Core MQTT utilities extracted from iot2mqtt.

This module provides essential utilities for MQTT operations:
- exceptions: Custom exception classes
- mqtthelper: MQTT helper functions and classes
- utils: Utility functions and classes
"""

__version__ = "1.0.2"

# Explicit imports from submodules
from iot2mqtt.core.exceptions import (
    ConnectionException,
    DecodingException,
    NoValueException,
)
from iot2mqtt.core.mqtthelper import (
    ClientHelper,
    ConnectionRetryPolicy,
    MQTTContext,
    SecurityContext,
)
from iot2mqtt.core.utils import (
    MetricsCollector,
    Singleton,
    TimerManager,
    check_parameter,
    retry_with_timer,
)

__all__ = [
    # From exceptions
    "ConnectionException",
    "DecodingException",
    "NoValueException",
    # From mqtthelper
    "ClientHelper",
    "ConnectionRetryPolicy",
    "MQTTContext",
    "SecurityContext",
    # From utils
    "MetricsCollector",
    "Singleton",
    "TimerManager",
    "check_parameter",
    "retry_with_timer",
]
