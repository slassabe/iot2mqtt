# coding=utf-8
"""Message processing for IoT protocols.

Provides abstract and concrete processors for handling discovery, availability, and state
messages from different IoT device protocols (Z2M, TASMOTA, ESPSOMFY, RING). Includes
device registry management, message normalization, and state refinement utilities.

Key entry points: Processor, Discoverer, AvailabilityNormalizer, StateNormalizer.
"""

from abc import ABCMeta, abstractmethod
from typing import Dict, List, Optional, Type

from pydantic import BaseModel, Field, ValidationError
from pydantic_core import PydanticSerializationError

from iot2mqtt import dev, messenger, topics
from iot2mqtt.core import exceptions, utils
from iot2mqtt.devices.common_abstract import (
    POWER_OFF,
    POWER_ON,
    Availability,
    DeviceState,
    Registry,
    Switch,
    Switch2Channels,
)
from iot2mqtt.devices.zigbee_abstract import Button, ButtonValues, Motion


class Processor(metaclass=ABCMeta):
    """Abstract base for message processors.

    Subclasses implement the `process` method to refine or handle messages.
    """

    @abstractmethod
    def process(self, message: messenger.Message) -> Optional[messenger.Message]:
        """Process a message.

        Args:
            message: The message to process.

        Returns:
            The processed message, or None if not processed.
        """

    @staticmethod
    def no_op(message: messenger.Message) -> None:
        """No-op handler for messages that should not be processed."""

    @staticmethod
    def pass_through(message: messenger.Message) -> messenger.Message:
        """Return the message unchanged."""
        return message


def _check_devices(msg: messenger.Message, device_ids: str) -> bool:
    """Check if a message is for specified device IDs.

    Args:
        msg: The message to check.
        device_ids: A device ID, comma-separated list of device IDs, or '*' for all.

    Returns:
        True if the message is for one of the specified devices.
    """
    utils.check_parameter("device_ids", device_ids, str)
    if "*" in device_ids:
        return True
    device_id_list = device_ids.split(",")
    return msg.device_id in device_id_list


def _check_message_typing(msg: messenger.Message, expected_type: Type[DeviceState]) -> bool:
    """Check if a message contains a refined state of the expected type.

    Raises TypeError if refined state exists but is not of the expected type.
    """
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


def is_message_typing(msg: messenger.Message, expected_type: Type[DeviceState]) -> bool:
    """Check if a message contains a refined state of the expected type.

    Returns False if no refined state exists or state is not of expected type.
    """
    utils.check_parameter("msg", msg, messenger.Message)
    if msg.refined is None:
        return False
    if not messenger.is_type_state(msg):
        return False
    return isinstance(msg.refined, expected_type)


def is_motion_detected(msg: messenger.Message, device_ids: str) -> bool:
    """Check if motion is detected in a message for specified devices.

    Args:
        msg: The message to check.
        device_ids: A device ID, comma-separated list of device IDs, or '*' for all.

    Returns:
        True if motion is detected for one of the specified devices.
    """
    if _check_devices(msg, device_ids) and _check_message_typing(msg, Motion):
        return msg.refined.occupancy
    return False


def is_button_action_expected(
    msg: messenger.Message, device_ids: str, action: dev.ButtonAction
) -> bool:
    """Check if a message contains the expected button action for specified devices.

    Args:
        msg: The message to check.
        device_ids: A device ID, comma-separated list of device IDs, or '*' for all.
        action: The button action to match.

    Returns:
        True if the message contains the expected button action for one of the specified devices.
    """
    utils.check_parameter("action", action, ButtonValues)
    if _check_devices(msg, device_ids) and _check_message_typing(msg, Button):
        return msg.refined.action == action
    return False


def is_switch_power_expected(
    msg: messenger.Message, device_ids: Optional[str], is_on: bool
) -> bool:
    """Check if switch power status matches expected state.

    Args:
        msg: The message containing the switch state.
        device_ids: A device ID, comma-separated list of device IDs, or '*' for all.
        is_on: Expected power status (True for on, False for off).

    Returns:
        True if switch power status matches the expected state for one of the specified devices.
    """
    utils.check_parameter("is_on", is_on, bool)

    if _check_devices(msg, device_ids) and _check_message_typing(msg, (Switch, Switch2Channels)):
        return msg.refined.power == POWER_ON if is_on else POWER_OFF
    return False


class MessageLogger(Processor):
    """Processor that logs messages for debugging."""

    def process(self, message: messenger.Message) -> None:
        """Log the message at debug level."""
        utils.i2m_log.debug(message)


