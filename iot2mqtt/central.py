# coding=utf-8

"""
MQTT message processing and device control for IoT devices.

Manages MQTT topic subscriptions, message formatting, processing, and device
state retrieval/control across multiple protocols (Zigbee2MQTT, Tasmota, ESPSomfy, Ring).
"""

import json
import sys
import time
from abc import ABC, abstractmethod
from enum import Enum
from queue import Full, Queue
from typing import Any, Callable, Dict, List, Optional, Type, Union

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

import paho.mqtt.client as mqtt

from iot2mqtt import dev, devices, encoder, messenger, processor, topics
from iot2mqtt.core import mqtthelper, utils
from iot2mqtt.devices.common_abstract import SWITCH_OFF, SWITCH_ON

DEFAULT_ON_TIME = 0.0
DEFAULT_OFF_TIME = 0.0
QUEUE_TIMEOUT = 1  # write on queue timeout in seconds

_UNSUPPORTED_MODEL_LOGGED: set = set()  # models already warned about missing encoder

Parser: TypeAlias = Callable[..., Optional[messenger.Item]]
DataItem: TypeAlias = Union[Dict, str, int, List[Dict]]


class MessageStructure(Enum):
    """Message format types for MQTT parsing."""

    JSON = "json"
    RAW = "raw"
    ESPSOMFY = "espsomfy"
    RING = "ring"


class MessageFormater(ABC):
    """Abstract base class for formatting incoming MQTT messages.

    Subclasses implement format-specific parsing logic for different protocols.
    """

    @staticmethod
    @abstractmethod
    def modify_incoming_message(
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        raw_payload: str,
    ) -> Optional[DataItem]:
        """Parse incoming message according to protocol and message type."""
        pass


class JsonMessageFormater(MessageFormater):
    """Format incoming JSON MQTT messages."""

    @staticmethod
    def modify_incoming_message(
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        raw_payload: str,
    ) -> Optional[DataItem]:
        # Called by :
        # - zigbee2mqtt state messages : _on_z2m_state
        # - Tasmota state messages : _on_tasmota_state
        # - zigbee2mqtt discovery messages : _on_z2m_disco
        # - Tasmota discovery messages: _on_tasmota_disco
        try:
            return json.loads(raw_payload)
        except json.JSONDecodeError:
            return raw_payload


class RawMessageFormater(MessageFormater):
    """Format incoming raw text MQTT messages."""

    @staticmethod
    def modify_incoming_message(
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        raw_payload: str,
    ) -> Optional[DataItem]:
        # Called by :
        # - Tasmota availability messages: _on_tasmota_avail
        # - ESPSomfy availability messages: _on_espsomfy_avail
        return raw_payload


class ESPSomfyMessageFormater(MessageFormater):
    """Format incoming ESPSomfy STATE and DISCO MQTT messages."""

    @staticmethod
    def modify_incoming_message(
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        raw_payload: str,
    ) -> Optional[DataItem]:
        # Called by :
        # - ESPSomfy state messages: _on_espsomfy_state
        # - ESPSomfy discovery messages : _on_espsomfy_disco
        key = topics.InfoTopicManager().get_wildcard_by_position(
            protocol=protocol, message_type=message_type, topic=topic, position=1
        )
        if message_type == messenger.MessageType.DISCO:
            value = json.loads(raw_payload)
        else:
            value = raw_payload
        return {key: value}


class RingTags(Enum):
    """Ring MQTT topic component tags."""

    STATE = "state"
    INFO = "info"
    ATTRIBUTES = "attributes"
    IMAGE = "image"
    COMMAND = "command"


