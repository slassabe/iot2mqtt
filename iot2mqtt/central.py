#!/usr/local/bin/python3
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


class MessageParser(ABC):
    """
    Abstract base class for parsing incoming MQTT messages.
    """

    @staticmethod
    @abstractmethod
    def parse(
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        raw_payload: str,
    ) -> Optional[DataItem]:
        """
        Parse the incoming MQTT message according to the specified protocol and message type.
        """
        pass


class JsonMessageParser(MessageParser):
    """
    Parses incoming MQTT messages in JSON format.
    """

    @staticmethod
    def parse(
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


class RawMessageParser(MessageParser):
    """
    Parses incoming MQTT messages in raw format.
    """

    @staticmethod
    def parse(
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        raw_payload: str,
    ) -> Optional[DataItem]:
        # Called by :
        # - Tasmota availability messages: _on_tasmota_avail
        # - ESPSomfy availability messages: _on_espsomfy_avail
        return raw_payload


class ESPSomfyMessageParser(MessageParser):
    """
    Parses incoming ESPSomfy messages.
    """

    @staticmethod
    def parse(
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        raw_payload: str,
    ) -> Optional[DataItem]:
        # Called by :
        # - ESPSomfy state messages: _on_espsomfy_state
        # - ESPSomfy discovery messages : _on_espsomfy_disco
        key = topics.InfoTopicManager().resolve_wildcards(
            protocol=protocol, message_type=message_type, topic=topic, position=1
        )
        if message_type == messenger.MessageType.DISCO:
            value = json.loads(raw_payload)
        else:
            value = raw_payload
        return {key: value}


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
        _protocols = protocols_expected or [dev.Protocol.Z2M, dev.Protocol.TASMOTA, dev.Protocol.ESPSOMFY]
        self._subscribe_to_topics(_protocols)
        self._parsers = {
            MessageStructure.JSON: JsonMessageParser.parse,
            MessageStructure.RAW: RawMessageParser.parse,
            MessageStructure.ESPSOMFY: ESPSomfyMessageParser.parse,
        }

    def _subscribe_to_topics(self, protocols_expected) -> None:
        def _callback_add(
            protocol: dev.Protocol,
            message_type: messenger.MessageType,
            callback: Callable[[messenger.Message], None],
        ):
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
        # Set connection handler
        self._mqtt_client.connect_handler_add(self._on_connect)

    def _process_message(
        self,
        client: mqtt.Client,  # pylint: disable=unused-argument
        userdata: Any,  # pylint: disable=unused-argument
        mqtt_message: mqtt.MQTTMessage,
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        parser: Parser,
    ) -> None:
        """
        Process an incoming MQTT message and put the result in the output queue.
        """
        topic = mqtt_message.topic
        _raw_payload = str(mqtt_message.payload.decode("utf-8"))
        if _raw_payload is None:
            utils.i2m_log.info("Received empty message on topic %s", topic)
            return
        _device_id = self._get_device_id(
            protocol=protocol,
            message_type=message_type,
            topic=topic,
        )

        _data = parser(
            protocol=protocol,
            message_type=message_type,
            topic=topic,
            raw_payload=_raw_payload,
        )

        if _data is None:
            return
        _item = messenger.Item(data=_data)
        _incoming = messenger.Message(
            protocol=protocol,
            model=None,
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

    def _get_device_id(
        self,
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
    ) -> Optional[str]:
        """
        Get the device ID from the topic.
        """
        PREFIX = "shade"
        _index = topics.InfoTopicManager().resolve_wildcards(
            protocol=protocol,
            message_type=message_type,
            topic=topic,
            position=0,
        )
        if protocol == dev.Protocol.ESPSOMFY:
            if message_type == messenger.MessageType.AVAIL:
                return PREFIX
            if message_type in [
                messenger.MessageType.DISCO,
                messenger.MessageType.STATE,
            ]:
                return _index
        return _index

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
            parser=self._parsers[MessageStructure.JSON],
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
            parser=self._parsers[MessageStructure.RAW],
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
            parser=self._parsers[MessageStructure.RAW],
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
            parser=self._parsers[MessageStructure.JSON],
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
            parser=self._parsers[MessageStructure.JSON],
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
            parser=self._parsers[MessageStructure.ESPSOMFY],
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
            parser=self._parsers[MessageStructure.JSON],
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
            parser=self._parsers[MessageStructure.JSON],
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
            parser=self._parsers[MessageStructure.ESPSOMFY],
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
        if protocol in [dev.Protocol.TASMOTA, dev.Protocol.ESPSOMFY]:
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
    Scrutinizer(mqtt_client=mqtt_client, output_queue=_raw_data_queue, protocols_expected=protocols_expected)
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
    _registry = message.refined
    if message.message_type != messenger.MessageType.DISCO:
        utils.i2m_log.error("Must be DISCOVERY message, not: %s", message)
        return message
    if _registry is None:
        utils.i2m_log.error("No refined message found for: %s", message)
        return message
    for _device_id in _registry.device_ids:
        _device: Optional[dev.Device] = processor.DeviceDirectory.get_device(_device_id)
        _model = _device.model
        _protocol = _device.protocol
        accessor.trigger_get_state(_device_id, protocol=_protocol, model=_model)
    return message


topics.InfoTopicManager().configure_topic_registry()
topics.CommandTopicManager().configure_topic_registry()