class MessageWritter(Processor):
    """Processor that writes messages to a file in JSON format."""

    def __init__(self, file_name: str) -> None:
        """Open the file for writing.

        Args:
            file_name: Path to the file where messages will be written.
        """
        self._file = open(file_name, "w", encoding="utf-8")

    def process(self, message: messenger.Message) -> messenger.Message:
        """Write the message to the file and return None.

        Args:
            message: The message to write.

        Returns:
            None

        Logs a warning if serialization fails.
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
    """Processor that resolves device models from the device directory.

    If a device is not found, a warning is logged once per device ID.
    """

    _notified_devices = {}

    @classmethod
    def reset(cls) -> None:
        """Clear all registered notification records for testing."""
        cls._notified_devices.clear()

    def _notify_once(self, message: messenger.Message) -> None:
        """Log a warning for unknown device, once per device ID."""
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
        """Resolve and set the device model from the directory.

        Args:
            message: The message with a device ID to look up.

        Returns:
            The message with model set.

        Raises:
            DecodingException: If the message is a discovery message.
        """
        if message.message_type == messenger.MessageType.DISCO:
            raise exceptions.DecodingException(f"Discovery message not allowed: {message}")
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
    """Registry of discovered devices.

    Maintains a mapping from device ID to device object.
    """

    _directory: Dict[str, dev.Device] = {}

    @classmethod
    def reset(cls) -> None:
        """Clear all registered devices for testing."""
        cls._directory.clear()

    def update_devices(self, devices: List[dev.Device]) -> None:
        """Update the directory with devices, overwriting existing entries.

        Args:
            devices: Devices to add or update in the directory.

        Raises:
            TypeError: If devices is not a list.
        """
        if not isinstance(devices, list):
            raise TypeError("parameter 'devices' must be a list of devices")
        self._directory.update({device.name: device for device in devices})

    @staticmethod
    def get_device(device_id: str) -> Optional[dev.Device]:
        """Retrieve a device by ID.

        Args:
            device_id: The device ID to look up.

        Returns:
            The device if found, otherwise None.
        """
        return DeviceDirectory._directory.get(device_id)

    @staticmethod
    def get_devices() -> List[dev.Device]:
        """Retrieve all devices in the directory.

        Returns:
            List of all device objects.
        """
        return list(DeviceDirectory._directory.values())

    @staticmethod
    def get_device_ids() -> List[dev.Device]:
        """Retrieve all device IDs in the directory.

        Returns:
            List of all device IDs.
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
    """ESPSomfy discovery message structure."""

    config: ESPSomfyConfig


# Tasmota discovery message example :
#    {'ip': '192.168.1.25',
#    'dn': 'ZbBridge',
#    'hn': 'tasmota-9F808B-0139',
#    'mac': 'E8DB849F808B',
#    'md': 'Sonoff ZbBridge',
#    't': 'tasmota_9F808B'}


class TasmotaDiscovery(BaseModel, frozen=True):
    """Tasmota discovery message structure."""

    address: str = Field(alias="hn", default=None)
    model: str = Field(alias="md", default=None)
    device_id: str = Field(alias="t", default=None)


class Discoverer(Processor):
    """Processor that discovers and registers devices from discovery messages.

    Processes discovery messages from supported protocols (Z2M, TASMOTA, ESPSOMFY, RING)
    and updates the device directory.
    """

    directory = DeviceDirectory()

    def process(self, message: messenger.Message) -> Optional[messenger.Message]:
        """Process a discovery message to register devices.

        Args:
            message: The discovery message to process.

        Returns:
            Message with refined Registry of discovered device IDs, or None if protocol unknown.

        Raises:
            DecodingException: If message is not a discovery message.
        """

        if message.message_type != messenger.MessageType.DISCO:
            raise exceptions.DecodingException(f"Not a discovery message: {message.message_type}")
        if message.protocol == dev.Protocol.Z2M:
            return self._discover_z2m(message)
        if message.protocol == dev.Protocol.TASMOTA:
            return self._discover_tasmota(message)
        if message.protocol == dev.Protocol.ESPSOMFY:
            return self._discover_espsomfy(message)
        if message.protocol == dev.Protocol.RING:
            return self._discover_ring(message)

        utils.i2m_log.warning("Unknown protocol, dropping discovery message: %s", message.protocol)
        return None

    def _discover_z2m(self, message: messenger.Message) -> Optional[messenger.Message]:
        """Discover Z2M devices and update directory."""
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

        def _device_dict(raw_message: dict, device_type_list: List[str]) -> List[dev.Device]:
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
                f"Bad format: {message} - " f"Expected list, got {type(_raw_data).__name__}"
            )

        _discovery_result = _device_dict(_raw_data, device_type_list=_device_types)
        self.directory.update_devices(_discovery_result)
        _devices = _device_list(_raw_data, device_type_list=_device_types)
        message.refined = Registry(device_ids=_devices)
        return message

    def _discover_tasmota(self, message: messenger.Message) -> Optional[messenger.Message]:
        """Discover Tasmota device and update directory."""
        _raw_data = message.raw_item.data
        if not _raw_data:
            raise exceptions.DecodingException("Empty raw data received")
        try:
            _discovery = TasmotaDiscovery(**_raw_data)
        except ValidationError as exc:
            utils.i2m_log.error("Error when refining raw data: '%s': %s", _raw_data, exc)
            return None

        _device = dev.Device(
            address=_discovery.address,
            name=_discovery.device_id,
            model=dev.ModelFactory.get(_discovery.model),
            protocol=dev.Protocol.TASMOTA,
        )
        self.directory.update_devices([_device])
        message.refined = Registry(device_ids=[_discovery.device_id])
        return message

    def _discover_espsomfy(self, message: messenger.Message) -> Optional[messenger.Message]:
        """Discover ESPSomfy device and update directory."""
        _raw_data = message.raw_item.data
        if not _raw_data:
            raise exceptions.DecodingException("Empty raw data received")
        try:
            _discovery = ESPSomfyDiscovery(**_raw_data)
        except ValidationError as exc:
            utils.i2m_log.error("Error when refining raw data: '%s': %s", _raw_data, exc)
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
        message.refined = Registry(device_ids=[_device_id])
        return message

    def _discover_ring(self, message: messenger.Message) -> Optional[messenger.Message]:
        """Discover Ring device and update directory."""
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
        message.refined = Registry(device_ids=[_device_id])
        return message


