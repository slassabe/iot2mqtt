# coding=utf-8

"""
Module for managing MQTT topics and processing messages for IoT devices.

This module includes classes and functions to manage MQTT topic configurations,
subscribe to topics, process incoming messages, and trigger state changes on devices.
It supports multiple protocols such as Zigbee2MQTT and Tasmota.

Classes
-------

- Scrutinizer: Subscribes to MQTT topics and processes incoming messages.
- DeviceAccessor: Accesses device state via MQTT.

Functions
---------

- get_refined_data_queue: Returns a queue of refined messages by processing raw messages from MQTT.

"""
import json
import time
from abc import ABC, abstractmethod
from enum import Enum
from queue import Full, Queue
from typing import Any, Callable, Dict, List, Optional, TypeAlias, Union

import paho.mqtt.client as mqtt

from iot2mqtt import (abstract, dev, encoder, messenger, mqtthelper, processor,
                      topics, utils)

DEFAULT_ON_TIME = 0.0
DEFAULT_OFF_TIME = 0.0
QUEUE_TIMEOUT = 1  # write on queue timeout in seconds

Parser: TypeAlias = Callable[..., Optional[messenger.Item]]
DataItem: TypeAlias = Union[Dict, str, int, List[Dict]]


class MessageStructure(Enum):
    """
    Incoming MQTT message determining the parsing of the messages.
    """

    JSON = "json"
    RAW = "raw"
    ESPSOMFY = "espsomfy"
    RING = "ring"


class MessageFormater(ABC):
    """
    Abstract base class for parsing incoming MQTT messages.
    """

    @staticmethod
    @abstractmethod
    def modify_incoming_message(
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        raw_payload: str,
    ) -> Optional[DataItem]:
        """
        Parse the incoming MQTT message according to the specified protocol and message type.
        """
        pass


class JsonMessageFormater(MessageFormater):
    """
    Format incoming MQTT messages in JSON format.
    """

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
    """
    Format incoming MQTT messages in raw format.
    """

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
    """
    Format incoming STATE and DISCO ESPSomfy messages.
    """

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
            utils.i2m_log.warning(
                "Dismissing RING device message with topic tag: %s", topic_tag
            )
            return None
        return {_key: raw_payload}


