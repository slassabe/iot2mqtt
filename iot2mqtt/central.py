#!/usr/local/bin/python3
# coding=utf-8

"""
Module for managing MQTT topics and processing messages for IoT devices.

This module includes classes and functions to manage MQTT topic configurations,
subscribe to topics, process incoming messages, and trigger state changes on devices.
It supports multiple protocols such as Zigbee2MQTT and Tasmota.

"""
import json
import threading
import time
from queue import Queue
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt
from pydantic import BaseModel, ValidationError

from iot2mqtt import (abstract, dev, encoder, messenger, mqtthelper, processor,
                      utils)

Z2M_INFO_BASE_TOPIC = "zigbee2mqtt"
Z2M_CMND_BASE_TOPIC = "zigbee2mqtt"
TASMOTA_INFO_BASE_TOPIC = "tele"
TASMOTA_CMND_BASE_TOPIC = "cmnd"
TASMOTA_DISCOVERY_TOPIC = "tasmota/discovery"

DEFAULT_ON_TIME = 5.0
DEFAULT_OFF_TIME = 0.0


class _TopicManager(metaclass=utils.Singleton):
    """
    A registry for managing topic configurations based on protocol and message type.

    This class provides a centralized way to store and retrieve topic configurations
    for different combinations of protocol and message type. It acts as a registry
    for topic configurations, allowing easy access to the topic base, topic extension,
    and device name offset for a given protocol and message type.
    """

    def __init__(self) -> None:
        # self._topic_registry: Dict[TopicRegistryKey, "TopicManager"] = {}
        self._topic_registry = {}


class _CommandTopicManager(_TopicManager):
    """
    Manages command topics for different protocols.

    This class provides methods to register and retrieve command base topics
    for various protocols. It acts as a registry for command topic configurations,
    allowing easy access to the command base topic for a given protocol.
    """

    def register(
        self,
        protocol: dev.Protocol,
        command_topic_base: str,
    ) -> None:
        """
        Register a command topic base for a given protocol.

        Args:
            protocol (dev.Protocol): The protocol for which the command topic base is
                being registered.
            command_topic_base (str): The base topic for commands of the given protocol.

        Raises:
            ValueError: If the protocol is already registered.
        """
        if protocol in self._topic_registry:
            raise ValueError("Protocol is already registered")
        self._topic_registry[protocol] = command_topic_base

    def get_command_base_topic(self, protocol: dev.Protocol) -> str:
        """
        Get the command base topic for a given protocol.
        """
        return self._topic_registry[protocol]

    def configure_topic_registry(self) -> None:
        """
        Configure the topic registry.
        """
        _prefix = "TEST/"
        _prefix = ""
        self.register(
            protocol=dev.Protocol.Z2M, command_topic_base=_prefix + Z2M_INFO_BASE_TOPIC
        )
        self.register(
            protocol=dev.Protocol.TASMOTA,
            command_topic_base=_prefix + TASMOTA_CMND_BASE_TOPIC,
        )


class _InfoTopicRegistryKey(BaseModel):
    """
    A key used to uniquely identify a topic configuration based on the
    protocol and message type.
    """

    protocol: dev.Protocol
    message_type: messenger.MessageType

    class Config:
        "Pydantic configuration for the InfoTopicRegistryKey class."
        frozen = True


class _InfoTopicRegistry(BaseModel):
    """
    Registered values for a given protocol and message type.
    """

    info_topic_base: str
    topic_to_subscribe: str
    device_name_offset: int


