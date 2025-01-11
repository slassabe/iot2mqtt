#!/usr/local/bin/python3
# coding=utf-8

"""
This module provides various classes and functions for managing MQTT topics and configurations
used in the `scrutinizer` module.

It includes classes for managing topic configurations based on protocol and message type,
as well as functions for retrieving topic configurations and generating MQTT topics.
"""

from typing import List

from pydantic import BaseModel

from iot2mqtt import dev, messenger, utils

Z2M_INFO_BASE_TOPIC = "zigbee2mqtt"
Z2M_CMND_BASE_TOPIC = "zigbee2mqtt"

TASMOTA_INFO_BASE_TOPIC = "stat"
TASMOTA_AVAIL_BASE_TOPIC = "tele"
TASMOTA_CMND_BASE_TOPIC = "cmnd"
TASMOTA_DISCOVERY_TOPIC = "tasmota/discovery"

ESPSOMFY_AVAIL_BASE_TOPIC = "ESPSomfy"
ESPSOMFY_INFO_BASE_TOPIC = "ESPSomfy/shades"
ESPSOMFY_CMND_BASE_TOPIC = "ESPSomfy/shades"
ESPSOMFY_DISCOVERY_TOPIC = "homeassistant/cover"


class TopicManager(metaclass=utils.Singleton):
    """
    A registry for managing topic configurations based on protocol and message type.

    This class provides a centralized way to store and retrieve topic configurations
    for different combinations of protocol and message type. It acts as a registry
    for topic configurations, allowing easy access to the topic base, topic extension,
    and device name offset for a given protocol and message type.
    """

    def __init__(self) -> None:
        self._topic_registry = {}


class CommandTopicManager(TopicManager):
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
        _prefix = ""
        self.register(
            protocol=dev.Protocol.Z2M, command_topic_base=_prefix + Z2M_CMND_BASE_TOPIC
        )
        self.register(
            protocol=dev.Protocol.TASMOTA,
            command_topic_base=_prefix + TASMOTA_CMND_BASE_TOPIC,
        )
        self.register(
            protocol=dev.Protocol.ESPSOMFY,
            command_topic_base=_prefix + ESPSOMFY_CMND_BASE_TOPIC,
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


class InfoTopicManager(TopicManager):
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
            info_topic_base=TASMOTA_AVAIL_BASE_TOPIC,
            info_topic_extension="/+/LWT",
        )
        self.register(
            protocol=dev.Protocol.ESPSOMFY,
            message_type=messenger.MessageType.AVAIL,
            info_topic_base=ESPSOMFY_AVAIL_BASE_TOPIC,
            info_topic_extension="/status",
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
            # info_topic_extension="/+/+",
            info_topic_extension="/+/RESULT",
        )
        self.register(
            protocol=dev.Protocol.ESPSOMFY,
            message_type=messenger.MessageType.STATE,
            info_topic_base=ESPSOMFY_INFO_BASE_TOPIC,
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
        self.register(
            protocol=dev.Protocol.ESPSOMFY,
            message_type=messenger.MessageType.DISCO,
            info_topic_base=ESPSOMFY_DISCOVERY_TOPIC,
            info_topic_extension="/+/config",
        )
