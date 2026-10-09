# coding=utf-8

"""
Shelly device registrations (WiFi protocol).

Registers Shelly smart home devices for MQTT bridge integration via native
Shelly protocol: smart plugs and multi-channel relays/dimmers.
"""

from iot2mqtt import dev, registry
from iot2mqtt.devices.common_abstract import Switch, Switch2Channels

SHELLY_PLUGS_TAG = "Shelly Plug S"  # Shelly Plug S WiFi smart plug

SHELLY_PLUGS_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SHELLY_PLUGS_TAG, device_state_class=Switch, protocol=dev.Protocol.SHELLY
)
registry.DeviceRegistry.register_encoder(
    SHELLY_PLUGS_TAG,
    settable_fields=["Power"],
    gettable_fields=["Power"],
    field_aliases={"power": "Power"},
)

SHELLY_UNI_TAG = "Shelly Uni"  # Shelly Uni WiFi relay/dimmer

SHELLY_UNI_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SHELLY_UNI_TAG,
    device_state_class=Switch2Channels,
    protocol=dev.Protocol.SHELLY,
)
registry.DeviceRegistry.register_encoder(
    SHELLY_UNI_TAG,
    settable_fields=["Power1", "Power2"],
    gettable_fields=["Power1", "Power2"],
    field_aliases={"power1": "Power1", "power2": "Power2"},
)