class Scrutinizer:
    """
    A class responsible for subscribing to MQTT topics and processing incoming messages.

    The Scrutinizer class subscribes to various MQTT topics based on protocol and message type,
    processes incoming messages, and places the processed messages into an output queue of
    raw data.

    Args:
        mqtt_client (mqtthelper.ClientHelper): The MQTT client helper instance.
        output_queue (Queue): The queue where the raw data is placed.
        protocols_expected (List[dev.Protocol], optional): List of expected protocols. None for all.
        queue_timeout (int, optional): Timeout for queue operations in seconds. Defaults to 1.
    """

    # Reference to Frank Zappa - The Central Scrutinizer ❤

    def __init__(
        self,
        mqtt_client: mqtthelper.ClientHelper,
        output_queue: Queue,
        protocols_expected: List[dev.Protocol] = None,
        queue_timeout: int = QUEUE_TIMEOUT,  # timeout in sec.
    ) -> None:
        self._mqtt_client = mqtt_client
        self._output_queue = output_queue
        self._queue_timeout = queue_timeout
        self._metrics_collector = utils.MetricsCollector()
        # Listen all supported protocols by default
        _protocols = protocols_expected or [
            dev.Protocol.Z2M,
            dev.Protocol.TASMOTA,
            dev.Protocol.RING,
            dev.Protocol.ESPSOMFY,
        ]
        self._subscribe_to_topics(_protocols)
        self._formaters: dict[MessageStructure, MessageFormater] = {
            MessageStructure.JSON: JsonMessageFormater,
            MessageStructure.RAW: RawMessageFormater,
            MessageStructure.ESPSOMFY: ESPSomfyMessageFormater,
            MessageStructure.RING: RingMessageFormater,
        }

    def _get_formater(self, message_structure: MessageStructure) -> Callable:
        return self._formaters[message_structure].modify_incoming_message

    def _subscribe_to_topics(self, protocols_expected) -> None:
        def _callback_add(
            protocol: dev.Protocol,
            message_type: messenger.MessageType,
            callback: Callable[[messenger.Message], None],
        ) -> None:
            _topic = topics.InfoTopicManager().get_topic_to_subscribe(
                protocol, message_type
            )
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

    def _process_message(
        self,
        client: mqtt.Client,  # pylint: disable=unused-argument
        userdata: Any,  # pylint: disable=unused-argument
        mqtt_message: mqtt.MQTTMessage,
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        target_message_structure: MessageStructure,
    ) -> None:
        """
        Process an incoming MQTT message and put the result in the output queue.
        Args:
            client (mqtt.Client): The MQTT client instance.
            userdata (Any): User data associated with the client.
            mqtt_message (mqtt.MQTTMessage): The incoming MQTT message.
            protocol (dev.Protocol): The protocol associated with the message.
            message_type (messenger.MessageType): The type of the message.
            target_message_structure (MessageStructure): The target structure of the message.
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
            utils.i2m_log.error(
                "Output queue is full. Dropping message for topic %s", topic
            )

    def _on_z2m_avail(self, *argc, **kwargs) -> None:
        """
        Process zigbee2mqtt availability messages:
        zigbee2mqtt/<device_id>/availability: <value>
        """
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.AVAIL,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_tasmota_avail(self, *argc, **kwargs) -> None:
        """
        Process Tasmota availability messages:
        tele/<device_id>/LWT: <value>
        """
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.AVAIL,
            target_message_structure=MessageStructure.RAW,
        )

    def _on_espsomfy_avail(self, *argc, **kwargs) -> None:
        """
        Process ESPSomfy availability messages:
        ESPSomfy/status: <value>
        """
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.ESPSOMFY,
            message_type=messenger.MessageType.AVAIL,
            target_message_structure=MessageStructure.RAW,
        )

    def _on_ring_avail(self, *argc, **kwargs) -> None:
        """
        Process RING availability messages:
        ring/<location_id>/<product_category>/<device_id>/status: <value>
        """
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
        """
        Process zigbee2mqtt state messages:
        zigbee2mqtt/<device_id>: {<property>: <value>}
        """
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.STATE,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_tasmota_state(self, *argc, **kwargs) -> None:
        """
        Process Tasmota state messages:
        stat/<device_id>/RESULT: {<property>: <value>}
        """
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.STATE,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_espsomfy_state(self, *argc, **kwargs) -> None:
        """
        Process ESPSomfy state messages:
        ESPSomfy/shades/<device_id>/<property>: <value>
        """
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.ESPSOMFY,
            message_type=messenger.MessageType.STATE,
            target_message_structure=MessageStructure.ESPSOMFY,
        )

    def _on_ring_state(self, *argc, **kwargs) -> None:
        """
        Process RING state messages:
        ESPSomfy/shades/<device_id>/<property>: <value>
        """
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.RING,
            message_type=messenger.MessageType.STATE,
            target_message_structure=MessageStructure.RING,
        )

    def _on_z2m_disco(self, *argc, **kwargs) -> None:
        """
        Process zigbee2mqtt discovery messages:
        zigbee2mqtt/bridge/devices: [{<property>: <value>}]
        """
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.DISCO,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_tasmota_disco(self, *argc, **kwargs) -> None:
        """
        Process Tasmota discovery messages:
        tasmota/discovery/<device_id>/config: {<property>: <value>}
        """
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.DISCO,
            target_message_structure=MessageStructure.JSON,
        )

    def _on_espsomfy_disco(self, *argc, **kwargs) -> None:
        """
        Process ESPSomfy discovery messages:
        homeassistant/cover/<device_id>/config: {<property>: <value>}
        """
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
        flags: mqtt.ConnectFlags,  # pylint: disable=unused-argument
        reason_code: mqtt.ReasonCode,  # pylint: disable=unused-argument
        properties: mqtt.Properties,  # pylint: disable=unused-argument
    ) -> None:
        """Subscribes to MQTT topics on connection."""
        for _topic in topics.InfoTopicManager().get_all_topics_to_subscribe():
            utils.i2m_log.debug("Subscribing to %s", _topic)
            client.subscribe(_topic)


class DeviceAccessor:
    RETRY_COUNT_MAX = 3
    RETRY_ELAPSE = 60  # seconds

    _timer_mgr = utils.TimerManager()
    """
    A class responsible for accessing device state via MQTT.

    This class provides methods to trigger the retrieval of the current state of a device
    using the MQTT protocol. It interacts with the MQTT client to publish state retrieval
    or state change commands to the appropriate MQTT topics based on the device model and
    protocol.

    Args:
        mqtt_client (mqtthelper.ClientHelper): An instance of the MQTT client helper used
            to publish messages to MQTT topics.
    """

    def __init__(self, mqtt_client: mqtthelper.ClientHelper) -> None:
        self._mqtt_client = mqtt_client

    def trigger_get_state(
        self, device_id: str, protocol: dev.Protocol, model: dev.Model
    ) -> None:
        """
        Triggers the retrieval of the current state of a device via MQTT.

        This method publishes state retrieval commands to the appropriate MQTT topics based
        on the device model and protocol. It uses the encoder registry to get the fields
        that can be retrieved for the given device model and constructs the MQTT topics
        accordingly.

        Args:
            device_id (str): The id of the device for which the state is being retrieved.
            protocol (dev.Protocol): The communication protocol used by the device (e.g., Z2M,
                TASMOTA).
            model (dev.Model): The model of the device.

        Raises:
            NotImplementedError: If the protocol is unknown or not supported.

        Note:
            If the encoder for the given device model is not found, a debug message is logged
            and the method returns without publishing any messages.
        """

        def _publish_it(topic: str, payload: str) -> None:
            utils.i2m_log.debug(
                "Publishing state retrieval to %s - state : %s", topic, payload
            )
            self._mqtt_client.publish(topic, payload=payload, qos=1, retain=False)
            return

        _command_base_topic = topics.CommandTopicManager().get_command_base_topic(
            protocol
        )
        _encoder = encoder.EncoderRegistry.get_encoder(model=model)
        if _encoder is None:
            utils.i2m_log.debug("Cannot get state for model: %s", model)
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

    def trigger_change_state(
        self, device_id: str, protocol: dev.Protocol, state: Dict
    ) -> None:
        """
        Publish a state change message to the MQTT topic for the given device.

        Args:
            device_id (str): The id of the device.
            protocol (dev.Protocol): The communication protocol.
            state (Dict): The new state to be published.

        Note:
            Refer to the documentation of the :mod:`iot2mqtt.abstract` module to generate the state,
            by the use of the `model_dump` method.

        """

        def _publish_it(topic: str, payload: str) -> None:
            utils.i2m_log.debug(
                "Publishing state change to %s - state : %s", topic, payload
            )
            self._mqtt_client.publish(topic, payload=payload, qos=1, retain=False)
            return

        _command_base_topic = topics.CommandTopicManager().get_command_base_topic(
            protocol
        )
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
        """
        Publishes state changes for Ring devices to MQTT topics.

        Args:
            device_id (str): The Ring device identifier
            protocol (dev.Protocol): Must be Protocol.RING
            state (Dict): State changes to apply to the device
            location_id (str): The Ring location identifier
            model (str): The Ring device model/category

        Raises:
            ValueError: If device_id, location_id or model are empty
            NotImplementedError: If protocol is not Protocol.RING

        The method constructs Ring-specific MQTT command topics in the format:
        <base_topic>/<location_id>/<model>/<device_id>/<state_key>/command
        """

        def _publish_it(topic: str, payload: str) -> None:
            utils.i2m_log.debug(
                "Publishing state change to %s - state : %s", topic, payload
            )
            self._mqtt_client.publish(topic, payload=payload, qos=1, retain=False)
            return

        if not device_id or not location_id or not model:
            _msg = (
                f"device_id: {device_id}, location_id: {location_id} /"
                f"and model: {location_id} must not be empty"
            )
            raise ValueError(_msg)

        _command_base_topic = topics.CommandTopicManager().get_command_base_topic(
            protocol
        )
        if protocol == dev.Protocol.RING:
            for _key, _value in state.items():
                _command_topic = (
                    f"{_command_base_topic}/{location_id}/"
                    f"{model}/{device_id}/{_key}/command"
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
        _device: Optional[dev.RingDevice] = processor.DeviceDirectory.get_device(
            device_id
        )
        if _device is None:
            if retry_count > self.RETRY_COUNT_MAX:
                utils.i2m_log.error("[%s] device not found: abort", device_id)
                return
            utils.i2m_log.warning(
                "[%s] device not found: retry (%s)", device_id, retry_count
            )
            _params = {
                "device_id": device_id,
                "state": state,
                "retry_count": retry_count + 1,
            }
            self._timer_mgr.create_timer(
                device_id=device_id,
                countdown=self.RETRY_ELAPSE * (retry_count + 1),
                task=self._do_trigger_change_state_helper,
                kwargs=_params,
            )
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
        """
        Triggers state changes for multiple devices.

        Args:
            device_ids (str): A comma-separated string of device IDs to update
            state (Dict): The state changes to apply to each device

        The method splits the device_ids string and triggers state changes for each device
        individually, with retry handling in case devices are not immediately available.
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
            state=encoder.encode(
                model, abstract.SWITCH_ON if power_on else abstract.SWITCH_OFF
            ),
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
        """
        Manage the power state change of switch devices.

        This function handles the power state change of switchs, optionally scheduling
        the change to occur after a countdown. It also manages the timing for turning
        the devices on and off based on the provided on_time and off_time parameters.

        Args:
            device_ids (str): A comma-separated string of switch ids.
            protocol (dev.Protocol): The protocol used by the device.
            model (dev.Model): The model of the device.
            power_on (bool): The desired power state (True for ON, False for OFF).
            countdown (float, optional): The countdown time in seconds before the power state
                change occurs. Defaults to 0.
            on_time (float, optional): The duration in seconds to keep the device ON.
                Defaults to DEFAULT_ON_TIME.
            off_time (float, optional): The duration in seconds to keep the device OFF.
                Defaults to DEFAULT_OFF_TIME.

        Returns:
            None

        Note:
            The discovery step is not required for this function to work, but the protocol and
            model must be provided compared to :func:`switch_power_change_helper` function.

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
        """
        Helper function to change the power state of switch devices.

        This function retrieves devices from the device directory based on the provided
        device names, and then calls the `switch_power_change` function to change their
        power state.

        Args:
            device_ids (str): A comma-separated string of switch ids.
            power_on (bool): The desired power state. True to power on, False to power off.
            countdown (float, optional): The countdown period in seconds before changing
                the power state. Defaults to 0.
            on_time (float, optional): The duration in seconds for which the device should
                remain powered on. Defaults to DEFAULT_ON_TIME.
            off_time (float, optional): The duration in seconds for which the device should
                remain powered off. Defaults to DEFAULT_OFF_TIME.

        Returns:
            None

        Note:
            The discovery step must be performed before calling this function.

        """
        for device_id in device_ids.split(","):
            # Retrieve the device from the device directory
            _device: Optional[dev.Device] = processor.DeviceDirectory.get_device(
                device_id
            )
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
    types_expected: List[messenger.MessageType] = None,
    protocols_expected: List[dev.Protocol] = None,
    models_expected: List[dev.Model] = None,
    devices_expected: List[str] = None,
) -> bool:
    """
    Validates if a message matches the expected criteria for message type,
    protocol, model and device.

    Args:
        message: The messenger.Message object to validate
        types_expected: List of allowed message types
        protocols_expected: List of allowed protocols
        models_expected: List of allowed device models
        devices_expected: List of allowed device IDs

    Returns:
        bool: True if message matches all specified criteria, False otherwise

    Note:
        If any of the expected lists are None, that criteria is not checked.
        The message must have non-None values for message_type, protocol and model.
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
    protocols_expected: List[dev.Protocol] = None,
    models_expected: List[dev.Model] = None,
    devices_expected: List[str] = None,
) -> Queue:
    """
    Creates and returns a queue of refined messages by processing raw messages from MQTT.

    This function sets up a message processing pipeline that:
    1. Captures raw MQTT messages via a Scrutinizer
    2. Processes discovery messages to identify devices
    3. Resolves device models and processes availability/state messages
    4. Normalizes messages into standardized formats

    Args:
        mqtt_client (mqtthelper.ClientHelper): The MQTT client helper instance
        protocols_expected (List[dev.Protocol], optional): List of protocols to filter messages by
        models_expected (List[dev.Model], optional): List of device models to filter messages by
        devices_expected (List[str], optional): List of device IDs to filter messages by

    Returns:
        Queue: A queue containing the refined (processed) messages that match the specified filters

    Note:
        The pipeline includes a 1-second delay after discovery messages to ensure all devices
        are properly identified before processing state messages.
    """
    _raw_data_queue = Queue()
    _layer1_queue = Queue()
    _layer2_queue = Queue()
    _refined_queue = Queue()
    Scrutinizer(
        mqtt_client=mqtt_client,
        output_queue=_raw_data_queue,
        protocols_expected=protocols_expected,
    )
    _accessor = DeviceAccessor(mqtt_client=mqtt_client)

    messenger.Dispatcher(
        name="pipeline-discovery",
        input_queue=_raw_data_queue,
        output_queue=_layer1_queue,
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
        # Remove non matching protocol messages
        default_handler=processor.Processor.no_op,
    )
    time.sleep(1)  # Listen to receive all discovery messages

    messenger.Dispatcher(
        name="pipeline-layer1",
        input_queue=_layer1_queue,
        output_queue=_layer2_queue,
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
    messenger.Dispatcher(
        name="normalizer",
        input_queue=_layer2_queue,
        output_queue=_refined_queue,
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
        # Remove non matching messages
        default_handler=processor.Processor.no_op,
    )
    return _refined_queue


def _get_device_state(
    message: messenger.Message, accessor: DeviceAccessor
) -> Optional[messenger.Message]:
    """
    Ask for state device
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