class _InfoTopicManager(_TopicManager):
    """
    Manages topic configurations for different protocols and message types.

    This class provides methods to register, retrieve, and resolve MQTT topics
    based on protocol and message type. It acts as a registry for topic configurations,
    allowing easy access to the topic base, topic extension, and device name offset.
    """

    def resolve_wildcards(
        self,
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        position: int = 0,
    ) -> str:
        """
        Resolve wildcards in the topic based on the protocol and message type.
        """
        _registry_key = _InfoTopicRegistryKey(
            protocol=protocol, message_type=message_type
        )
        _registry_value = self._topic_registry.get(_registry_key)
        _offset = _registry_value.device_name_offset
        _result = topic[_offset:].split("/")[position]
        return _result

    def get_sub_topic(
        self, protocol: dev.Protocol, message_type: messenger.MessageType, topic: str
    ) -> str:
        """
        Get the sub-topic from the given topic based on the protocol and message type.
        """
        _registry_key = _InfoTopicRegistryKey(
            protocol=protocol, message_type=message_type
        )
        _registry_value = self._topic_registry.get(_registry_key)
        _offset = _registry_value.device_name_offset
        _sub_topic = topic[_offset:].split("/")[1]
        return _sub_topic

    def get_topic_to_subscribe(
        self, protocol: dev.Protocol, message_type: messenger.MessageType
    ) -> str:
        """
        Get the topic to subscribe to based on the protocol and message type.
        """
        _registry_key = _InfoTopicRegistryKey(
            protocol=protocol, message_type=message_type
        )
        _registry_value = self._topic_registry.get(_registry_key)
        return _registry_value.topic_to_subscribe

    def get_all_topics_to_subscribe(self) -> List[str]:
        """
        Get a list of all topics to subscribe to.
        """
        return [x.topic_to_subscribe for x in self._topic_registry.values()]

    def register(
        self,
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        info_topic_base: str,
        info_topic_extension: str,
    ) -> None:
        """
        Register a topic configuration.
        """
        _registry_key = _InfoTopicRegistryKey(
            protocol=protocol, message_type=message_type
        )
        if _registry_key in self._topic_registry:
            raise ValueError("Key is already registered")
        _registry_value = _InfoTopicRegistry(
            info_topic_base=info_topic_base,
            topic_to_subscribe=info_topic_base + info_topic_extension,
            device_name_offset=len(info_topic_base) + 1,
        )
        self._topic_registry[_registry_key] = _registry_value

    def configure_topic_registry(self) -> None:
        """
        Configure the topic registry.
        """
        self.register(
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.AVAIL,
            info_topic_base=Z2M_INFO_BASE_TOPIC,
            info_topic_extension="/+/availability",
        )
        self.register(
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.AVAIL,
            info_topic_base=TASMOTA_INFO_BASE_TOPIC,
            info_topic_extension="/+/LWT",
        )
        self.register(
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.STATE,
            info_topic_base=Z2M_INFO_BASE_TOPIC,
            info_topic_extension="/+",
        )
        self.register(
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.STATE,
            info_topic_base=TASMOTA_INFO_BASE_TOPIC,
            info_topic_extension="/+/+",
        )
        self.register(
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.DISCO,
            info_topic_base=Z2M_INFO_BASE_TOPIC,
            info_topic_extension="/bridge/devices",
        )
        self.register(
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.DISCO,
            info_topic_base=TASMOTA_DISCOVERY_TOPIC,
            info_topic_extension="/+/config",
        )


