#!/usr/local/bin/python3
# coding=utf-8
"""
This module provides various classes and functions for processing IoT messages within the 
iot2mqtt framework. It includes abstract base classes, utility functions, and concrete 
implementations for handling different types of messages and device protocols.

"""

from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, ValidationError
from pydantic_core import PydanticSerializationError

from iot2mqtt import abstract, dev, exceptions, messenger, topics, utils


class Processor(metaclass=ABCMeta):
    """
    An abstract base class for processing messages.

    The `Processor` class defines the interface for processing messages. Subclasses must
    implement the `process` method. It also provides static methods for no-op and pass-through
    message handling.
    """

    @abstractmethod
    def process(self, message: messenger.Message) -> Optional[messenger.Message]:
        pass

    @staticmethod
    def no_op(message: messenger.Message) -> None:
        """Default no-op function when message callback is not provided."""
        # utils.i2m_log.debug("Incoming message not processed: %s", message)
        return None

    @staticmethod
    def pass_through(message: messenger.Message) -> messenger.Message:
        """Copy of the message without any processing."""
        return message


def _check_devices(msg: messenger.Message, device_ids: str) -> bool:
    """
    Checks if the given message is for one of the specified device names.

    Args:
        msg (messenger.Message): The message to check.
        device_ids (str): The device name, a comma-separated list of device ids
            or `*` for all to check for.

    Returns:
        bool: True if the message is for one of the specified device names, False otherwise.
    """
    utils.check_parameter("device_ids", device_ids, str)
    if "*" in device_ids:
        return True
    device_id_list = device_ids.split(",")
    return msg.device_id in device_id_list


def _check_message_typing(
    msg: messenger.Message, expected_type: Type[abstract.DeviceState]
) -> bool:
    utils.check_parameter("msg", msg, messenger.Message)
    if msg.refined is None:
        return False
    if not messenger.is_type_state(msg):
        return False
    if not isinstance(msg.refined, expected_type):
        raise TypeError(
            f"Message should refer to {expected_type},"
            f" got {msg.refined} of class {type(msg.refined).__name__}"
        )
    return True


def is_message_typing(
    msg: messenger.Message, expected_type: Type[abstract.DeviceState]
) -> bool:
    """
    Checks if the given message is of the expected type.
    """
    utils.check_parameter("msg", msg, messenger.Message)
    if msg.refined is None:
        return False
    if not messenger.is_type_state(msg):
        return False
    return isinstance(msg.refined, expected_type)


def is_motion_detected(msg: messenger.Message, device_ids: str) -> bool:
    """
    Checks if motion is detected in the given message for the specified device.

    Args:
        msg (messenger.Message): The message to check for motion detection.
        device_ids (str): The device name, a comma-separated list of device ids
            or `*` for all to check for motion.

    Returns:
        bool: True if motion is detected, False otherwise.
    """
    if _check_devices(msg, device_ids) and _check_message_typing(msg, abstract.Motion):
        return msg.refined.occupancy
    return False


def is_button_action_expected(
    msg: messenger.Message, device_ids: str, action: dev.ButtonAction
) -> bool:
    """
    Checks if the given message contains a button action for the specified device.

    Args:
        msg (messenger.Message): The message to check for a button action.
        device_ids (str): The device name, a comma-separated list of device ids
            or `*` for all to check for button press.
        action (dev.ButtonAction): The button action to check for.

    Returns:
        bool: True if the message contains the specified button action, False otherwise.
    """
    utils.check_parameter("action", action, abstract.ButtonValues)
    if _check_devices(msg, device_ids) and _check_message_typing(msg, abstract.Button):
        return msg.refined.action == action
    return False


def is_switch_power_expected(
    msg: messenger.Message, device_ids: Optional[str], is_on: bool
) -> bool:
    """
    Checks if the power status of the switch is as expected.

    Args:
        msg (messenger.Message): The message containing the switch state.
        device_ids (str): The device name, a comma-separated list of device ids
                or `*` for all to check for switch state.
        is_on (bool): The expected power status of the switch.

    Returns:
        bool: True if the power status of the switch is as expected, False otherwise.
    """
    utils.check_parameter("is_on", is_on, bool)

    if _check_devices(msg, device_ids) and _check_message_typing(
        msg, (abstract.Switch, abstract.Switch2Channels)
    ):
        return msg.refined.power == abstract.POWER_ON if is_on else abstract.POWER_OFF
    return False


