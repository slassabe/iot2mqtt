#!/usr/local/bin/python3
# coding=utf-8

"""
This module provides utility functions and classes for the iot2mqtt framework.

Classes
-------

- Singleton: A metaclass for creating singleton classes.

Functions
---------

- check_parameter: Validates a parameter against specified type and optionality requirements.

Constants
---------

- i2m_log: Logger instance for the iot2mqtt module.
- DEBUG: Boolean flag indicating whether debugging is enabled.

"""
import logging
from typing import Any, Type, TypeVar

i2m_log = logging.getLogger("iot2mqtt")
DEBUG = True

T = TypeVar("T")


class Singleton(type):
    """ref : Python Cookbook Recipes for Mastering Python 3, (David Beazley, Brian K. Jones)
    Using a Metaclass to Control Instance Creation
    """

    def __init__(cls: Type[T], *args, **kwargs) -> None:
        cls.__instance = None
        super().__init__(*args, **kwargs)

    def __call__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
            return cls.__instance
        return cls.__instance


def check_parameter(
    name: str, value: Any, class_of: type, optional: bool = False
) -> None:
    """
    Check if a parameter meets the specified type and optionality requirements.

    This function validates a parameter by checking if it is of the expected type.
    If the parameter is not optional and is None, or if it is not an instance of the
    specified type, a TypeError is raised.

    Args:
        name (str): The name of the parameter being checked.
        value (Any): The value of the parameter to check.
        class_of (type): The expected type of the parameter.
        optional (bool, optional): Whether the parameter is optional. Defaults to False.

    Raises:
        TypeError: If the parameter is not optional and is None, or if it is not an instance
                   of the specified type.
    """
    if value is None:
        if optional:
            return
        raise TypeError(f"Not optional parameter {name} is None")
    if not isinstance(value, class_of):
        raise TypeError(
            f"{name} must be a {class_of}, got {value} of class {type(value).__name__}"
        )
