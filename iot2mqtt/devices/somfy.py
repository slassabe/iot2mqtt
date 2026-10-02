# coding=utf-8

"""
Somfy device registrations (ESPSomfy protocol).

Registers Somfy RTS motorized shades via ESPSomfy-RTS bridge:
  - Position and tilt control
  - Wind/sun detection and response
  - Target presets

Enables automated window covering management.
"""

from iot2mqtt import abstract, dev, registry
from iot2mqtt.devices import fields
from iot2mqtt.devices.somfy_abstract import SomfyShade

SOMFY_SHADES_TAG = "ESPSomfy-RTS MQTT"

SOMFY_SHADES_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SOMFY_SHADES_TAG,
    device_state_class=SomfyShade,
    protocol=dev.Protocol.ESPSOMFY,
)
registry.DeviceRegistry.register_encoder(
    SOMFY_SHADES_TAG,
    settable_fields=[
        fields.DIRECTION,
        fields.MYPOS,
        fields.MYTILTPOS,
        fields.POSITION,
        fields.SUNFLAG,
        fields.SUNNY,
        fields.TARGET,
        fields.TILTPOSITION,
        fields.TILTTARGET,
        fields.WINDY,
    ],
    gettable_fields=[],
    field_aliases={fields.POWER: fields.STATE},
)
