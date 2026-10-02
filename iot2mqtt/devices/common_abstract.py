# coding=utf-8

"""

Constants
---------

- POWER_ON: String constant representing the "ON" state.
- POWER_OFF: String constant representing the "OFF" state.
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
        last_seen (Optional[datetime]): The timestamp of when the device was
                                        last seen. This field can be accessed
                                        using aliases "last_seen" or "Time".
    """

    last_seen: Optional[datetime] = Field(
        default=None, validation_alias=AliasChoices("last_seen", "Time")
    )


class Availability(BaseModel):
    """
    Represents the availability status of a device.

    Attributes:
        is_online (bool): Indicates whether the device is online. This field is immutable.
    """

    is_online: bool = Field(frozen=True)


class Registry(BaseModel):
    """
    Represents a registry of dicovered devices.

    Attributes:
        device_ids (List[str]): A list of device ids.
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
        power_on_behavior (Optional[str]): The behavior of the switch when power is restored.
        power (str): The current power state of the switch: "ON" or "OFF"
            This field can be accessed using aliases "power", "state", or "POWER".
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
        power1 (str): The current power state of the first channel: "ON" or "OFF"
            This field can be accessed using aliases "power1" or "POWER1".
        power2 (str): The current power state of the second channel: "ON" or "OFF"
            This field can be accessed using aliases "power2" or "POWER2".
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
        Range (Optional[float]): The range value of the ADC.
        voltage (float): The computed voltage based on the range value.
    """

    Range: Optional[float] = Field(default=None)

    @computed_field
    @property
    def voltage(self) -> float:
        """
        Calculate the voltage based on the range.

        Returns:
            float: The calculated voltage in volts.
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
