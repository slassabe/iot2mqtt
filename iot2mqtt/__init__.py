#!/usr/local/bin/python3
# coding=utf-8
"""
This is the initialization module for the iot2mqtt package.

"""
from iot2mqtt import (abstract, central, dev, messenger, mqtthelper, processor,
                      setup)

from .version import __version__

setup.Models()
