#!/usr/local/bin/python3
# coding=utf-8
"""
Processor Module

This module provides various classes and functions for processing IoT messages within the 
iot2mqtt framework. It includes abstract base classes, utility functions, and concrete 
implementations for handling different types of messages and device protocols.

"""

from abc import ABCMeta, abstractmethod
from typing import Dict, List, Optional, Type

from pydantic import ValidationError

from iot2mqtt import abstract, dev, messenger, utils


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


def _check_devices(msg: messenger.Message, device_names: str) -> bool:
    """
    Checks if the given message is for one of the specified device names.

    Args:
        msg (messenger.Message): The message to check.
        device_names (str): The device name, a comma-separated list of device names
            or `*` for all to check for.

    Returns:
        bool: True if the message is for one of the specified device names, False otherwise.
    """
    utils.check_parameter("device_names", device_names, str)
    if "*" in device_names:
        return True
    device_name_list = device_names.split(",")
    return msg.device_name in device_name_list


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
            f"Message should refer to {expected_type}, got {msg.refined} of class {type(msg.refined).__name__}"
        )
    return True


def is_motion_detected(msg: messenger.Message, device_names: str) -> bool:
    """
    Checks if motion is detected in the given message for the specified device.

    Args:
        msg (messenger.Message): The message to check for motion detection.
        device_names (str): The device name, a comma-separated list of device names
            or `*` for all to check for motion.

    Returns:
        bool: True if motion is detected, False otherwise.
    """
    if _check_devices(msg, device_names) and _check_message_typing(
        msg, abstract.Motion
    ):
        return msg.refined.occupancy
    return False


def is_button_action_expected(
    msg: messenger.Message, device_names: str, action: dev.ButtonAction
) -> bool:
    """
    Checks if the given message contains a button action for the specified device.

    Args:
        msg (messenger.Message): The message to check for a button action.
        device_names (str): The device name, a comma-separated list of device names
            or `*` for all to check for button press.
        action (dev.ButtonAction): The button action to check for.

    Returns:
        bool: True if the message contains the specified button action, False otherwise.
    """
    utils.check_parameter("action", action, abstract.ButtonValues)
    if _check_devices(msg, device_names) and _check_message_typing(
        msg, abstract.Button
    ):
        return msg.refined.action == action
    return False