class MessageLogger(Processor):
    """
    A processor that logs messages for debugging purposes.

    The `MessageLogger` class processes messages by logging them using the configured logger.
    """

    def process(self, message: messenger.Message) -> None:
        """
        Logs the given message for debugging purposes.

        Args:
            message (messenger.Message): The message to be logged.

        Returns:
            None
        """
        utils.i2m_log.debug(message)


class MessageWritter(Processor):
    """
    A processor that writes messages to a file.

    The `MessageWritter` class processes messages by writing them to a specified file in
    JSON format. It ensures that the file is properly opened and closed.
    """

    def __init__(self, file_name: str) -> None:
        self._file = open(file_name, "w", encoding="utf-8")

    def process(self, message: messenger.Message) -> messenger.Message:
        """
        Initializes the MessageWritter with the specified file name.

        Args:
            file_name (str): The name of the file where messages will be written.

        Returns:
            None
        """
        try:
            self._file.write("\n," + message.model_dump_json(indent=4))
        except PydanticSerializationError:
            utils.i2m_log.warning("Error while writing message to file")
        self._file.flush()
        return None

    def __del__(self):
        # Properly close file if an exception occures
        self._file.close()


class ModelResolver(Processor):
    """
    A processor that resolves the model of a device based on its name.

    The `ModelResolver` class processes messages to determine the model of the device
    by looking it up in the device directory. If the model is unknown, it logs a warning.
    """

    _notified_devices = {}

    def _notify_once(self, message: messenger.Message) -> None:
        _device_id = message.device_id
        if _device_id in self._notified_devices:
            return
        utils.i2m_log.warning(
            '["%s"] unable to normalyse message - device_id: "%s" - type: %s - value: %s',
            self.__class__.__name__,
            _device_id,
            message.message_type.value,
            message.raw_item.data,
        )
        self._notified_devices[_device_id] = True

    def process(self, message: messenger.Message) -> Optional[messenger.Message]:
        """
        Resolves the model of the device in the given message.

        Args:
            message (messenger.Message): The message containing the device name.

        Returns:
            Optional[messenger.Message]: The message with the resolved model, or the original
            message if the model is unknown.

        Raises:
            DecodingException: If a discovery message is received.

        """
        if message.message_type == messenger.MessageType.DISCO:
            raise exceptions.DecodingException(
                f"Discovery message not allowed: {message}"
            )
        if message.model is not None:
            # Model already set for protocol RING
            return message
        _device_id = message.device_id
        _device = Discoverer.directory.get_device(_device_id)
        message.model = _device.model if _device else dev.ModelFactory.UNKNOWN
        if message.model == dev.ModelFactory.UNKNOWN:
            self._notify_once(message)
        return message


class DeviceDirectory:
    """
    A directory for managing devices.

    The `DeviceDirectory` class provides methods to update, retrieve, and list devices.
    It maintains an internal dictionary to store device information.
    """

    _directory: Dict[str, dev.Device] = {}

    def update_devices(self, devices: List[dev.Device]) -> None:
        """
        Updates the device directory with a list of devices.

        Args:
            devices (List[dev.Device]): A list of devices to be added or updated in the directory.
        """
        if not isinstance(devices, list):
            raise TypeError("parameter 'devices' must be a list of devices")
        self._directory.update({device.name: device for device in devices})

    @staticmethod
    def get_device(device_id: str) -> Optional[dev.Device]:
        """
        Retrieves a device from the directory by its name.

        Args:
            device_id (str): The id of the device to retrieve.

        Returns:
            Optional[dev.Device]: The device object if found, otherwise None.
        """
        return DeviceDirectory._directory.get(device_id)

    @staticmethod
    def get_devices() -> List[dev.Device]:
        """
        Retrieves a list of all devices in the directory.

        Returns:
            List[dev.Device]: A list of all device objects in the directory.
        """
        return list(DeviceDirectory._directory.values())

    @staticmethod
    def get_device_ids() -> List[dev.Device]:
        """
        Retrieves a list of all device ids in the directory.

        Returns:
            List[dev.Device]: A list of all device ids in the directory.
        """
        return list(DeviceDirectory._directory.keys())


# ESPSomfy discovery message example :
#    {'config': {'~': 'ESPSomfy/shades/2',
#                'device': {
#                    'via_device': 'mqtt_espsomfyrts_ABCA6C',
#                    'model': 'ESPSomfy-RTS MQTT'}}
#    }


class ESPSomfyDevice(BaseModel, frozen=True):
    address: str = Field(alias="via_device", default=None)
    model: str


