# coding=utf-8

from typing import Optional, Union

from pydantic import (
    BeforeValidator,
)
from typing_extensions import Annotated

from iot2mqtt.core import exceptions
from iot2mqtt.devices.common_abstract import DeviceState


def _validate_somfy_value(value: any, expected_type) -> any:
    if value != "":
        return expected_type(value)
    else:
        raise exceptions.NoValueException(expected_type)


SomfyInt = Annotated[
    Union[int, str, None], BeforeValidator(lambda v: _validate_somfy_value(v, int))
]
SomfyBool = Annotated[
    Union[bool, str, None], BeforeValidator(lambda v: _validate_somfy_value(v, bool))
]


class SomfyDevice(DeviceState):
    """
    Represents the state of a Somfy RTS device.
    """

    name: Optional[str] = None
    remoteAddress: Optional[str] = None
    # The current direction of the motor movement. This will be one of the following values :
    # -1 = The shade is moving up, 0 = The shade is stopped, 1 = The shade is moving down
    direction: SomfyInt = None
    # The last rolling code that was used to send the last command from ESPSomfy RTS
    lastRollingCode: SomfyInt = None
    # Indicates the existence of a sun sensor. Valid values are true or false
    sunSensor: SomfyBool = None
    # Indicates whether the sun sensor is enabled or not. Valid values are 0 or 1
    sunFlag: SomfyInt = None
    # Indicates whether the shade thinks it is sunny or not. Valid values are 0 or 1
    sunny: SomfyInt = None
    # Indicates whether the shade thinks it is windy or calm. Valid values are 0 or 1
    windy: SomfyInt = None


class SomfyGroup(SomfyDevice):
    groupId: Optional[int] = None


class SomfyShade(SomfyDevice):
    # shadeId: Optional[int] = None
    shadeId: SomfyInt = None
    shadeType: SomfyInt = None
    # The tilt type if the shade type is blind :
    # 0 = None, 1 = Tilt Motor, 2 = Integrated Tilt, 3 = Tilt Only
    tiltType: SomfyInt = None
    # Indicates whether up is down and down is up.
    flipCommands: SomfyBool = None
    # Indicates whether 100% is open or closed. Valid values are true or false
    flipPosition: SomfyBool = None
    # The current lift position in percentage of the motor.
    position: SomfyInt = None
    # The current tilt position in percentage of the motor.
    tiltPosition: SomfyInt = None
    # The lift position that the shade is seeking
    target: SomfyInt = None
    # The tilt position that the shade is seeking
    tiltTarget: SomfyInt = None
    # The current favorite lift position. -1 is unset
    mypos: SomfyInt = None
    # The current favorite tilt position. -1 is unset
    myTiltPos: SomfyInt = None

    # Undocumented
    cmd: Optional[str] = None
    cmdAddress: Optional[str] = None
    cmdSource: Optional[str] = None


__all__ = [
    "SomfyDevice",
    "SomfyGroup",
    "SomfyShade",
    "SomfyInt",
    "SomfyBool",
]
