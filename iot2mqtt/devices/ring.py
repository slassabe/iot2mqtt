# coding=utf-8
"""
Ring device registrations (Ring Bridge protocol).

Registers Ring security devices via ring-mqtt bridge:
  - RingAlarm: Security system control
  - RingCamera: Video doorbell with motion/sound
  - RingChime: Indoor chime notification hub

Provides bidirectional control for smart home integration.
"""

from iot2mqtt import abstract, dev, registry
from iot2mqtt.devices import fields

#
RING_ALARM_TAG = "alarm"
RING_ALARM_MODEL = registry.DeviceRegistry.register_state(
    model_tag=RING_ALARM_TAG, device_state_class=abstract.RingAlarm, protocol=dev.Protocol.RING
)
registry.DeviceRegistry.register_encoder(
    RING_ALARM_TAG,
    settable_fields=[fields.MODE],
    gettable_fields=[],
)
#
RING_CAMERA_TAG = "camera"
RING_CAMERA_MODEL = registry.DeviceRegistry.register_state(
    model_tag=RING_CAMERA_TAG, device_state_class=abstract.Camera, protocol=dev.Protocol.RING
)
registry.DeviceRegistry.register_encoder(
    RING_CAMERA_TAG,
    settable_fields=[
        fields.LIGHT,
        fields.MOTION_DETECTION,
        fields.MOTION_WARNING,
        fields.SIREN,
        fields.SNAPSHOT_INTERVAL,
        fields.STREAM,
    ],
    gettable_fields=[],
)
#
RING_CHIME_TAG = "chime"
RING_CHIME_MODEL = registry.DeviceRegistry.register_state(
    model_tag=RING_CHIME_TAG, device_state_class=abstract.Chime, protocol=dev.Protocol.RING
)
registry.DeviceRegistry.register_encoder(
    RING_CHIME_TAG,
    settable_fields=[fields.PLAY_MOTION_SOUND, fields.SNOOZE, fields.SNOOZE_MINUTES],
    gettable_fields=[],
)