class RingMessageFormater(MessageFormater):
    """
    Format incoming Ring STATE messages.

    <topic_tag> : "state" | "info" | "attributes" | "image" | "command"
    <category> (RING abstract classes) : "alarm" | "camera" | "chime"
    <attribute> : attribute defined in abstract.py

    - ring/<location_id>/<category>/<device_id>/<attribute>/state
    - ring/<location_id>/<category>/<device_id>/<attribute>/info
    - ring/<location_id>/<category>/<device_id>/<attribute>/attributes
    - ring/<location_id>/<category>/<device_id>/<attribute>/image
    - ring/<location_id>/<category>/<device_id>/<attribute>/command
    """

    TOPIC_TAG_POSITION = 4
    ATTRIBUTE_POSITION = 3

    @staticmethod
    def modify_incoming_message(
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        raw_payload: Union[str, bytes],
    ) -> Optional[DataItem]:
        # Called by :
        # - RING state messages: _on_ring_state
        if not isinstance(raw_payload, (str, bytes)):
            utils.i2m_log.error("Invalid payload type: %s", type(raw_payload))
            return None
        _topic_tag = topics.InfoTopicManager().get_wildcard_by_position(
            protocol=protocol,
            message_type=message_type,
            topic=topic,
            position=RingMessageFormater.TOPIC_TAG_POSITION,
        )
        _attribute = topics.InfoTopicManager().get_wildcard_by_position(
            protocol=protocol,
            message_type=message_type,
            topic=topic,
            position=RingMessageFormater.ATTRIBUTE_POSITION,
        )
        return RingMessageFormater._handle_message(
            topic_tag=_topic_tag, attribute=_attribute, raw_payload=raw_payload
        )

    @staticmethod
    def _handle_message(
        topic_tag: str, attribute: str, raw_payload: Union[str, bytes]
    ) -> Optional[DataItem]:
        def _to_json(payload: str) -> Optional[Dict[str, Any]]:
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return None

        if topic_tag == RingTags.COMMAND.value:
            # Dismissing echo sending command messages
            return None
        if topic_tag == RingTags.STATE.value:
            _key = attribute
            if attribute == RingTags.INFO.value:
                _json_payload = _to_json(raw_payload)
                if _json_payload is not None:
                    raw_payload = _json_payload
        elif topic_tag == RingTags.ATTRIBUTES.value:
            _key = f"{attribute}_{topic_tag}"
            _json_payload = _to_json(raw_payload)
            if _json_payload is not None:
                raw_payload = _json_payload
            else:
                return None
        elif topic_tag == RingTags.IMAGE.value:
            _key = f"{attribute}_{topic_tag}"
        else:
            utils.i2m_log.warning("Dismissing RING device message with topic tag: %s", topic_tag)
            return None
        return {_key: raw_payload}


