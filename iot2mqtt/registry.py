# coding=utf-8
"""Device state and encoder registry.

Central registration point for device models, their state normalizers, and command encoders.
Maintains metadata about registered devices and provides discovery/query methods.

Key entry points: DeviceRegistry.register_state, DeviceRegistry.register_encoder.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

from iot2mqtt import dev, encoder, processor
from iot2mqtt.devices.common_abstract import DeviceState


@dataclass
class DeviceInfo:
    """Metadata for a registered device model.

    Attributes:
        model: The device model identifier.
        device_state_class: State normalizer class for this model.
        protocol: The IoT protocol (Z2M, TASMOTA, etc.), or None if unknown.
        source: Module name where this device is defined (e.g., "iot2mqtt.devices.zigbee2mqtt" or "user").
    """

    model: dev.Model
    device_state_class: Type[DeviceState]
    protocol: Optional[dev.Protocol]
    source: str  # e.g. "iot2mqtt.devices.zigbee2mqtt" or "user"


class DeviceRegistry:
    """Central registry for device state normalizers and command encoders.

    Provides discovery and registration of device models, state classes, and their
    capabilities (settable/gettable fields). Models may be passive (state-only) or
    active (state + commands).
    """

    _devices: Dict[str, DeviceInfo] = {}  # keyed by model tag (str), not dev.Model

    @classmethod
    def register_state(
        cls,
        model_tag: str,
        device_state_class: Type[DeviceState],
        protocol: Optional[dev.Protocol] = None,
    ) -> dev.Model:
        """Register a device model and its state normalizer class.

        Required for all devices (passive or active). Registers the state class with
        StateNormalizerFactory.

        Args:
            model_tag: Unique identifier for the model.
            device_state_class: State normalizer class to handle this model's messages.
            protocol: The IoT protocol (Z2M, TASMOTA, etc.), or None if unknown.

        Returns:
            The Model instance for this tag (also obtainable via dev.ModelFactory.get).
        """
        _model_instance = dev.ModelFactory.get(model_tag)
        processor.StateNormalizerFactory.register(_model_instance, device_state_class)
        cls._devices[model_tag] = DeviceInfo(
            model=_model_instance,
            device_state_class=device_state_class,
            protocol=protocol,
            source=device_state_class.__module__,
        )
        return _model_instance

    @classmethod
    def register_encoder(
        cls,
        model_tag: str,
        settable_fields: List[str],
        gettable_fields: List[str],
        field_aliases: Optional[Dict[str, str]] = None,
        field_converters: Optional[Dict[str, Callable[[Any], Any]]] = None,
    ) -> None:
        """Register command (set/get) capability for an already-registered model.

        Only needed for active devices. Requires register_state() to be called first.

        Args:
            model_tag: Model identifier (must already be registered via register_state).
            settable_fields: Fields that can be set via commands.
            gettable_fields: Fields that can be queried.
            field_aliases: Optional mapping from internal field names to protocol names.
            field_converters: Optional mapping from field names to value conversion functions.

        Raises:
            ValueError: If model_tag is not already registered via register_state.
        """
        if model_tag not in cls._devices.keys():
            raise ValueError(
                f"Call register_state() on '{model_tag}' before register_encoder() - _devices: {cls._devices.keys()}"
            )
        _model_instance = cls._devices[model_tag].model
        encoder.EncoderRegistry(
            models=[_model_instance],
            settable_fields=settable_fields,
            gettable_fields=gettable_fields,
            field_aliases=field_aliases,
            field_converters=field_converters,
        )

    @classmethod
    def is_registered(cls, model_tag: str) -> bool:
        """Check if a model is registered.

        Args:
            model_tag: The model identifier to check.

        Returns:
            True if the model is registered, False otherwise.
        """
        return model_tag in cls._devices

    @classmethod
    def is_active(cls, model_tag: str) -> bool:
        """Check if a model has active (command) capability.

        Args:
            model_tag: The model identifier to check.

        Returns:
            True if the model is registered and has an encoder (settable/gettable capability).
        """
        if not cls.is_registered(model_tag=model_tag):
            return False
        _model = cls._devices[model_tag].model
        return encoder.EncoderRegistry.get_encoder(_model) is not None

    @classmethod
    def get_device_class(cls, model_tag: str) -> Optional[Type[DeviceState]]:
        """Get the DeviceState class for a registered model.

        Args:
            model_tag: The model identifier to look up.

        Returns:
            The DeviceState class for this model, or None if not registered.
        """
        if model_tag not in cls._devices:
            return None
        return cls._devices[model_tag].device_state_class

    @classmethod
    def get_model(cls, model_tag: str) -> Optional[dev.Model]:
        """Get the Model instance for a registered model tag.

        Args:
            model_tag: The model identifier to look up.

        Returns:
            The Model instance for this tag, or None if not registered.
        """
        if model_tag not in cls._devices:
            return None
        return cls._devices[model_tag].model

    @classmethod
    def list_devices(cls) -> Dict[str, DeviceInfo]:
        """Get all registered devices.

        Returns:
            Dictionary mapping model tags to their DeviceInfo.
        """
        return cls._devices

    @classmethod
    def list_models_by_protocol(cls, protocol: dev.Protocol) -> List[str]:
        """Get all registered model tags for a given protocol.

        Args:
            protocol: The IoT protocol to filter by.

        Returns:
            List of model tags with this protocol.
        """
        _model_tags = []
        for _tag, _dev_info in cls._devices.items():
            if _dev_info.protocol == protocol:
                _model_tags.append(_tag)
        return _model_tags