class ESPSomfyConfig(BaseModel, frozen=True):
    path: str = Field(alias="~", default=None)
    device: ESPSomfyDevice


class ESPSomfyDiscovery(BaseModel, frozen=True):
    """
    A dictionary representing the discovery message configuration of an ESPSomfy device.
    """

    config: ESPSomfyConfig


# Tasmota discovery message example :
#    {'ip': '192.168.1.25',
#    'dn': 'ZbBridge',
#    'hn': 'tasmota-9F808B-0139',
#    'mac': 'E8DB849F808B',
#    'md': 'Sonoff ZbBridge',
#    't': 'tasmota_9F808B'}


class TasmotaDiscovery(BaseModel, frozen=True):
    """
    A dictionary representing the discovery message configuration of an Tasmota device.
    """

    address: str = Field(alias="hn", default=None)
    model: str = Field(alias="md", default=None)
    device_id: str = Field(alias="t", default=None)


class Discoverer(Processor):
    """
    A processor that discovers and registers devices based on incoming discovery messages.

    The `Discoverer` class processes discovery messages from different protocols
    (e.g., Z2M, TASMOTA) to update the device directory with new devices and their details.
    """

    directory = DeviceDirectory()

    def process(self, message: messenger.Message) -> Optional[messenger.Message]:
        """
        Processes a discovery message to update the device directory and refine the message.

        Args:
            message (messenger.Message): The discovery message to be processed.

        Returns:
            Optional[messenger.Message]: The refined message with discovered devices, or the
            original message if the protocol is unknown.

        Raises:
            DecodingException: If not a discovery message.

        """

        if message.message_type != messenger.MessageType.DISCO:
            raise exceptions.DecodingException(
                f"Not a discovery message: {message.message_type}"
            )
        if message.protocol == dev.Protocol.Z2M:
            return self._discover_z2m(message)
        if message.protocol == dev.Protocol.TASMOTA:
            return self._discover_tasmota(message)
        if message.protocol == dev.Protocol.ESPSOMFY:
            return self._discover_espsomfy(message)
        if message.protocol == dev.Protocol.RING:
            return self._discover_ring(message)

        utils.i2m_log.info("Unknown protocol: %s", message.protocol)
        return message

    def _discover_z2m(self, message: messenger.Message) -> Optional[messenger.Message]:
        _key_name = "friendly_name"
        _key_address = "ieee_address"
        _key_model = "model"
        _key_definition = "definition"
        _key_type = "type"
        _device_types = ["EndDevice", "Router"]
        # Magic strings
        NO_DEFINITION = "NO_DEFINITION"
        NO_MODEL = "NO_MODEL"
        NO_FRIENDLY_NAME = "NO_FRIENDLY_NAME"
        NO_IEEE_ADDRESS = "NO_IEEE_ADDRESS"

        def _device_dict(
            raw_message: dict, device_type_list: List[str]
        ) -> List[dev.Device]:
            def _get_model(entry: dict) -> str:
                _definition = entry.get(_key_definition)
                if not _definition:
                    utils.i2m_log.warning(
                        "[%s]: no 'definition' key in raw data : %s",
                        entry.get(_key_name),
                        entry,
                    )
                    return NO_DEFINITION
                _model = _definition.get(_key_model)
                if not _model:
                    utils.i2m_log.warning(
                        "[%s]: no 'model' key in definition data: %s",
                        entry.get(_key_name),
                        _definition,
                    )
                    return NO_MODEL
                return _model

            return [
                dev.Device(
                    name=entry.get(_key_name, NO_FRIENDLY_NAME),
                    protocol=dev.Protocol.Z2M,
                    address=entry.get(_key_address, NO_IEEE_ADDRESS),
                    model=dev.ModelFactory.get(_get_model(entry)),
                )
                for entry in raw_message
                if entry.get(_key_type) in device_type_list
            ]

        def _device_list(raw_message: dict, device_type_list: List[str]) -> List[str]:
            return [
                entry.get(_key_name)
                for entry in raw_message
                if entry.get(_key_type) in device_type_list
            ]

        _raw_data = message.raw_item.data
        if not isinstance(_raw_data, list):
            raise exceptions.DecodingException(
                f"Bad format: {message} - "
                f"Expected list, got {type(_raw_data).__name__}"
            )

        _discovery_result = _device_dict(_raw_data, device_type_list=_device_types)
        self.directory.update_devices(_discovery_result)
        _devices = _device_list(_raw_data, device_type_list=_device_types)
        message.refined = abstract.Registry(device_ids=_devices)
        return message

    def _discover_tasmota(
        self, message: messenger.Message
    ) -> Optional[messenger.Message]:
        _raw_data = message.raw_item.data
        if not _raw_data:
            raise exceptions.DecodingException("Empty raw data received")
        try:
            _discovery = TasmotaDiscovery(**_raw_data)
        except ValidationError as exc:
            utils.i2m_log.error(
                "Error when refining raw data: '%s': %s", _raw_data, exc
            )
            return None

        _device = dev.Device(
            address=_discovery.address,
            name=_discovery.device_id,
            model=dev.ModelFactory.get(_discovery.model),
            protocol=dev.Protocol.TASMOTA,
        )
        self.directory.update_devices([_device])
        message.refined = abstract.Registry(device_ids=[_discovery.device_id])
        return message

    def _discover_espsomfy(
        self, message: messenger.Message
    ) -> Optional[messenger.Message]:
        _raw_data = message.raw_item.data
        if not _raw_data:
            raise exceptions.DecodingException("Empty raw data received")
        try:
            _discovery = ESPSomfyDiscovery(**_raw_data)
        except ValidationError as exc:
            utils.i2m_log.error(
                "Error when refining raw data: '%s': %s", _raw_data, exc
            )
            return None
        _path = str(_discovery.config.path)
        _index = _path.split("/")[-1]
        _device_id = _index

        _device = dev.Device(
            address=_discovery.config.device.address,
            name=_device_id,
            model=dev.ModelFactory.get(_discovery.config.device.model),
            protocol=dev.Protocol.ESPSOMFY,
        )
        self.directory.update_devices([_device])
        message.refined = abstract.Registry(device_ids=[_device_id])
        return message

    def _discover_ring(self, message: messenger.Message) -> Optional[messenger.Message]:
        _device_id = topics.InfoTopicManager().get_device_id(
            protocol=dev.Protocol.RING,
            message_type=messenger.MessageType.DISCO,
            topic=message.topic,
        )
        _model = topics.InfoTopicManager().get_model(
            protocol=dev.Protocol.RING,
            message_type=messenger.MessageType.DISCO,
            topic=message.topic,
        )
        _location_id = topics.InfoTopicManager().get_ring_location_id(
            message_type=messenger.MessageType.DISCO,
            topic=message.topic,
        )
        if self.directory.get_device(_device_id) is not None:
            return None
        _device = dev.RingDevice(
            address=_device_id,
            name=_device_id,
            model=_model,
            protocol=dev.Protocol.RING,
            location_id=_location_id,
        )
        self.directory.update_devices([_device])
        message.refined = abstract.Registry(device_ids=[_device_id])
        return message