class Scrutinizer:
    """Subscribe to MQTT topics and process incoming messages into output queue.

    Manages topic subscriptions for multiple protocols and routes messages through
    the appropriate formatter based on protocol and message type.
    """

    # Reference to Frank Zappa - The Central Scrutinizer ❤

    def __init__(
        self,
        mqtt_client: mqtthelper.ClientHelper,
        output_queue: Queue,
        protocols_expected: Optional[List[dev.Protocol]] = None,
        queue_timeout: int = QUEUE_TIMEOUT,  # timeout in sec.
    ) -> None:
        self._mqtt_client = mqtt_client
        self._output_queue = output_queue
        self._queue_timeout = queue_timeout
        self._metrics_collector = utils.MetricsCollector()
        self._formaters: dict[MessageStructure, Type[MessageFormater]] = {
            MessageStructure.JSON: JsonMessageFormater,
            MessageStructure.RAW: RawMessageFormater,
            MessageStructure.ESPSOMFY: ESPSomfyMessageFormater,
            MessageStructure.RING: RingMessageFormater,
        }
        # Listen all supported protocols by default
        _protocols = protocols_expected or dev.Protocol.supported()
        devices.load_devices_for_protocols(_protocols)
        self._subscribe_to_topics(_protocols)

    def _get_formater(self, message_structure: MessageStructure) -> Callable:
        return self._formaters[message_structure].modify_incoming_message

    def _subscribe_to_topics(self, protocols_expected) -> None:
        def _callback_add(
            protocol: dev.Protocol,
            message_type: messenger.MessageType,
            callback: Callable[[messenger.Message], None],
        ) -> None:
            _topic = topics.InfoTopicManager().get_topic_to_subscribe(protocol, message_type)
            self._mqtt_client.message_callback_add(_topic, callback)

        _avail = messenger.MessageType.AVAIL
        _state = messenger.MessageType.STATE
        _disco = messenger.MessageType.DISCO
        _z2m_proto = dev.Protocol.Z2M
        _tasmota_proto = dev.Protocol.TASMOTA
        _espsomfy_proto = dev.Protocol.ESPSOMFY
        _ring_proto = dev.Protocol.RING

        if _z2m_proto in protocols_expected:
            _callback_add(_z2m_proto, _disco, self._on_z2m_disco)
            _callback_add(_z2m_proto, _avail, self._on_z2m_avail)
            _callback_add(_z2m_proto, _state, self._on_z2m_state)

        if _tasmota_proto in protocols_expected:
            _callback_add(_tasmota_proto, _disco, self._on_tasmota_disco)
            _callback_add(_tasmota_proto, _avail, self._on_tasmota_avail)
            _callback_add(_tasmota_proto, _state, self._on_tasmota_state)

        if _espsomfy_proto in protocols_expected:
            _callback_add(_espsomfy_proto, _disco, self._on_espsomfy_disco)
            _callback_add(_espsomfy_proto, _avail, self._on_espsomfy_avail)
            _callback_add(_espsomfy_proto, _state, self._on_espsomfy_state)

        if _ring_proto in protocols_expected:
            _callback_add(_ring_proto, _avail, self._on_ring_avail)
            _callback_add(_ring_proto, _state, self._on_ring_state)
        # Set connection handler
        self._mqtt_client.connect_handler_add(self._on_connect)

        # IMPORTANT: If already connected (e.g. Docker/Linux where TCP handshake
        # completes before Scrutinizer is instantiated), on_connect will never fire.
        # Must subscribe immediately in this case.
        if self._mqtt_client.is_connected():
            utils.i2m_log.debug("Already connected - subscribing immediately")
            for _topic in topics.InfoTopicManager().get_all_topics_to_subscribe():
                utils.i2m_log.debug("Subscribing to %s", _topic)
                self._mqtt_client.subscribe(_topic)

    def _process_message(
        self,
        client: mqtt.Client,  # pylint: disable=unused-argument
        userdata: Any,  # pylint: disable=unused-argument
        mqtt_message: mqtt.MQTTMessage,
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        target_message_structure: MessageStructure,
    ) -> None:
        """Process incoming MQTT message and queue the result.

        Formats the raw payload, extracts device and model information from the topic,
        and places the processed message into the output queue.
        """
        topic = mqtt_message.topic
        try:
            _raw_payload = str(mqtt_message.payload.decode("utf-8"))
        except UnicodeDecodeError:
            _raw_payload = mqtt_message.payload
        if _raw_payload is None:
            utils.i2m_log.info("Received empty message on topic %s", topic)
            return

        _data = self._get_formater(target_message_structure)(
            protocol=protocol,
            message_type=message_type,
            topic=topic,
            raw_payload=_raw_payload,
        )
        if _data is None:
            return

        _item = messenger.Item(data=_data)
        _device_id = topics.InfoTopicManager().get_device_id(
            protocol=protocol,
            message_type=message_type,
            topic=topic,
        )
        _model = topics.InfoTopicManager().get_model(
            protocol=protocol,
            message_type=message_type,
            topic=topic,
        )
        _incoming = messenger.Message(
            topic=topic,
            protocol=protocol,
            model=_model,
            device_id=_device_id,
            message_type=message_type,
            raw_item=_item,
        )
        try:
            self._output_queue.put(_incoming, block=True, timeout=self._queue_timeout)
        except Full:
            utils.i2m_log.error("Output queue is full. Dropping message for topic %s", topic)

    def _on_z2m_avail(self, *argc, **kwargs) -> None:
        """Handle Zigbee2MQTT availability messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.AVAIL,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_tasmota_avail(self, *argc, **kwargs) -> None:
        """Handle Tasmota availability messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.AVAIL,
            target_message_structure=MessageStructure.RAW,
        )

    def _on_espsomfy_avail(self, *argc, **kwargs) -> None:
        """Handle ESPSomfy availability messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.ESPSOMFY,
            message_type=messenger.MessageType.AVAIL,
            target_message_structure=MessageStructure.RAW,
        )

    def _on_ring_avail(self, *argc, **kwargs) -> None:
        """Handle Ring availability messages and trigger discovery."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.RING,
            message_type=messenger.MessageType.AVAIL,
            target_message_structure=MessageStructure.RAW,
        )
        # RING device don't have DISCO message, so we need to send a DISCO message
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.RING,
            message_type=messenger.MessageType.DISCO,
            target_message_structure=MessageStructure.RAW,
        )

    def _on_z2m_state(self, *argc, **kwargs) -> None:
        """Handle Zigbee2MQTT state messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.STATE,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_tasmota_state(self, *argc, **kwargs) -> None:
        """Handle Tasmota state messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.STATE,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_espsomfy_state(self, *argc, **kwargs) -> None:
        """Handle ESPSomfy state messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.ESPSOMFY,
            message_type=messenger.MessageType.STATE,
            target_message_structure=MessageStructure.ESPSOMFY,
        )

    def _on_ring_state(self, *argc, **kwargs) -> None:
        """Handle Ring state messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.RING,
            message_type=messenger.MessageType.STATE,
            target_message_structure=MessageStructure.RING,
        )

    def _on_z2m_disco(self, *argc, **kwargs) -> None:
        """Handle Zigbee2MQTT discovery messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.DISCO,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_tasmota_disco(self, *argc, **kwargs) -> None:
        """Handle Tasmota discovery messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.DISCO,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_espsomfy_disco(self, *argc, **kwargs) -> None:
        """Handle ESPSomfy discovery messages."""
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.ESPSOMFY,
            message_type=messenger.MessageType.DISCO,
            target_message_structure=MessageStructure.ESPSOMFY,
        )

    def _on_connect(  # pylint: disable=too-many-arguments
        self,
        client: mqtt.Client,
        userdata: Any,  # pylint: disable=unused-argument
        flags: Any,  # pylint: disable=unused-argument
        reason_code: Any,  # pylint: disable=unused-argument
        properties: Any,  # pylint: disable=unused-argument
    ) -> None:
        """Subscribes to MQTT topics on connection."""
        for _topic in topics.InfoTopicManager().get_all_topics_to_subscribe():
            utils.i2m_log.debug("Subscribing to %s", _topic)
            client.subscribe(_topic)