def is_switch_power_expected(
    msg: messenger.Message, device_names: Optional[str], is_on: bool
) -> bool:
    """
    Checks if the power status of the switch is as expected.

    Args:
        msg (messenger.Message): The message containing the switch state.
        device_names (str): The device name, a comma-separated list of device names
                or `*` for all to check for switch state.
        is_on (bool): The expected power status of the switch.

    Returns:
        bool: True if the power status of the switch is as expected, False otherwise.
    """
    utils.check_parameter("is_on", is_on, bool)

    if _check_devices(msg, device_names) and _check_message_typing(
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
        self._file.write("\n," + message.model_dump_json(indent=4))
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

    def process(self, message: messenger.Message) -> Optional[messenger.Message]:
        """
        Resolves the model of the device in the given message.

        Args:
            message (messenger.Message): The message containing the device name.

        Returns:
            Optional[messenger.Message]: The message with the resolved model, or the original
            message if the model is unknown.

        Raises:
            DecodingException: If a discovery message.

        """
        if message.message_type == messenger.MessageType.DISCO:
            _error_msg = f"Discovery message not allowed: {message}"
            raise DecodingException(_error_msg)
        _device_name = message.device_name
        _device = Discoverer.directory.get_device(_device_name)
        message.model = _device.model if _device else dev.Model.UNKNOWN
        if message.model == dev.Model.UNKNOWN:
            utils.i2m_log.debug(
                "[%s]: message type: %s - unknown model for: %s",
                self.__class__.__name__,
                message.message_type,
                _device_name,
            )
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
        self._directory.update({device.name: device for device in devices})

    @staticmethod
    def get_device(device_name: str) -> Optional[dev.Device]:
        """
        Retrieves a device from the directory by its name.

        Args:
            device_name (str): The name of the device to retrieve.

        Returns:
            Optional[dev.Device]: The device object if found, otherwise None.
        """
        return DeviceDirectory._directory.get(device_name)

    @staticmethod
    def get_devices() -> List[dev.Device]:
        """
        Retrieves a list of all devices in the directory.

        Returns:
            List[dev.Device]: A list of all device objects in the directory.
        """
        return list(DeviceDirectory._directory.values())

    @staticmethod
    def get_device_names() -> List[dev.Device]:
        """
        Retrieves a list of all device names in the directory.

        Returns:
            List[dev.Device]: A list of all device names in the directory.
        """
        return list(DeviceDirectory._directory.keys())


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
            _error_msg = f"Not a discovery message: {message.message_type}"
            raise DecodingException(_error_msg)
        message.model = dev.Model.NONE
        if message.protocol == dev.Protocol.Z2M:
            return self._discover_z2m(message)
        if message.protocol == dev.Protocol.TASMOTA:
            return self._discover_tasmota(message)

        _error_msg = f"Unknown protocol: {message.protocol}"
        utils.i2m_log.info(_error_msg)
        return message

    def _discover_z2m(self, message: messenger.Message) -> Optional[messenger.Message]:
        def _device_dict(raw_message: dict, device_type_list: List[str]) -> Dict:
            return [
                dev.Device(
                    name=entry.get("friendly_name"),
                    protocol=dev.Protocol.Z2M,
                    address=entry.get("ieee_address"),
                    model=dev.Model.from_str(entry.get("definition", {}).get("model")),
                )
                for entry in raw_message
                if entry.get("type") in device_type_list
            ]

        def _device_list(raw_message: dict, device_type_list: List[str]) -> Dict:
            return [
                entry.get("friendly_name")
                for entry in raw_message
                if entry.get("type") in device_type_list
            ]

        device_types = [
            "EndDevice",
            "Router",
        ]
        _raw_data = message.raw_item.data
        if not isinstance(_raw_data, list):
            _error_msg = f"Bad format: {message}"
            raise DecodingException(_error_msg)
        _discovery_result = _device_dict(_raw_data, device_type_list=device_types)
        self.directory.update_devices(_discovery_result)
        _devices = _device_list(_raw_data, device_type_list=device_types)
        message.refined = abstract.Registry(device_names=_devices)
        return message

    def _discover_tasmota(
        self, message: messenger.Message
    ) -> Optional[messenger.Message]:
        _key_name = "t"
        _key_address = "hn"
        _key_model = "md"

        _raw_data = message.raw_item.data
        if not isinstance(_raw_data, dict):
            _error_msg = f"Expecting dict type for: {message}"
            raise DecodingException(_error_msg)
        if not all(k in _raw_data for k in (_key_address, _key_name, _key_model)):
            _error_msg = f"Bad format for: {message}"
            raise DecodingException(_error_msg)
        _device_name = _raw_data.get(_key_name)
        _device_address = _raw_data.get(_key_address)
        _device_model = _raw_data.get(_key_model)
        _device = dev.Device(
            address=_device_address,
            name=_device_name,
            model=dev.Model.from_str(_device_model),
            protocol=dev.Protocol.TASMOTA,
        )
        self.directory.update_devices([_device])
        message.refined = abstract.Registry(device_names=[_device_name])
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
            _error_msg = f"Unknown availability value: {value}"
            raise DecodingException(_error_msg)
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
            _error_msg = f"Not an availability message: {message}"
            raise DecodingException(_error_msg)
        _raw_data = message.raw_item.data
        if message.protocol == dev.Protocol.TASMOTA:
            _raw_avail_value = self._decode_availability(_raw_data, "Online", "Offline")
        elif message.protocol == dev.Protocol.Z2M:
            if isinstance(_raw_data, dict):
                _avail_value = _raw_data.get("state")
            elif isinstance(_raw_data, str):
                _avail_value = _raw_data
            else:
                _error_msg = (
                    f"Bad type {type(_raw_data)} for device {message.device_name}"
                )
                raise DecodingException(_error_msg)
            _raw_avail_value = self._decode_availability(
                _avail_value, "online", "offline"
            )
        else:
            _error_msg = (
                f"Protocol {message} not covered for device {message.device_name}"
            )
            raise DecodingException(_error_msg)
        message.refined = self.ONLINE if _raw_avail_value else self.OFFLINE
        return message


class StateNormalizer(Processor):
    """
    A processor that normalizes the state of various devices based on their model and protocol.

    The `StateNormalizer` class is responsible for refining raw message data into structured
    device state representations. It supports different device models and protocols.
    """

    _REFINE_CONFIG = {
        dev.Model.SN_AIRSENSOR: abstract.AirSensor,
        dev.Model.SN_MINI: abstract.Switch,
        dev.Model.SN_MINI_L2: abstract.Switch,
        dev.Model.SN_SMART_PLUG: abstract.Switch,
        dev.Model.SHELLY_PLUGS: abstract.Switch,
        dev.Model.SHELLY_UNI: abstract.Switch2Channels,
        dev.Model.SN_MOTION: abstract.Motion,
        dev.Model.SN_BUTTON: abstract.Button,
        dev.Model.SRTS_A01: abstract.SrtsA01,
        dev.Model.NEO_ALARM: abstract.Alarm,
    }

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
            _error_msg = f"Not a state message: {message.message_type}"
            raise DecodingException(_error_msg)
        _raw_data = message.raw_item.data
        _tag = message.raw_item.tag
        _target_class = self._REFINE_CONFIG.get(message.model)
        if message.protocol == dev.Protocol.Z2M:
            if not _target_class:
                _error_msg = (
                    f"[{message.device_name}] Model {message.model} not supported"
                )
                utils.i2m_log.warning(_error_msg)
                return None
            if not isinstance(_raw_data, dict):
                _error_msg = f"Bad format: {message}"
                raise DecodingException(_error_msg)
            try:
                message.refined = _target_class(**_raw_data)
                return message
            except ValidationError as exc:
                _error_msg = f"Error when refining raw data: '{_raw_data}': {exc}"
                utils.i2m_log.error(_error_msg)
                raise DecodingException(_error_msg)  # Re-raise the exception
        if message.protocol == dev.Protocol.TASMOTA:
            if _tag == "STATE":
                if _raw_data is None:
                    _error_msg = f"Bad format: {message}"
                    raise DecodingException(_error_msg)
                if not _target_class:
                    _error_msg = (
                        f"[{message.device_name}] Model {message.model} not supported"
                    )
                    utils.i2m_log.warning(_error_msg)
                    return None
                message.refined = _target_class(**_raw_data)
                return message
            if _tag == "SENSOR":
                _analog = _raw_data.get("ANALOG")
                _energy = _raw_data.get("ENERGY")
                if _analog is not None:
                    utils.i2m_log.debug("Analog: %s", _analog)
                if _energy is not None:
                    utils.i2m_log.debug("Energy: %s", _energy)
                return message
        utils.i2m_log.warning("No state normalizer for %s", message.device_name)
        return None  # No refinement


class DecodingException(Exception):
    """
    Exception raised for errors in the decoding process.

    This exception is raised when a message is received on the wrong topic
    or when there is an issue with decoding the message.

    Attributes:
        message (str): The error message describing the exception.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
