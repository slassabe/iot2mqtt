#!/usr/local/bin/python3
# coding=utf-8
"""
Encoder Module

This module provides functionality for encoding and validating device states, managing timers, 
and handling power state changes for various device models.

"""

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

from iot2mqtt import abstract, dev, utils


class Encoder(BaseModel):
    """
    Encoder class for transforming and validating device states.
    """

    settable_fields: List[str] = Field(frozen=True)
    gettable_fields: List[str] = Field(frozen=True)
    field_aliases: Optional[Dict[str, str]] = Field(default=None, frozen=True)
    field_converters: Optional[Dict[str, Callable[[Any], Any]]] = Field(
        default=None, frozen=True
    )

    def __repr__(self):
        return (
            f"Encoder(fields='{self.settable_fields}'"
            f", aliases='{self.field_aliases}'"
            f", converter={self.field_converters})"
        )

    def transform(self, state: abstract.DeviceState) -> Dict:
        """
        Transforms the given device state into an encoded dictionary.

        Args:
            state (abstract.DeviceState): The current state of the device to be encoded.

        Returns:
            Dict: The encoded state of the device as a dictionary.
        """
        _encoded_state = {}
        for key, value in state.model_dump(exclude_none=True).items():
            _alias = self.field_aliases.get(key) if self.field_aliases else None
            _converter = (
                self.field_converters.get(key) if self.field_converters else None
            )

            if _converter is None:
                transformed_value = value
            else:
                transformed_value = _converter(value)
            if _alias is None:
                _encoded_state[key] = transformed_value
            else:
                _encoded_state[_alias] = transformed_value
        return _encoded_state

    def check_compliance(self, state_dump: Dict) -> bool:
        """
        Checks if the given state dictionary complies with the expected fields.

        Args:
            state_dump (Dict): The state dictionary to be checked for compliance.

        Returns:
            bool: True if the state dictionary complies with the encoder's expected fields,
            False otherwise.
        """
        _compliant = True
        for key, value in state_dump.items():
            if key not in self.settable_fields:
                utils.i2m_log.warning('Cannot encode field "%s"', key)
                _compliant = False
        return _compliant


class EncoderRegistry:
    """
    A registry for managing encoders for different device models.

    This class allows for the creation and retrieval of encoders that are responsible for
    transforming and validating device states for various device models. Encoders are stored
    in a registry and can be accessed using the device model as the key.

    Attributes:
        _registry (Dict[dev.Model, Encoder]): A dictionary that maps device models to their
            corresponding encoders.

    Args:
        models (dev.Model): The device models for which the encoder is being created.
        settable_fields (List[str]): List of fields that can be set for the device model.
        gettable_fields (List[str]): List of fields that can be retrieved for the device model.
        field_aliases (Optional[Dict[str, str]], optional): Optional dictionary of field
            aliases. Defaults to None.
        field_converters (Optional[Dict[str, Callable[[Any], Any]]], optional): Optional
            dictionary of field converters. Defaults to None.

    Raises:
        ValidationError: If there is an error creating the encoder for the given models.
    """

    _registry: Dict[dev.Model, Encoder] = {}

    def __init__(
        self,
        models: dev.Model,
        settable_fields: List[str],
        gettable_fields: List[str],
        field_aliases: Optional[Dict[str, str]] = None,
        field_converters: Optional[Dict[str, Callable[[Any], Any]]] = None,
    ) -> None:
        try:
            _encoder = Encoder(
                settable_fields=settable_fields,
                gettable_fields=gettable_fields,
                field_aliases=field_aliases,
                field_converters=field_converters,
            )
        except ValidationError as exc:
            utils.i2m_log.error(
                "Error creating encoder for models %s : %s", models, exc
            )
            return
        for _model in models:
            self._registry[_model] = _encoder

    @staticmethod
    def get_encoder(model: dev.Model) -> Optional[Encoder]:
        """
        Retrieves the encoder for the given device model.

        Args:
            model (dev.Model): The device model for which the encoder is being retrieved.

        Returns:
            Optional[Encoder]: The encoder for the given device model, or  None if no encoder
            is found.
        """
        return EncoderRegistry._registry.get(model)


EncoderRegistry(
    models=[dev.Model.SN_MINI, dev.Model.SN_MINI_L2, dev.Model.SN_SMART_PLUG],
    settable_fields=["state"],
    gettable_fields=["state"],
    field_aliases={"power": "state"},
)
EncoderRegistry(
    models=[dev.Model.SHELLY_PLUGS],
    settable_fields=["Power"],
    gettable_fields=["Power"],
    field_aliases={"power": "Power"},
)

EncoderRegistry(
    models=[dev.Model.SHELLY_UNI],
    settable_fields=["Power1", "Power2"],
    gettable_fields=["Power1", "Power2"],
    field_aliases={"power1": "Power1", "power2": "Power2"},
)

EncoderRegistry(
    models=[dev.Model.NEO_ALARM],
    settable_fields=["alarm", "duration", "melody", "volume"],
    gettable_fields=[],
)

EncoderRegistry(
    models=[dev.Model.SRTS_A01],
    settable_fields=[
        "child_lock",
        "external_temperature_input",
        "occupied_heating_setpoint",
        "preset",
        "schedule_settings",
        "schedule",
        "schedule_settings",
        "sensor",
        "system_mode",
        "valve_detection",
        "window_detection",
    ],
    gettable_fields=[
        "child_lock",  # Just one field request get all fields
    ],
)


def encode(model: dev.Model, state: abstract.DeviceState) -> Dict[str, Any]:
    """
    Encode the state of a device model into a dictionary format using the appropriate encoder.

    Args:
        model (dev.Model): The device model for which the state needs to be encoded.
        state (abstract.DeviceState): The current state of the device to be encoded.

    Returns:
        Dict[str, Any]: The encoded state of the device as a dictionary. If no encoder is found,
        the state is returned as a dictionary without transformation.

    """
    utils.check_parameter("model", model, dev.Model)
    utils.check_parameter("state", state, abstract.DeviceState)
    _encoder = EncoderRegistry.get_encoder(model=model)
    if _encoder is None:
        utils.i2m_log.warning(
            "No encoder found for model: %s with state: %s", model, state
        )
        return state.model_dump()
    return _encoder.transform(state)


def check_compliance(model: dev.Model, state: Dict) -> bool:
    """
    Check if the given state complies with the encoder for the specified model.

    Args:
        model (dev.Model): The device model for which compliance needs to be
            checked.
        state (Dict): The state of the device to be checked for compliance.

    Returns:
        bool: True if the state complies with the encoder, False otherwise.

    """
    utils.check_parameter("model", model, dev.Model)
    utils.check_parameter("state", state, Dict)
    _encoder = EncoderRegistry.get_encoder(model=model)
    if _encoder is None:
        utils.i2m_log.warning("No encoder found for model: %s", model)
        return False
    return _encoder.check_compliance(state)