class DeviceAccessor:
    """Access and control device state via MQTT.

    Publishes state retrieval and state change commands to the appropriate MQTT topics
    based on the device model and protocol.
    """

    RETRY_COUNT_MAX = 3
    RETRY_ELAPSE = 60  # seconds

    _timer_mgr = utils.TimerManager()

    def __init__(self, mqtt_client: mqtthelper.ClientHelper) -> None:
        self._mqtt_client = mqtt_client

    def trigger_get_state(self, device_id: str, protocol: dev.Protocol, model: dev.Model) -> None:
        """Publish state retrieval commands for a device.

        Uses the encoder registry to get gettable fields and constructs the appropriate
        MQTT topics for the given protocol.

        Args:
            device_id: Device identifier.
            protocol: Communication protocol (Z2M, TASMOTA, ESPSOMFY, or RING).
            model: Device model.

        Raises:
            NotImplementedError: If protocol is unknown.
        """

        def _publish_it(topic: str, payload: str) -> None:
            # The debug log for publishing state retrieval is commented out to reduce verbosity
            # in the logs.
            # utils.i2m_log.debug(
            #     "Publishing state retrieval to %s - state : %s", topic, payload
            # )
            self._mqtt_client.publish(topic, payload=payload, qos=1, retain=False)
            return

        _command_base_topic = topics.CommandTopicManager().get_command_base_topic(protocol)
        _encoder = encoder.EncoderRegistry.get_encoder(model=model)
        if _encoder is None:
            if model not in _UNSUPPORTED_MODEL_LOGGED:
                utils.i2m_log.debug(
                    "No encoder for model %s — state polling skipped for all instances",
                    model,
                )
                _UNSUPPORTED_MODEL_LOGGED.add(model)
            return
        _fields = _encoder.gettable_fields
        if protocol == dev.Protocol.Z2M:
            _command_topic = f"{_command_base_topic}/{device_id}/get"
            _pl = {_field: "" for _field in _fields}
            _command_payload = json.dumps(_pl)
            _publish_it(_command_topic, _command_payload)
            return
        if protocol in [dev.Protocol.TASMOTA, dev.Protocol.ESPSOMFY, dev.Protocol.RING]:
            for _field in _fields:
                _command_topic = f"{_command_base_topic}/{device_id}/{_field}"
                _command_payload = ""
                _publish_it(_command_topic, _command_payload)
            return
        _error_msg = f"Unknown protocol {protocol}"
        raise NotImplementedError(_error_msg)

    def trigger_change_state(self, device_id: str, protocol: dev.Protocol, state: Dict) -> None:
        """Publish state change commands for a device.

        Constructs MQTT command topics based on protocol and publishes the new state.

        Args:
            device_id: Device identifier.
            protocol: Communication protocol (Z2M, TASMOTA, or ESPSOMFY).
            state: Dictionary of state changes to apply.

        Raises:
            NotImplementedError: If protocol is unknown.
        """

        def _publish_it(topic: str, payload: str) -> None:
            utils.i2m_log.debug("Publishing state change to %s - state : %s", topic, payload)
            self._mqtt_client.publish(topic, payload=payload, qos=1, retain=False)
            return

        _command_base_topic = topics.CommandTopicManager().get_command_base_topic(protocol)
        _json_state = json.dumps(state)
        if protocol == dev.Protocol.Z2M:
            _command_topic = f"{_command_base_topic}/{device_id}/set"
            _publish_it(_command_topic, _json_state)
            return
        if protocol == dev.Protocol.TASMOTA:
            for _key, _value in state.items():
                _command_topic = f"{_command_base_topic}/{device_id}/{_key}"
                _publish_it(_command_topic, _value)
            return
        if protocol == dev.Protocol.ESPSOMFY:
            for _key, _value in state.items():
                _command_topic = f"{_command_base_topic}/{device_id}/{_key}/set"
                _publish_it(_command_topic, _value)
            return
        _error_msg = f"Unknown protocol {protocol}"
        raise NotImplementedError(_error_msg)

    def ring_trigger_change_state(
        self,
        device_id: str,
        protocol: dev.Protocol,
        state: Dict,
        location_id: str,
        model: str,
    ) -> None:
        """Publish state changes for Ring devices to MQTT topics.

        Args:
            device_id: Ring device identifier.
            protocol: Must be Protocol.RING.
            state: State changes to apply.
            location_id: Ring location identifier.
            model: Ring device model/category.

        Raises:
            ValueError: If device_id, location_id, or model are empty, or protocol is not RING.

        Topic format: <base_topic>/<location_id>/<model>/<device_id>/<state_key>/command
        """

        def _publish_it(topic: str, payload: str) -> None:
            utils.i2m_log.debug("Publishing state change to %s - state : %s", topic, payload)
            self._mqtt_client.publish(topic, payload=payload, qos=1, retain=False)
            return

        if not device_id or not location_id or not model:
            _msg = (
                f"device_id: {device_id}, location_id: {location_id} /"
                f"and model: {location_id} must not be empty"
            )
            raise ValueError(_msg)

        _command_base_topic = topics.CommandTopicManager().get_command_base_topic(protocol)
        if protocol == dev.Protocol.RING:
            for _key, _value in state.items():
                _command_topic = (
                    f"{_command_base_topic}/{location_id}/" f"{model}/{device_id}/{_key}/command"
                )
                _publish_it(_command_topic, _value)
            return
        _error_msg = f"Protocol {protocol} is not permitted for Ring devices"
        raise ValueError(_error_msg)

    def _do_trigger_change_state_helper(
        self,
        device_id: str,
        state: Dict,
        retry_count: int = 0,
    ) -> None:
        _device: Optional[dev.RingDevice] = processor.DeviceDirectory.get_device(device_id)
        if _device is None:
            scheduled = utils.retry_with_timer(
                self._timer_mgr,
                key=device_id,
                countdown_base=self.RETRY_ELAPSE,
                max_retries=self.RETRY_COUNT_MAX,
                task=self._do_trigger_change_state_helper,
                retry_count=retry_count,
                kwargs={"device_id": device_id, "state": state},
            )
            if not scheduled:
                utils.i2m_log.error("[%s] device not found: abort", device_id)
            return
        if _device.protocol == dev.Protocol.RING:
            self.ring_trigger_change_state(
                device_id=device_id,
                protocol=_device.protocol,
                state=state,
                location_id=_device.location_id,
                model=_device.model,
            )
            return
        if _device.protocol in [dev.Protocol.TASMOTA, dev.Protocol.ESPSOMFY]:
            self.trigger_change_state(
                device_id=device_id,
                protocol=_device.protocol,
                state=state,
            )
            return
        _error_msg = f"Unknown protocol {_device.protocol}"
        raise NotImplementedError(_error_msg)

    def trigger_change_state_helper(
        self,
        device_ids: str,
        state: Dict,
    ) -> None:
        """Trigger state changes for multiple devices by ID.

        Args:
            device_ids: Comma-separated device ID string.
            state: State changes to apply to each device.
        """
        for _device_id in device_ids.split(","):
            self._do_trigger_change_state_helper(
                device_id=_device_id,
                state=state,
                retry_count=0,
            )

    def _do_switch_power(
        self,
        device_id: str,
        protocol: dev.Protocol,
        model: dev.Model,
        power_on: bool,
    ) -> None:
        self.trigger_change_state(
            device_id=device_id,
            protocol=protocol,
            state=encoder.encode(model, SWITCH_ON if power_on else SWITCH_OFF),
        )

    def _do_switch_power_change(
        self,
        device_id: str,
        protocol: dev.Protocol,
        model: dev.Model,
        power_on: bool,
        countdown: float,
        on_time: float,
        off_time: float,
    ) -> None:
        # This method performs the following steps:
        # 1. If a countdown is specified (countdown != 0), it schedules the power state change to
        #    occurafter the countdown period. It uses the TimerManager to manage the countdown and
        #    calls switch_power_change again with countdown set to 0.
        # 2. If no countdown is specified, it immediately changes the power state of the device by
        #    calling the _do_switch_power method.
        # 3. If the device is being turned on and an on_time is specified (on_time > 0), it
        #    schedules the device to be turned off after the on_time period using the TimerManager
        # 4. If the device is being turned off and an off_time is specified (off_time > 0), it
        #    schedules the device to be turned on after the off_time period using the TimerManager

        def _manage_timer_helper(_power_on: bool, _countdown: bool) -> None:
            _params = {
                "device_id": device_id,
                "protocol": protocol,
                "model": model,
                "power_on": _power_on,
            }
            self._timer_mgr.create_timer(
                device_id=device_id,
                countdown=_countdown,
                task=self._do_switch_power,
                kwargs=_params,
            )

        if countdown != 0:
            _params = {
                "device_ids": device_id,
                "protocol": protocol,
                "model": model,
                "power_on": power_on,
                "countdown": 0,
                "on_time": on_time,
                "off_time": off_time,
            }
            self._timer_mgr.create_timer(
                device_id=device_id,
                countdown=countdown,
                task=self.switch_power_change,
                kwargs=_params,
            )
        else:
            self._do_switch_power(
                device_id=device_id,
                protocol=protocol,
                model=model,
                power_on=power_on,
            )
            if power_on and on_time > 0:
                _manage_timer_helper(_power_on=False, _countdown=on_time)
            elif not power_on and off_time > 0:
                _manage_timer_helper(_power_on=True, _countdown=off_time)

    def switch_power_change(
        self,
        device_ids: str,
        protocol: dev.Protocol,
        model: dev.Model,
        power_on: bool,
        countdown: float = 0,
        on_time: float = DEFAULT_ON_TIME,
        off_time: float = DEFAULT_OFF_TIME,
    ) -> None:
        """Manage power state changes for switch devices.

        Handles immediate or delayed power state changes with optional on/off duration timers.

        Args:
            device_ids: Comma-separated device ID string.
            protocol: Device protocol.
            model: Device model.
            power_on: Desired power state (True for ON, False for OFF).
            countdown: Delay in seconds before change; defaults to 0.
            on_time: Duration in seconds to keep device ON; defaults to DEFAULT_ON_TIME.
            off_time: Duration in seconds to keep device OFF; defaults to DEFAULT_OFF_TIME.

        Note:
            Requires device discovery for the device protocol to be completed first.
        """
        for device_id in device_ids.split(","):
            self._do_switch_power_change(
                device_id=device_id,
                protocol=protocol,
                model=model,
                power_on=power_on,
                countdown=countdown,
                on_time=on_time,
                off_time=off_time,
            )

    def switch_power_change_helper(
        self,
        device_ids: str,
        power_on: bool,
        countdown: float = 0,
        on_time: float = DEFAULT_ON_TIME,
        off_time: float = DEFAULT_OFF_TIME,
    ) -> None:
        """Manage power state changes for switch devices by ID lookup.

        Retrieves devices from the device directory and calls switch_power_change with
        the device's protocol and model.

        Args:
            device_ids: Comma-separated device ID string.
            power_on: Desired power state (True for ON, False for OFF).
            countdown: Delay in seconds before change; defaults to 0.
            on_time: Duration in seconds to keep device ON; defaults to DEFAULT_ON_TIME.
            off_time: Duration in seconds to keep device OFF; defaults to DEFAULT_OFF_TIME.

        Note:
            Device discovery must be performed before calling this function.
        """
        for device_id in device_ids.split(","):
            # Retrieve the device from the device directory
            _device: Optional[dev.Device] = processor.DeviceDirectory.get_device(device_id)
            if _device is None:
                devices = processor.DeviceDirectory.get_device_ids()
                utils.i2m_log.warning("Device %s not found in %s", device_id, devices)
                return
            # Call the switch_power_change function with the retrieved device's protocol and model
            self._do_switch_power_change(
                device_id=device_id,
                protocol=_device.protocol,
                model=_device.model,
                power_on=power_on,
                countdown=countdown,
                on_time=on_time,
                off_time=off_time,
            )


