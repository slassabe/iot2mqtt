# coding=utf-8
"""
Device state encoding and encoder registry management.

Provides Encoder class for transforming and validating device states with field
aliasing and conversion support, plus EncoderRegistry for managing encoders across
device models.
"""

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

from iot2mqtt import dev
from iot2mqtt.core import utils
from iot2mqtt.devices.common_abstract import DeviceState


class Encoder(BaseModel):
    """Encode and validate device states with field aliasing and conversion.
    
    Transforms device state objects to dictionaries using optional field aliases
    and converter functions for customization.
    """

    settable_fields: List[str] = Field(frozen=True)
    gettable_fields: List[str] = Field(frozen=True)
    field_aliases: Optional[Dict[str, str]] = Field(default=None, frozen=True)
    field_converters: Optional[Dict[str, Callable[[Any], Any]]] = Field(default=None, frozen=True)

    def __repr__(self):
        return (
            f"Encoder(fields='{self.settable_fields}'"
            f", aliases='{self.field_aliases}'"
            f", converter={self.field_converters})"
        )

    def transform(self, state: DeviceState) -> Dict:
        """Transform device state to dictionary with aliases and converters applied.

        Args:
            state: Device state to encode.

        Returns:
            Encoded state as dictionary with aliases and converted values.
        """
        _encoded_state = {}
        for key, value in state.model_dump(exclude_none=True).items():
            _alias = self.field_aliases.get(key) if self.field_aliases else None
            _converter = self.field_converters.get(key) if self.field_converters else None
            if _converter is None:
                transformed_value = value
            else:
                transformed_value = _converter(value)
            if _alias is None:
                _encoded_state[key] = transformed_value
            else:
                _encoded_state[_alias] = transformed_value
        return _encoded_state


class EncoderRegistry:
    """Registry mapping device models to their corresponding encoders.
    
    Manages encoder creation and retrieval for device models with support for
    field aliasing and conversion. Thread-safe for concurrent access.
    """

    _registry: Dict[dev.Model, Encoder] = {}

    @classmethod
    def reset(cls) -> None:
        """Clear all registered encoders (for testing/runtime reset)."""
        cls._registry.clear()

    def __init__(
        self,
        models: dev.Model,
        settable_fields: List[str],
        gettable_fields: List[str],
        field_aliases: Optional[Dict[str, str]] = None,
        field_converters: Optional[Dict[str, Callable[[Any], Any]]] = None,
    ) -> None:
        """Register an encoder for one or more device models.

        Args:
            models: Device model(s) to register encoder for.
            settable_fields: Fields that can be set on the device.
            gettable_fields: Fields that can be retrieved from the device.
            field_aliases: Optional mapping of field names to aliases.
            field_converters: Optional mapping of field names to conversion functions.

        Logs error if encoder creation fails due to validation error.
        """
        try:
            _encoder = Encoder(
                settable_fields=settable_fields,
                gettable_fields=gettable_fields,
                field_aliases=field_aliases,
                field_converters=field_converters,
            )
        except ValidationError as exc:
            utils.i2m_log.error("Error creating encoder for models %s : %s", models, exc)
            return
        for _model in models:
            self._registry[_model] = _encoder

    @staticmethod
    def get_encoder(model: dev.Model) -> Optional[Encoder]:
        """Retrieve encoder for a device model.

        Args:
            model: Device model to get encoder for.

        Returns:
            Encoder instance if found, None otherwise.
        """
        return EncoderRegistry._registry.get(model)


def encode(model: dev.Model, state: DeviceState) -> Dict[str, Any]:
    """Encode device state using the appropriate encoder.

    Retrieves the encoder for the model and transforms the state. If no encoder is found,
    returns the state as-is via model_dump().

    Args:
        model: Device model.
        state: Device state to encode.

    Returns:
        Encoded state as dictionary. Returns untransformed state if no encoder found.
    """
    utils.check_parameter("model", model, dev.Model)
    utils.check_parameter("state", state, DeviceState)

    _encoder = EncoderRegistry.get_encoder(model=model)
    if _encoder is None:
        utils.i2m_log.warning("No encoder found for model: %s with state: %s", model, state)
        return state.model_dump()
    return _encoder.transform(state)
