# coding=utf-8

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

from iot2mqtt import abstract, dev, encoder, processor


@dataclass
class DeviceInfo:
    """Metadata about a single registered device model."""

    model: dev.Model
    device_state_class: Type[abstract.DeviceState]
    protocol: Optional[dev.Protocol]
    source: str  # e.g. "iot2mqtt.devices.zigbee2mqtt" or "user"


class DeviceRegistry:
    """Thin, discoverable facade over StateNormalizerFactory + EncoderRegistry."""

    _devices: Dict[str, DeviceInfo] = {}  # keyed by model tag (str), not dev.Model

    @classmethod
    def register_state(
        cls,
        model_tag: str,
        device_state_class: Type[abstract.DeviceState],
        protocol: Optional[dev.Protocol] = None,
    ) -> dev.Model:
        """
        Register (or re-register) the DeviceState class for a model tag.
        Required for EVERY device — passive or active.
        Returns the dev.Model instance (also obtainable via dev.ModelFactory.get(model_tag)).
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
        """
        Add command (set/get) capability to an ALREADY state-registered model.
        Only needed for ACTIVE devices. Raises if register_state() wasn't called first.
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
        """Check if a model tag is registered."""
        return model_tag in cls._devices

    @classmethod
    def is_active(cls, model_tag: str) -> bool:
        """True if the model has encoder (settable/gettable) capability."""
        if not cls.is_registered(model_tag=model_tag):
            return False
        _model = cls._devices[model_tag].model
        return encoder.EncoderRegistry.get_encoder(_model) is not None

    @classmethod
    def get_device_class(cls, model_tag: str) -> Optional[Type[abstract.DeviceState]]:
        """Get the DeviceState class for a registered model tag."""
        if model_tag not in cls._devices:
            return None
        return cls._devices[model_tag].device_state_class

    @classmethod
    def get_model(cls, model_tag: str) -> Optional[dev.Model]:
        """Get the Model instance for a registered model tag."""
        if model_tag not in cls._devices:
            return None
        return cls._devices[model_tag].model

    @classmethod
    def list_devices(cls) -> Dict[str, DeviceInfo]:
        """Return all registered devices."""
        return cls._devices

    @classmethod
    def list_models_by_protocol(cls, protocol: dev.Protocol) -> List[str]:
        """List all model tags with the given protocol."""
        _model_tags = []
        for _tag, _dev_info in cls._devices.items():
            if _dev_info.protocol == protocol:
                _model_tags.append(_tag)
        return _model_tags
