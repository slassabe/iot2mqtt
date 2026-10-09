# coding=utf-8

"""
Common abstract device state classes and shared constants.

This module provides the base classes for device state representations
and shared power state constants used across device implementations.

Key entry points:
  - DeviceState: Base class for all device state models.
  - Availability: Device online/offline status.
  - Registry: Collection of discovered device identifiers.
  - Switch, Switch2Channels: Power switch state models.
  - ADC: Analog-to-Digital Converter state.
  - POWER_ON, POWER_OFF: Standard power state constants.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    computed_field,
)


class DeviceState(BaseModel):
    """
    Root class for all device state classes.

    This class serves as the base for various device state representations,
    providing common attributes and functionality.

    Attributes:
        last_seen: Timestamp when the device was last seen (aliases: "last_seen", "Time").
    """

    last_seen: Optional[datetime] = Field(
        default=None, validation_alias=AliasChoices("last_seen", "Time")
    )


class Availability(BaseModel):
    """
    Represents the availability status of a device.

    Attributes:
        is_online: Whether the device is currently online (immutable after creation).
    """

    is_online: bool = Field(frozen=True)


class Registry(BaseModel):
    """
    Represents a registry of discovered devices.

    Attributes:
        device_ids: List of unique device identifiers.
    """

    device_ids: List[str] = []


#
# Shared Data
#

POWER_ON = "ON"
POWER_OFF = "OFF"


class Switch(DeviceState):
    """
    Represents the state of a switch device.

    Attributes:
        power_on_behavior: Behavior when power is restored after outage.
        power: Current power state ("ON" or "OFF"). Aliases: "power", "state", "POWER".
    """

    power_on_behavior: Optional[str] = None
    power: Optional[Literal["ON", "OFF"]] = Field(
        validation_alias=AliasChoices("power", "state", "POWER")
    )


SWITCH_ON = Switch(power=POWER_ON)
SWITCH_OFF = Switch(power=POWER_OFF)


class Switch2Channels(DeviceState):
    """
    Represents the state of a switch device with two channels.

    Attributes:
        power1: Current power state of the first channel ("ON" or "OFF"). Aliases: "power1", "POWER1".
        power2: Current power state of the second channel ("ON" or "OFF"). Aliases: "power2", "POWER2".
    """

    power1: Optional[Literal["ON", "OFF"]] = Field(
        default=None, validation_alias=AliasChoices("power1", "POWER1")
    )
    power2: Optional[Literal["ON", "OFF"]] = Field(
        default=None, validation_alias=AliasChoices("power2", "POWER2")
    )


# Orphan


class ADC(DeviceState):
    """
    Represents the state of an ADC (Analog-to-Digital Converter) device.

    Attributes:
        Range: Raw ADC range value. Voltage is computed by dividing by 100.
    """

    Range: Optional[float] = Field(default=None)

    @computed_field
    @property
    def voltage(self) -> float:
        """
        Compute voltage from the ADC range value.

        Divides the raw range value by 100 to convert to volts.

        Returns:
            Voltage in volts.
        """
        return self.Range / 100


__all__ = [
    "DeviceState",
    "Availability",
    "Registry",
    "Switch",
    "Switch2Channels",
    "ADC",
    "POWER_ON",
    "POWER_OFF",
    "SWITCH_ON",
    "SWITCH_OFF",
]