class AvailabilityNormalizer(Processor):
    """
    A processor that normalizes the availability status of devices based on their protocol and
    raw message data.

    The `AvailabilityNormalizer` class is responsible for interpreting raw availability data
    from different protocols (e.g., TASMOTA, Z2M) and converting it into a standardized
    `Availability` object indicating whetherthe device is online or offline.

    Constants:
        - ONLINE (abstract.Availability): Represents an online availability status.
        - OFFLINE (abstract.Availability): Represents an offline availability status.
    """

    ONLINE = abstract.Availability(is_online=True)
    OFFLINE = abstract.Availability(is_online=False)

    def _decode_availability(self, value: str, on_token: str, off_token: str) -> bool:
        if value not in (on_token, off_token):
            raise exceptions.DecodingException(f"Unknown availability value: {value}")
        return value == on_token

    def process(self, message: messenger.Message) -> Optional[messenger.Message]:
        """
        Processes a message to normalize its availability status based on the device protocol
        and raw data.

        Args:
            message (messenger.Message): The message containing raw availability data to be
                normalized.

        Returns:
            Optional[messenger.Message]: The message with refined availability data, or None
            if the message available.

        Raises:
            DecodingException: If the message type is not available, the protocol is
            not supported, or the raw data format is incorrect.
        """
        if message.message_type != messenger.MessageType.AVAIL:
            raise exceptions.DecodingException("Not an availability message: {message}")
        _raw_data = message.raw_item.data
        if message.protocol == dev.Protocol.TASMOTA:
            _raw_avail_value = self._decode_availability(_raw_data, "Online", "Offline")
        elif message.protocol == dev.Protocol.ESPSOMFY:
            _raw_avail_value = self._decode_availability(_raw_data, "online", "offline")
        elif message.protocol == dev.Protocol.RING:
            _raw_avail_value = self._decode_availability(_raw_data, "online", "offline")
        elif message.protocol == dev.Protocol.Z2M:
            if isinstance(_raw_data, dict):
                _avail_value = _raw_data.get("state")
            elif isinstance(_raw_data, str):
                _avail_value = _raw_data
            else:
                raise exceptions.DecodingException(
                    f"Bad type {type(_raw_data)}" f"for device {message.device_id}"
                )
            _raw_avail_value = self._decode_availability(
                _avail_value, "online", "offline"
            )
        else:
            raise exceptions.DecodingException(
                f"Protocol {message} not covered " f"for device {message.device_id}"
            )
        message.refined = self.ONLINE if _raw_avail_value else self.OFFLINE
        return message


