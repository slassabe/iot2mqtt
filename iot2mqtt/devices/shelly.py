# coding=utf-8

"""
Shelly device registrations (WiFi protocol).

Registers Shelly smart home devices:
  - Shelly Plug S: WiFi smart plug
  - Shelly Uni: WiFi relay/dimmer with dual channels

Devices communicate via native Shelly protocol through MQTT bridge.
"""

from iot2mqtt import abstract, dev, registry

SHELLY_PLUGS_TAG = "Shelly Plug S"  # Shelly Plug S WiFi smart plug

SHELLY_PLUGS_MODEL = registry.DeviceRegistry.register_state(
    model_tag=SHELLY_PLUGS_TAG, device_state_class=abstract.Switch, protocol=dev.Protocol.SHELLY
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
    device_state_class=abstract.Switch2Channels,
    protocol=dev.Protocol.SHELLY,
)
registry.DeviceRegistry.register_encoder(
    SHELLY_UNI_TAG,
    settable_fields=["Power1", "Power2"],
    gettable_fields=["Power1", "Power2"],
    field_aliases={"power1": "Power1", "power2": "Power2"},
)