def is_message_expected(
    message: messenger.Message,
    types_expected: Optional[List[messenger.MessageType]] = None,
    protocols_expected: Optional[List[dev.Protocol]] = None,
    models_expected: Optional[List[dev.Model]] = None,
    devices_expected: Optional[List[str]] = None,
) -> bool:
    """Validate if a message matches expected criteria.

    Checks if message matches type, protocol, model, and device filters. If any filter
    list is None, that criteria is not checked. Returns True if all specified criteria match.

    Args:
        message: Message to validate.
        types_expected: Allowed message types; None to skip check.
        protocols_expected: Allowed protocols; None to skip check.
        models_expected: Allowed device models; None to skip check.
        devices_expected: Allowed device IDs; None to skip check.

    Returns:
        True if message matches all specified criteria, False otherwise.
    """

    def _validate_list_membership(value: Any, expected_list) -> bool:
        if value is None:
            return False
        return value in expected_list

    if not any([types_expected, protocols_expected, models_expected, devices_expected]):
        return True

    if types_expected and not _validate_list_membership(
        message.message_type,
        types_expected,
    ):
        return False
    if protocols_expected and not _validate_list_membership(
        message.protocol,
        protocols_expected,
    ):
        return False
    if models_expected and not _validate_list_membership(
        message.model,
        models_expected,
    ):
        return False
    if devices_expected and not _validate_list_membership(
        message.device_id,
        devices_expected,
    ):
        return False
    return True