class StateNormalizerFactory:
    """
    Factory class for managing state normalizers for different device models.

    This class provides methods to register and retrieve state normalizers, which are responsible
    for refining raw message data into structured device state representations. It maintains an
    internal registry to store the mapping between device models and their corresponding state
    normalizers.

    """

    _registry: Dict[dev.Model, Type[abstract.DeviceState]] = {}

    def __init__(
        self,
        initial_registry: Optional[Dict[dev.Model, Type[abstract.DeviceState]]] = None,
    ) -> None:
        """
        Initialize the factory with an optional initial registry.

        Args:
            initial_registry (Optional[Dict[dev.Model, Type[abstract.DeviceState]]]): An optional
                dictionary to initialize the registry with. If provided, the dictionary will be
                used to update the internal registry.
        """
        if initial_registry:
            self._registry.update(initial_registry)

    @classmethod
    def get(cls, model: dev.Model) -> Optional[Type[abstract.DeviceState]]:
        """
        Retrieve the target abstract type for a given model.

        Args:
            model (dev.Model): The device model for which to retrieve the state normalizer.

        Returns:
            Optional[Type[abstract.DeviceState]]: The state normalizer class for the given model,
            or None if the model is not found in the registry.
        """
        return cls._registry.get(model)

    @classmethod
    def register(
        cls, model: dev.Model, abstract_type: Type[abstract.DeviceState]
    ) -> None:
        """
        Register a target abstract type for the given model.

        Args:
            model (dev.Model): The device model to register.
            abstract_type (Type[abstract.DeviceState]): The state normalizer class to associate
                with the given model.
        """
        cls._registry[model] = abstract_type


class StateNormalizer(Processor):
    """
    A processor that normalizes the state of various devices based on their model and protocol.

    The `StateNormalizer` class is responsible for refining raw message data into structured
    device state representations. It supports different device models and protocols.
    """

    _notified_devices = {}

    def _notify_once(self, message: messenger.Message) -> None:
        _device_id = message.device_id
        if _device_id in self._notified_devices:
            return
        utils.i2m_log.warning(
            '["%s"] unable to normalyse message - device_id: "%s" - type: %s - model: %s - value: %s',
            self.__class__.__name__,
            _device_id,
            message.message_type.value,
            message.model if message.model else "Unset",
            message.raw_item.data,
        )
        self._notified_devices[_device_id] = True

    def process(self, message: messenger.Message) -> Optional[messenger.Message]:
        """
        Processes a message to normalize its state based on the device model and protocol.

        Args:
            message (messenger.Message): The message containing raw data to be normalized.

        Returns:
            Optional[messenger.Message]: The message with refined state data, or None if no
            refinement is possible.

        Raises:
            DecodingException: If the message model is not supported, the raw data format
                is incorrect, or an error occurs during the refinement process.
        """
        if message.message_type != messenger.MessageType.STATE:
            raise exceptions.DecodingException(
                f"Not a state message: {message.message_type}"
            )
        _raw_data = message.raw_item.data
        if not isinstance(_raw_data, dict):
            raise exceptions.DecodingException(f"Bad format: {message}")

        _target_class = StateNormalizerFactory.get(message.model)
        if not _target_class:
            self._notify_once(message)
            return None
        try:
            message.refined = _target_class(**_raw_data)
        except ValidationError as exc:
            utils.i2m_log.error("Error refining raw data: %s \n %s", exc, _raw_data)
            return None
        except exceptions.NoValueException as exc:
            # Silently ignore empty values
            utils.i2m_log.debug("[%s] Exception: %s", message.device_id, exc)
            return None

        return message