class Scrutinizer:
    """
    A class responsible for subscribing to MQTT topics and processing incoming messages.

    The Scrutinizer class subscribes to various MQTT topics based on protocol and message type,
    processes incoming messages, and places the processed messages into an output queue of
    raw data.

    Args:
        mqtt_client (mqtthelper.ClientHelper): The MQTT client helper instance.
        output_queue (Queue): The queue where the raw data is placed.
        queue_timeout (int, optional): Timeout for queue operations in seconds. Defaults to 1.
    """

    # Reference to Frank Zappa - The Central Scrutinizer ❤

    def __init__(
        self,
        mqtt_client: mqtthelper.ClientHelper,
        output_queue: Queue,
        queue_timeout: int = 1,  # timeout in sec.
    ) -> None:
        self._mqtt_client = mqtt_client
        self._output_queue = output_queue
        self._queue_timeout = queue_timeout
        self._subscribe_to_topics()

    def _subscribe_to_topics(self) -> None:
        def _callback_add(
            protocol: dev.Protocol,
            message_type: messenger.MessageType,
            callback: Callable[[messenger.Message], None],
        ):
            _topic = _InfoTopicManager().get_topic_to_subscribe(protocol, message_type)
            self._mqtt_client.message_callback_add(_topic, callback)

        _z2m = dev.Protocol.Z2M
        _tasmota = dev.Protocol.TASMOTA
        _avail = messenger.MessageType.AVAIL
        _state = messenger.MessageType.STATE
        _disco = messenger.MessageType.DISCO
        # Set availability handlers
        _callback_add(_z2m, _avail, self._on_z2m_avail)
        _callback_add(_tasmota, _avail, self._on_tasmota_avail)
        # Set state handlers
        _callback_add(_z2m, _state, self._on_z2m_state)
        _callback_add(_tasmota, _state, self._on_tasmota_state)
        # Set discovery handlers
        _callback_add(_z2m, _disco, self._on_z2m_disco)
        _callback_add(_tasmota, _disco, self._on_tasmota_disco)
        # Set connection handler
        self._mqtt_client.connect_handler_add(self._on_connect)

    def _json_to_item(
        self,
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
        topic: str,
        payload: str,
    ) -> messenger.Item:
        """
        Convert a JSON payload to a messenger.Item object.
        """
        try:
            _payload = json.loads(payload)
            _tag = None
            if protocol == dev.Protocol.TASMOTA:
                _tag = _InfoTopicManager().resolve_wildcards(
                    protocol=protocol,
                    message_type=message_type,
                    topic=topic,
                    position=1,
                )
            return messenger.Item(data=_payload, tag=_tag)
        except ValidationError as exc:
            utils.i2m_log.error(
                "Failed to parse message: %s - data: %s - tag: %s",
                repr(exc.errors()[0]["type"]),
                _payload,
                _tag,
            )
            return None

    def _process_message(
        self,
        client: mqtt.Client,  # pylint: disable=unused-argument
        userdata: Any,  # pylint: disable=unused-argument
        mqtt_message: mqtt.MQTTMessage,
        protocol: dev.Protocol,
        message_type: messenger.MessageType,
    ) -> None:
        """
        Process an incoming MQTT message and put the result in the output queue.
        """
        topic = mqtt_message.topic
        _raw_payload = str(mqtt_message.payload.decode("utf-8"))
        if _raw_payload is None:
            utils.i2m_log.info("Received empty message on topic %s", topic)
            return
        _device_name = _InfoTopicManager().resolve_wildcards(
            protocol=protocol, message_type=message_type, topic=topic
        )
        try:
            _item = self._json_to_item(
                protocol=protocol,
                message_type=message_type,
                topic=topic,
                payload=_raw_payload,
            )
        except json.JSONDecodeError:
            _is_tasmota = protocol == dev.Protocol.TASMOTA
            _is_state = message_type == messenger.MessageType.STATE
            if _is_tasmota and _is_state:
                utils.i2m_log.debug("[%s] dismissed topic", topic)
                return
            _item = messenger.Item(data=_raw_payload)
        _incoming = messenger.Message(
            protocol=protocol,
            model=None,
            device_name=_device_name,
            message_type=message_type,
            raw_item=_item,
        )
        self._output_queue.put(_incoming, block=True, timeout=self._queue_timeout)

    def _on_z2m_avail(self, *argc, **kwargs) -> None:
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.AVAIL,
        )

    def _on_tasmota_avail(self, *argc, **kwargs) -> None:
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.AVAIL,
        )

    def _on_z2m_state(self, *argc, **kwargs) -> None:
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.STATE,
        )

    def _on_tasmota_state(self, *argc, **kwargs) -> None:
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.STATE,
        )

    def _on_z2m_disco(self, *argc, **kwargs) -> None:
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.Z2M,
            message_type=messenger.MessageType.DISCO,
        )

    def _on_tasmota_disco(self, *argc, **kwargs) -> None:
        self._process_message(
            *argc,
            **kwargs,
            protocol=dev.Protocol.TASMOTA,
            message_type=messenger.MessageType.DISCO,
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
        for _topic in _InfoTopicManager().get_all_topics_to_subscribe():
            utils.i2m_log.debug("Subscribing to %s", _topic)
            client.subscribe(_topic)


class _TimerManager:
    """
    A class to manage timers for devices, ensuring thread safety and preventing multiple timers
    from being active for the same device in case of bouncing messages
    """

    def __init__(self):
        self._timer_registry: Dict[str, threading.Thread] = {}
        self._timer_registry_lock = threading.Lock()

    def create_timer(
        self,
        device_name: str,
        countdown: float,
        task: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> threading.Thread:
        """
        Manages a timer for a specific device, ensuring that only one timer is active per device.

        This method creates and starts a new timer for the given device. If a timer for the device
        already exists, it cancels the existing timer before starting a new one. The timer will call
        the specified function (`task`) with the provided arguments (`args` and `kwargs`) after
        the countdown period.

        Args:
            device_name (str): The name of the device for which the timer is being managed.
            countdown (float): The countdown period in seconds after which the `task` function
                will be executed.
            task (Callable[..., Any]): The function to be called when the timer expires.
            args (tuple, optional): Positional arguments to be passed to the `task` function.
                Defaults to ().
            kwargs (Optional[Dict[str, Any]], optional): Keyword arguments to be passed to the
                `task` function. Defaults to None.

        Returns:
            threading.Thread: The newly created and started timer thread.
        """
        if kwargs is None:
            kwargs = {}
        try:
            with self._timer_registry_lock:
                _previous_timer = self._timer_registry.get(device_name)
                if _previous_timer is not None:
                    utils.i2m_log.debug("Replace previous timer for %s", device_name)
                    _previous_timer.cancel()
                _timer = threading.Timer(countdown, task, args=args, kwargs=kwargs)
                _timer.start()
                self._timer_registry[device_name] = _timer
        except Exception as e:
            utils.i2m_log.error(
                "Failed to manage timer for %s: %s", device_name, str(e)
            )
            raise


timer_manager = _TimerManager()


def is_timer_active(device_name: str) -> bool:
    """
    Checks if a timer is active for a specific device.

    Args:
        device_name (str): The name of the device to check for an active timer.

    Returns:
        bool: True if a timer is active for the specified device, False otherwise.
    """
    return device_name in timer_manager._timer_registry


class DeviceAccessor:
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
        self, device_name: str, protocol: dev.Protocol, model: dev.Model
    ) -> None:
        """
        Triggers the retrieval of the current state of a device via MQTT.

        This method publishes state retrieval commands to the appropriate MQTT topics based
        on the device model and protocol. It uses the encoder registry to get the fields
        that can be retrieved for the given device model and constructs the MQTT topics
        accordingly.

        Args:
            device_name (str): The name of the device for which the state is being retrieved.
            protocol (dev.Protocol): The communication protocol used by the device (e.g., Z2M, TASMOTA).
            model (dev.Model): The model of the device.

        Raises:
            NotImplementedError: If the protocol is unknown or not supported.

        Note:
            If the encoder for the given device model is not found, a debug message is logged
            and the method returns without publishing any messages.
        """
        _command_base_topic = _CommandTopicManager().get_command_base_topic(protocol)
        _encoder = encoder.EncoderRegistry.get_encoder(model=model)
        if _encoder is None:
            utils.i2m_log.debug("Cannot get state for model: %s", model)
            return
        _fields = _encoder.gettable_fields
        if protocol == dev.Protocol.Z2M:
            _command_topic = f"{_command_base_topic}/{device_name}/get"
            _pl = {_field: "" for _field in _fields}
            _command_payload = json.dumps(_pl)
            utils.i2m_log.debug(
                "Publishing state retrieval to %s - state : %s",
                _command_topic,
                _command_payload,
            )
            self._mqtt_client.publish(
                _command_topic, payload=_command_payload, qos=1, retain=False
            )
            return
        if protocol == dev.Protocol.TASMOTA:
            for _field in _fields:
                _command_topic = f"{_command_base_topic}/{device_name}/{_field}"
                utils.i2m_log.debug(
                    "Publishing state retrieval to %s - state : %s",
                    _command_topic,
                    '""',
                )
                self._mqtt_client.publish(
                    _command_topic, payload="", qos=1, retain=False
                )
            return
        _error_msg = f"Unknown protocol {protocol}"
        raise NotImplementedError(_error_msg)

    def trigger_change_state(
        self, device_name: str, protocol: dev.Protocol, state: Dict
    ) -> None:
        """
        Publish a state change message to the MQTT topic for the given device.

        Args:
            device_name (str): The name of the device.
            protocol (dev.Protocol): The communication protocol.
            state (Dict): The new state to be published.

        Note:
            Refer to the documentation of the :mod:`iot2mqtt.abstract` module to generate the state,
            by the use of the `model_dump` method.

        """
        _command_base_topic = _CommandTopicManager().get_command_base_topic(protocol)
        _json_state = json.dumps(state)
        if protocol == dev.Protocol.Z2M:
            _command_topic = f"{_command_base_topic}/{device_name}/set"
            utils.i2m_log.debug(
                "Publishing state change to %s - state : %s",
                _command_topic,
                _json_state,
            )
            self._mqtt_client.publish(
                _command_topic, payload=_json_state, qos=1, retain=False
            )
            return
        if protocol == dev.Protocol.TASMOTA:
            for _key, _value in state.items():
                _command_topic = f"{_command_base_topic}/{device_name}/{_key}"
                utils.i2m_log.debug(
                    "Publishing state change to %s - state : %s", _command_topic, _value
                )
                self._mqtt_client.publish(
                    _command_topic, payload=str(_value), qos=1, retain=False
                )
            return
        _error_msg = f"Unknown protocol {protocol}"
        raise NotImplementedError(_error_msg)

    def _do_switch_power(
        self,
        device_name: str,
        protocol: dev.Protocol,
        model: dev.Model,
        power_on: bool,
    ) -> None:
        utils.i2m_log.debug("Switching power of %s to %s", device_name, power_on)
        self.trigger_change_state(
            device_name=device_name,
            protocol=protocol,
            state=encoder.encode(
                model, abstract.SWITCH_ON if power_on else abstract.SWITCH_OFF
            ),
        )

    def _do_switch_power_change(
        self,
        device_name: str,
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
                "device_name": device_name,
                "protocol": protocol,
                "model": model,
                "power_on": _power_on,
            }
            timer_manager.create_timer(
                device_name=device_name,
                countdown=_countdown,
                task=self._do_switch_power,
                kwargs=_params,
            )

        if countdown != 0:
            _params = {
                "device_names": device_name,
                "protocol": protocol,
                "model": model,
                "power_on": power_on,
                "countdown": 0,
                "on_time": on_time,
                "off_time": off_time,
            }
            timer_manager.create_timer(
                device_name=device_name,
                countdown=countdown,
                task=self.switch_power_change,
                kwargs=_params,
            )
        else:
            self._do_switch_power(
                device_name=device_name,
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
        device_names: str,
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
            device_names (str): A comma-separated string of switch names.
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
        for device_name in device_names.split(","):
            self._do_switch_power_change(
                device_name=device_name,
                protocol=protocol,
                model=model,
                power_on=power_on,
                countdown=countdown,
                on_time=on_time,
                off_time=off_time,
            )

    def switch_power_change_helper(
        self,
        device_names: str,
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
            device_names (str): A comma-separated string of switch names.
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
        for device_name in device_names.split(","):
            # Retrieve the device from the device directory
            _device: Optional[dev.Device] = processor.DeviceDirectory.get_device(
                device_name
            )
            if _device is None:
                devices = processor.DeviceDirectory.get_device_names()
                utils.i2m_log.warning("Device %s not found in %s", device_name, devices)
                return
            # Call the switch_power_change function with the retrieved device's protocol and model
            self._do_switch_power_change(
                device_name=device_name,
                protocol=_device.protocol,
                model=_device.model,
                power_on=power_on,
                countdown=countdown,
                on_time=on_time,
                off_time=off_time,
            )


def get_refined_data_queue(mqtt_client: mqtthelper.ClientHelper) -> Queue:
    """
    Creates and returns a queue of refined messages by processing raw messages from MQTT.

    Args:
        mqtt_client (mqtthelper.ClientHelper): The MQTT client helper instance.

    Returns:
        Queue: The queue containing the refined (processed) messages.

    """
    _raw_data_queue = Queue()
    _layer1_queue = Queue()
    _layer2_queue = Queue()
    _refined_queue = Queue()
    Scrutinizer(mqtt_client=mqtt_client, output_queue=_raw_data_queue)

    messenger.Dispatcher(
        name="pipeline-discovery",
        input_queue=_raw_data_queue,
        output_queue=_layer1_queue,
        conditional_handlers=[
            (messenger.is_type_discovery, processor.Discoverer().process),
        ],
        # copy Discovery message to output queue
        default_handler=processor.Processor.pass_through,
    )
    time.sleep(2)  # Listen to receive all discovery messages
    _accessor = DeviceAccessor(mqtt_client=mqtt_client)
    messenger.Dispatcher(
        name="pipeline-layer1",
        input_queue=_layer1_queue,
        output_queue=_layer2_queue,
        conditional_handlers=[
            (
                lambda msg: not messenger.is_type_discovery(msg),
                processor.ModelResolver().process,
            ),
        ],
        # copy Discovery message to output queue
        default_handler=lambda msg: _get_device_state(msg, _accessor),
    )
    messenger.Dispatcher(
        name="normalizer",
        input_queue=_layer2_queue,
        output_queue=_refined_queue,
        conditional_handlers=[
            (
                messenger.is_type_availability,
                processor.AvailabilityNormalizer().process,
            ),
            (
                messenger.is_type_state,
                processor.StateNormalizer().process,
            ),
        ],
        # copy Discovery message to output queue
        default_handler=processor.Processor.pass_through,
    )
    return _refined_queue


_CONFIG_DEVICE = {
    (dev.Model.SN_MINI, dev.Protocol.Z2M): {"state": ""},
    (dev.Model.SN_MINI_L2, dev.Protocol.Z2M): {"state": ""},
    (dev.Model.SN_SMART_PLUG, dev.Protocol.Z2M): {"state": ""},
    (dev.Model.SHELLY_PLUGS, dev.Protocol.TASMOTA): {"POWER": ""},
    (dev.Model.SHELLY_UNI, dev.Protocol.TASMOTA): {"POWER1": "", "POWER2": ""},
}


def _config_device(
    message: messenger.Message, accessor: DeviceAccessor
) -> Optional[messenger.Message]:
    _registry = message.refined
    for _device_name in _registry.device_names:
        _device: Optional[dev.Device] = processor.DeviceDirectory.get_device(
            _device_name
        )
        _model = _device.model
        _protocol = _device.protocol
        _config_payload = _CONFIG_DEVICE.get((_model, _protocol))
        if _config_payload is None:
            utils.i2m_log.warning("No config payload for %s", _device_name)
            continue
        utils.i2m_log.info(
            "Device: %s - Model: %s - Protocol: %s - Payload: %s",
            _device_name,
            _model,
            _protocol,
            _config_payload,
        )
        accessor.trigger_change_state(_device_name, _protocol, _config_payload)
    return message


def _get_device_state(
    message: messenger.Message, accessor: DeviceAccessor
) -> Optional[messenger.Message]:
    _registry = message.refined
    for _device_name in _registry.device_names:
        _device: Optional[dev.Device] = processor.DeviceDirectory.get_device(
            _device_name
        )
        _model = _device.model
        _protocol = _device.protocol
        accessor.trigger_get_state(_device_name, protocol=_protocol, model=_model)
    return message


_InfoTopicManager().configure_topic_registry()
_CommandTopicManager().configure_topic_registry()