def get_refined_data_queue(
    mqtt_client: mqtthelper.ClientHelper,
    protocols_expected: Optional[List[dev.Protocol]] = None,
    models_expected: Optional[List[dev.Model]] = None,
    devices_expected: Optional[List[str]] = None,
    discovery_settle_seconds: float = 1.0,
) -> Queue:
    """Create a queue of refined messages from raw MQTT messages.

    Sets up a multi-stage message processing pipeline:
    1. Raw message capture via Scrutinizer
    2. Discovery message processing to identify devices
    3. Device model resolution for state/availability messages
    4. Message normalization to standardized formats

    Args:
        mqtt_client: MQTT client helper instance.
        protocols_expected: Protocols to filter; None to accept all.
        models_expected: Device models to filter; None to accept all.
        devices_expected: Device IDs to filter; None to accept all.
        discovery_settle_seconds: Delay after discovery to allow device registration.

    Returns:
        Queue containing refined messages matching all specified filters.
    """
    _raw_data_queue = Queue()
    _layer1_queue = Queue()
    _layer2_queue = Queue()
    _refined_queue = Queue()
    utils.check_parameter("protocols_expected", protocols_expected, List, optional=True)
    utils.check_parameter("models_expected", models_expected, List, optional=True)
    utils.check_parameter("devices_expected", devices_expected, List, optional=True)
    Scrutinizer(
        mqtt_client=mqtt_client,
        output_queue=_raw_data_queue,
        protocols_expected=protocols_expected,
    )
    _build_discovery_stage(
        input_queue=_raw_data_queue,
        output_queue=_layer1_queue,
        protocols_expected=protocols_expected,
    )
    time.sleep(discovery_settle_seconds)  # Listen to receive all discovery messages

    _build_resolution_stage(
        input_queue=_layer1_queue,
        output_queue=_layer2_queue,
        devices_expected=devices_expected,
        mqtt_client=mqtt_client,
    )

    _build_normalizer_stage(
        input_queue=_layer2_queue,
        output_queue=_refined_queue,
        models_expected=models_expected,
        devices_expected=devices_expected,
    )

    return _refined_queue