class AvailabilityNormalizer(Processor):
    """Processor that normalizes device availability status.

    Interprets raw availability data from different protocols (TASMOTA, Z2M, ESPSOMFY, RING)
    and converts to a standardized Availability object.

    Class constants represent online/offline status.
    """

    ONLINE = Availability(is_online=True)
    OFFLINE = Availability(is_online=False)

    def _decode_availability(self, value: str, on_token: str, off_token: str) -> bool:
        """Decode raw availability value to boolean."""

    def process(self, message: messenger.Message) -> Optional[messenger.Message]:
        """Normalize message availability status based on protocol.

        Args:
            message: Message containing raw availability data.

        Returns:
            Message with refined Availability status.

        Raises:
            DecodingException: If message type is not availability, protocol is unsupported,
                or raw data format is incorrect.
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
            _raw_avail_value = self._decode_availability(_avail_value, "online", "offline")
        else:
            raise exceptions.DecodingException(
                f"Protocol {message} not covered " f"for device {message.device_id}"
            )
        message.refined = self.ONLINE if _raw_avail_value else self.OFFLINE
        return message


class StateNormalizerFactory:
    """Registry of state normalizers for device models.

    Maps device models to their corresponding DeviceState classes for message refinement.
    """

    _registry: Dict[dev.Model, Type[DeviceState]] = {}

    @classmethod
    def reset(cls) -> None:
        """Clear all registered normalizers for testing."""
        cls._registry.clear()

    def __init__(
        self,
        initial_registry: Optional[Dict[dev.Model, Type[DeviceState]]] = None,
    ) -> None:
        """Initialize registry with optional initial mappings.

        Args:
            initial_registry: Optional dictionary of model-to-state-class mappings to load.
        """
        if initial_registry:
            self._registry.update(initial_registry)

    @classmethod
    def get(cls, model: dev.Model) -> Optional[Type[DeviceState]]:
        """Retrieve the state normalizer class for a model.

        Args:
            model: Device model to look up.

        Returns:
            The state normalizer class for the model, or None if not registered.
        """
        return cls._registry.get(model)

    @classmethod
    def register(cls, model: dev.Model, abstract_type: Type[DeviceState]) -> None:
        """Register a state normalizer for a device model.

        Args:
            model: Device model to register.
            abstract_type: State normalizer class for the model.
        """
        cls._registry[model] = abstract_type


class StateNormalizer(Processor):
    """Processor that normalizes device state messages based on model.

    Refines raw message data into structured DeviceState objects using registered
    state normalizers. Logs a warning once per device if normalization fails.
    """

    _notified_devices = {}

    @classmethod
    def reset(cls) -> None:
        """Clear all notification records for testing."""
        cls._notified_devices.clear()

    def _notify_once(self, message: messenger.Message) -> None:
        """Log a warning for normalization failure, once per device ID."""
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
        """Normalize a state message to a DeviceState object.

        Args:
            message: State message containing raw data to normalize.

        Returns:
            Message with refined state data, or None if normalization fails.

        Raises:
            DecodingException: If message type is not state or raw data format is incorrect.
        """
        if message.message_type != messenger.MessageType.STATE:
            raise exceptions.DecodingException(f"Not a state message: {message.message_type}")
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
