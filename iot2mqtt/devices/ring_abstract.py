# coding=utf-8


#
# Ring abstract devices
#

from datetime import datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    field_validator,
)


class RingDeviceState(BaseModel):
    """
    Represents the state of a Ring device.
    """

    pass


class MotionInfo(RingDeviceState):
    """
    Represents the state of a motion sensor device.
    """

    last_motion_time: Optional[str] = None
    detection_enabled: Optional[bool] = None


class StreamAttributes(RingDeviceState):
    status: Optional[Literal["inactive", "activating", "active", "failed"]] = None


class MotionAttributes(RingDeviceState):
    """
    Represents the state of a motion sensor device.
    """

    # {'motion_attributes': {'lastMotion': 1739625899,
    #                        'lastMotionTime': '2025-02-15T13:24:59Z',
    #                        'personDetected': False, 'motionDetectionEnabled': True}}
    lastMotion: Optional[int] = None
    lastMotionTime: Optional[datetime] = None
    personDetected: Optional[bool] = None
    motionDetectionEnabled: Optional[bool] = None

    @field_validator("lastMotionTime", mode="before")
    @classmethod
    def _coerce_last_motion_time(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip().lower() in {"none", "", "null", "undefined"}:
            return None
        return v


class BatteryAttributes(RingDeviceState):
    """Represents the state of a battery device."""

    # Get battery level (0-100)
    batteryLevel: Optional[int] = None
    batteryLife: Optional[int] = None
    batteryLife2: Optional[int] = None


class WirelessAttributes(RingDeviceState):
    wirelessNetwork: Optional[str] = None
    wirelessSignal: Optional[int] = None


class EventSelectAttributes(RingDeviceState):
    # {"recordingUrl":"https://www.sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
    #  "eventId":"1234"}
    recordingUrl: Optional[str] = None
    eventId: Optional[int] = None


class DingAttributes(RingDeviceState):
    #  {'ding_attributes': {'lastDing': 1741776527,
    #                       'lastDingTime': '2025-03-12T10:48:47Z'}}
    lastDing: Optional[int] = None
    lastDingTime: Optional[datetime] = None

    @field_validator("lastDingTime", mode="before")
    @classmethod
    def _coerce_last_ding_time(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip().lower() in {"none", "", "null", "undefined"}:
            return None
        return v


class SnapshotAttributes(RingDeviceState):
    # {'snapshot_attributes': {'timestamp': 1739874181, 'type': 'interval'}}
    timestamp: Optional[int] = None
    type: Optional[str] = None


class RingInfo(RingDeviceState):
    # {'info': RingInfo(last_seen=None,
    #       stream_Source='rtsp://172.18.0.6:8554/187f8877c231_live',
    #       still_Image_URL='https://localhost:8123{{ 
    #          states.camera.rez-de-chaussée_snapshot.attributes.entity_picture 
    #       }}')}
    stream_Source: Optional[str] = None
    still_Image_URL: Optional[str] = None


class Camera(RingDeviceState):
    """Represents the state of a camera device."""

    # Doorbell Ding Detected
    ding: Optional[bool] = None
    # Last ding time
    # ring/<location_id>/camera/<device_id>/ding/attributes
    ding_attributes: Optional[DingAttributes] = None
    # Motion Detected
    motion: Optional[bool] = None
    # Last motion time, person/motion detection enabled
    # ring/<location_id>/camera/<device_id>/motion/attributes
    motion_attributes: Optional[MotionAttributes] = None
    # Get/set motion detection ON/OFF
    motion_detection: Optional[bool] = None
    # Get/set motion warning ON/OFF
    motion_warning: Optional[bool] = None
    # Get/set light ON/OFF
    light: Optional[bool] = None
    # Get/set siren ON/OFF
    siren: Optional[bool] = None
    # Device info sensor
    info: Optional[RingInfo] = None
    # Snapshot images (JPEG binary data)
    # ring/<location_id>/camera/<device_id>/snapshot/image
    # {'snapshot_image': b'\xff\xd8\xff'}
    snapshot_image: Optional[bytes] = None
    # JSON attributes for image (timestamp)
    # ring/<location_id>/camera/<device_id>/snapshot/attributes
    snapshot_attributes: Optional[SnapshotAttributes] = None
    # Get/set snapshot refresh interval (10-604800)
    snapshot_interval: Optional[int] = None
    # Get/set live stream ON/OFF
    stream: Optional[bool] = None
    # Detailed live stream state:
    # ring/<location_id>/camera/<device_id>/stream/attributes
    stream_attributes: Optional[StreamAttributes] = None
    # Get/set event stream ON/OFF
    event_stream: Optional[bool] = None
    # Detailed event stream state:
    # ring/<location_id>/camera/<device_id>/event_stream/attributes
    event_stream_attributes: Optional[StreamAttributes] = None
    # Get/set selected event stream
    event_select: Optional[str] = None
    #
    # Undocumented Attributes
    #
    battery_attributes: Optional[BatteryAttributes] = None
    wireless_attributes: Optional[WirelessAttributes] = None
    # ring/<location_id>/camera/<device_id>/event_select/attributes
    event_select_attributes: Optional[EventSelectAttributes] = None


class Chime(RingDeviceState):
    """Represents the state of a chime device."""

    # Get/set volume (0-11)
    volume: Optional[int] = None
    # Get/set snooze state (ON = snooze)
    snooze: Optional[bool] = None
    # Get/set current minutes to snooze (1-1440)
    snooze_minutes: Optional[int] = None
    # Get/set ding sound (ON = Play ding chime)
    play_ding_sound: Optional[bool] = None
    # Get/set Motion chime (ON = Play ding chime)
    play_motion_sound: Optional[bool] = None
    # Get device info sensor
    info: Optional[RingInfo] = None
    # Undocumented Attributes
    wireless_attributes: Optional[WirelessAttributes] = None


class RingAlarm(RingDeviceState):
    """
    Modes Control Panel

    Virtual alarm control panel for setting Ring location modes for locations
    with Ring cameras but not Ring alarm.
    """

    # {'mode': 'armed_home'}
    mode: Optional[Literal["disarmed", "armed_home", "armed_away"]] = None


__all__ = [
    "RingDeviceState",
    "MotionInfo",
    "StreamAttributes",
    "MotionAttributes",
    "BatteryAttributes",
    "WirelessAttributes",
    "EventSelectAttributes",
    "DingAttributes",
    "SnapshotAttributes",
    "RingInfo",
    "Camera",
    "Chime",
    "RingAlarm",
]