def _build_discovery_stage(
    input_queue: Queue,
    output_queue: Queue,
    protocols_expected: Optional[List[dev.Protocol]],
) -> messenger.Dispatcher:
    return messenger.Dispatcher(
        name="pipeline-discovery",
        input_queue=input_queue,
        output_queue=output_queue,
        conditional_handlers=[
            # 1) Protocol Filtering
            (
                lambda msg: is_message_expected(
                    msg,
                    types_expected=[messenger.MessageType.DISCO],
                    protocols_expected=protocols_expected,
                ),
                processor.Discoverer().process,
            ),
            (
                # copy NON Discovery messages to output queue
                lambda msg: is_message_expected(
                    msg,
                    types_expected=[
                        messenger.MessageType.AVAIL,
                        messenger.MessageType.STATE,
                    ],
                    protocols_expected=protocols_expected,
                ),
                processor.Processor.pass_through,
            ),
        ],
        default_handler=processor.Processor.no_op,
    )


def _build_resolution_stage(
    input_queue: Queue,
    output_queue: Queue,
    devices_expected: Optional[List[str]],
    mqtt_client: mqtthelper.ClientHelper,
) -> messenger.Dispatcher:
    _accessor = DeviceAccessor(mqtt_client=mqtt_client)

    return messenger.Dispatcher(
        name="pipeline-resolution",
        input_queue=input_queue,
        output_queue=output_queue,
        conditional_handlers=[
            # Device filtering
            (
                lambda msg: is_message_expected(
                    msg,
                    types_expected=[messenger.MessageType.DISCO],
                ),
                lambda msg: _get_device_state(msg, _accessor),
            ),
            (
                lambda msg: is_message_expected(
                    msg,
                    types_expected=[messenger.MessageType.STATE],
                    devices_expected=devices_expected,
                ),
                processor.ModelResolver().process,
            ),
            (
                lambda msg: is_message_expected(
                    msg,
                    types_expected=[messenger.MessageType.AVAIL],
                    devices_expected=devices_expected,
                ),
                processor.Processor.pass_through,
            ),
        ],
        # Remove non matching messages
        default_handler=processor.Processor.no_op,
    )


def _build_normalizer_stage(
    input_queue: Queue,
    output_queue: Queue,
    models_expected: Optional[List[dev.Model]],
    devices_expected: Optional[List[str]] = None,
) -> messenger.Dispatcher:
    return messenger.Dispatcher(
        name="normalizer",
        input_queue=input_queue,
        output_queue=output_queue,
        conditional_handlers=[
            (
                lambda msg: is_message_expected(
                    msg,
                    [messenger.MessageType.AVAIL],
                    models_expected=models_expected,  # Remove availability if model is expected
                ),
                processor.AvailabilityNormalizer().process,
            ),
            (
                lambda msg: is_message_expected(
                    msg,
                    [messenger.MessageType.STATE],
                    models_expected=models_expected,
                ),
                processor.StateNormalizer().process,
            ),
            (
                lambda msg: is_message_expected(
                    msg,
                    [messenger.MessageType.DISCO],
                    models_expected=models_expected,
                    devices_expected=devices_expected,
                ),
                processor.Processor.pass_through,
            ),
        ],
        default_handler=processor.Processor.no_op,
    )


def _get_device_state(
    message: messenger.Message, accessor: DeviceAccessor
) -> Optional[messenger.Message]:
    """Trigger state retrieval for devices from discovery message.

    For each device in the discovery message, publishes a state retrieval request.
    Returns the message unchanged.
    """
    _refined_data = message.refined
    if message.message_type != messenger.MessageType.DISCO:
        utils.i2m_log.error("Must be DISCOVERY message, not: %s", message)
        return message
    if _refined_data is None:
        utils.i2m_log.error("No refined message found for: %s", message)
        return message
    for _device_id in _refined_data.device_ids:
        _device: Optional[dev.Device] = processor.DeviceDirectory.get_device(_device_id)
        _model = _device.model
        _protocol = _device.protocol
        accessor.trigger_get_state(_device_id, protocol=_protocol, model=_model)
    return message


topics.InfoTopicManager().configure_topic_registry()
topics.CommandTopicManager().configure_topic_registry()
