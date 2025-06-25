#!/usr/local/bin/python3
# coding=utf-8

"""
This module provides helper classes and functions for managing MQTT client operations 
using the paho.mqtt.client library. It includes context and security configurations, 
as well as client management for connecting, disconnecting, and handling MQTT events.

"""
import dataclasses
import socket
import time
from typing import Any, Callable, List, Optional

import certifi
import paho.mqtt.client as mqtt

from iot2mqtt import exceptions, utils


@dataclasses.dataclass
class MQTTContext:
    """
    MQTTContext holds the configuration for the MQTT client.

    Attributes:
        hostname (str): The hostname of the MQTT broker. Defaults to "127.0.0.1".
        client_id (str): The client ID to use for the MQTT connection. Defaults to an empty string.
        port (int): The port number to connect to the MQTT broker. Defaults to 1883.
        keepalive (int): The keepalive interval in seconds for the MQTT connection. Defaults to 60.
        clean_start (bool): Indicates whether to start with a clean session. Defaults to False.
        connected (bool): Indicates whether the client is currently connected. Initialized to False.
        started (bool): Indicates whether the client has started. Initialized to False.
        loop_forever_used (bool): Indicates whether the loop_forever method has been used.
            Initialized to False.

    Methods:
        __post_init__: Validates the parameters after initialization.
    """

    hostname: str = "127.0.0.1"
    client_id: str = ""
    port: int = 1883
    keepalive: int = 60
    clean_start: bool = False

    def __post_init__(self) -> None:
        utils.check_parameter("client_id", self.client_id, str)
        utils.check_parameter("hostname", self.hostname, str)
        utils.check_parameter("port", self.port, int)
        utils.check_parameter("keepalive", self.keepalive, int)
        utils.check_parameter("clean_start", self.clean_start, bool)

        self.connected = False
        self.started = False
        self.loop_forever_used = False


@dataclasses.dataclass
class SecurityContext:
    """
    SecurityContext holds the security-related configuration for the MQTT client.

    Attributes:
        tls (bool): Indicates whether TLS should be used for the connection. Defaults to False.
        user_name (Optional[str]): The username for MQTT authentication. Defaults to None.
        user_pwd (Optional[str]): The password for MQTT authentication. Defaults to None.

    """

    tls: bool = False
    user_name: Optional[str] = None
    user_pwd: Optional[str] = None

    def __post_init__(self) -> None:
        utils.check_parameter("tls", self.tls, bool)
        # utils.check_parameter("user_name", self.user_name, str, optional=True)
        # utils.check_parameter("user_pwd", self.user_pwd, str, optional=True)


class ConnectionRetryPolicy:
    """
    ConnectionRetryPolicy defines the retry policy for connecting to the MQTT broker.

    Attributes:
        MAX_RETRY (int): The maximum number of retry attempts for connecting to the broker.
        RETRY_DELAY (int): The delay in seconds between retry attempts.
    """

    MAX_RETRY = 5
    RETRY_DELAY = 5  # seconds


class ClientHelper(mqtt.Client):
    """
    ClientHelper is a helper class for managing MQTT client operations.

    This class extends the paho.mqtt.client.Client class and provides additional functionality
    for handling MQTT connections, disconnections, and event callbacks.

    This constructor sets up the MQTT client with the provided context and security settings.
    It also initializes the connection and disconnection handlers.

    Parameters:
        context (MQTTContext): The context containing MQTT connection parameters such as
            hostname, port
        security_ctxt (SecurityContext): The security context containing TLS and authentication
            settings.
    """

    def __init__(self, context: MQTTContext, security_ctxt: SecurityContext) -> None:
        super().__init__(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=context.client_id,
            userdata=None,
            protocol=mqtt.MQTTv5,
            transport="tcp",
        )
        if security_ctxt.tls:
            # enable TLS for secure connection
            self.tls_set(certifi.where())
        self.username_pw_set(security_ctxt.user_name, security_ctxt.user_pwd)

        self._context = context
        self.on_connect_handlers: List[Callable[..., None]] = []
        self.on_disconnect_handlers: List[Callable[..., None]] = []
        self.on_connect = self._handle_on_connect
        self.on_disconnect = self._handle_on_disconnect

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} "{self._context.hostname}:{self._context.port}">'

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} obj.  "
            f'"{self._client_id}" | '
            f'"{self._context.hostname}:{self._context.port}">'
        )

    def loop_forever(self, *argv, **kwargs) -> mqtt.MQTTErrorCode:
        """Start a new thread to run the network loop."""
        self._context.loop_forever_used = True
        return super().loop_forever(*argv, **kwargs)

    def start(self) -> mqtt.MQTTErrorCode:
        """
        Starts the client MQTT network loop.

        Connects the client if not already connected, and starts the network loop.

        Returns:
            mqtt.MQTTErrorCode: The result of calling client.loop_start().

        Raises:
            RuntimeError: If loop_start fails or connection is refused.
        """
        if self._context.started:
            utils.i2m_log.warning("[%s] already started", self)
            return mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS
        try:
            _rc = self._do_connect()
            if self.loop_start() != mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS:
                utils.i2m_log.error(
                    "[%s] loop_start failed : %s",
                    self,
                    mqtt.error_string(mqtt.MQTTErrorCode),
                )
                raise RuntimeError("loop_start failed")
            self._context.started = True
            return _rc
        except ConnectionRefusedError as exp:
            utils.i2m_log.fatal(
                "[%s] cannot connect host %s", exp, self._context.hostname
            )
            raise exceptions.ConnectionException("[%s] connection refused") from exp

    def stop(self) -> mqtt.MQTTErrorCode:
        """
        Stops the client MQTT connection.

        Stops the async loop if it was not already running and calls disconnect()
        to close the client connection.

        Returns:
            mqtt.MQTTErrorCode: The result of calling disconnect().

        Raises:
            RuntimeError: If loop_stop fails.
        """
        if not self._context.connected:
            utils.i2m_log.warning("[%s] Unable to stop disconnected client", self)
            return mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS
        _rc = self.disconnect()
        if not self._context.loop_forever_used:
            _rc = self.loop_stop()
            if _rc != mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS:
                utils.i2m_log.error(
                    'loop_stop failed - [%s] "%s"',
                    mqtt.MQTTErrorCode,
                    mqtt.error_string(mqtt.MQTTErrorCode),
                )
                raise RuntimeError("Unable to stop loop")
            self._context.started = False
        return _rc

    def _do_connect(self) -> mqtt.MQTTErrorCode:
        """
        Connects the client to the MQTT broker according to the Connection policy.

        This method attempts to connect to the MQTT broker using the connection parameters
        specified in the context. If the connection fails due to a temporary DNS resolution
        issue, it retries the connection according to the retry policy defined in
        ConnectionRetryPolicy.

        Returns:
            mqtt.MQTTErrorCode: The result code of the connection attempt.

        Raises:
            exceptions.ConnectionException: If all retry attempts fail.
        """

        for attempt in range(ConnectionRetryPolicy.MAX_RETRY):
            try:
                _rc = self.connect(
                    self._context.hostname,
                    port=self._context.port,
                    keepalive=self._context.keepalive,
                    clean_start=self._context.clean_start,
                    properties=None,
                )
                return _rc
            except socket.gaierror as exp:
                utils.i2m_log.fatal(
                    "[%s] cannot connect host %s (attempt %d/%d)",
                    exp,
                    self._context.hostname,
                    attempt + 1,
                    ConnectionRetryPolicy.MAX_RETRY,
                )
                if attempt < ConnectionRetryPolicy.MAX_RETRY - 1:
                    time.sleep(ConnectionRetryPolicy.RETRY_DELAY)
                else:
                    raise exceptions.ConnectionException("Connection failed") from None

    def _handle_on_connect(  # pylint: disable=too-many-arguments
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties,
    ) -> None:
        """Define the default connect callback implementation."""
        if reason_code == 0:
            self._context.connected = True
        for on_connect_handler in self.on_connect_handlers:
            on_connect_handler(client, userdata, flags, reason_code, properties)

    def connect_handler_add(self, handler: Callable) -> None:
        """
        Adds a handler to be called when the client successfully connects to the MQTT broker.

        This method allows you to register a callback function that will be invoked whenever
        the client establishes a connection to the MQTT broker.
        """
        self.on_connect_handlers.append(handler)

    def disconnect(self, *argc, **argv) -> mqtt.MQTTErrorCode:
        """
        Disconnects the client from the MQTT broker.

        This method overrides the default disconnect method to add logging functionality.
        It logs the result of the disconnection request and then returns the result code.

        Parameters:
            *argc: Variable length argument list passed to the superclass disconnect method.
            **argv: Arbitrary keyword arguments passed to the superclass disconnect method.

        Returns:
            mqtt.MQTTErrorCode: The result code of the disconnection request.
        """
        _rc = super().disconnect(*argc, **argv)
        utils.i2m_log.debug("[%s] Disconnection request returns : %s", self, _rc)
        return _rc

    def _handle_on_disconnect(  # pylint: disable=too-many-arguments
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties,
    ) -> None:
        """Define the default disconnect callback implementation."""
        self._context.connected = False
        for on_disconnect_handler in self.on_disconnect_handlers:
            on_disconnect_handler(
                client, userdata, disconnect_flags, reason_code, properties
            )

    def disconnect_handler_add(self, handler: Callable) -> None:
        """
        Adds a handler to be called when the client disconnects from the MQTT broker.

        This method allows you to register a callback function that will be invoked whenever
        the client disconnects from the MQTT broker.

        Returns:
            None
        """
        self.on_disconnect_handlers.append(handler)


class MQTTClientDeprecated(ClientHelper):
    """
    This class provides additional helper methods for MQTT operations.
    Could evolve to a more generic class in the future.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_message = self._handle_on_message_helper
        self.on_subscribe = self._handle_on_subscribe_helper

        self._default_message_callbacks: List[Callable] = []
        self.on_subscribe_handlers: List[Callable] = []

    def _handle_on_message_helper(
        self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
    ) -> None:
        """
        Define the message received callback implementation.

        Args:
            client (mqtt.Client): The client instance for this callback.
            userdata (Any): The private user data as set in Client() or userdata_set().
            message (mqtt.MQTTMessage): The received message with members: topic, payload, qos, retain.

        """
        for on_message_handler in self._default_message_callbacks:
            on_message_handler(client, userdata, message)

    def default_message_callback_add(self, callback: Callable) -> None:
        """
        Adds a callback function to the list of default message callbacks.

        Args:
            callback (Callable): The callback function to be added.

        Returns:
            None
        """
        self._default_message_callbacks.append(callback)

    def publish_and_wait(
        self, topic: str, payload: str, timeout: float, **kwargs
    ) -> mqtt.MQTTMessageInfo:
        """
        Publish a message on a topic and wait for it to be published.

        Args:
            topic (str): The topic on which to publish the message.
            payload (str): The message payload.
            timeout (float): The maximum time to wait for the message to be published.
            **kwargs: Additional keyword arguments to pass to the publish method.

        Returns:
            mqtt.MQTTMessageInfo: Information about the published message.

        Raises:
            ValueError: If any of the parameters are of incorrect type.
        """

        def timed_out() -> bool:
            return False if timeout_time is None else time.time() > timeout_time

        utils.check_parameter("topic", topic, str)
        utils.check_parameter("payload", payload, str)
        utils.check_parameter("timeout", timeout, (float, int))

        timeout_time = None if timeout is None else time.time() + timeout
        timeout_tenth = None if timeout is None else timeout / 10.0

        utils.i2m_log.warning(
            "Outgoing message on %s(%s) : %s", topic, type(payload), payload
        )
        _mi = self.publish(topic, payload, **kwargs)
        if timeout is not None and not timed_out():
            while not _mi.is_published():
                utils.i2m_log.debug("Message is not yet published.")
                time.sleep(timeout_tenth)
        return _mi

    def _handle_on_subscribe_helper(  # pylint: disable=too-many-arguments
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code_list: List[mqtt.ReasonCode],
        properties: mqtt.Properties,
    ) -> None:
        """Define the default subscribtion callback implementation."""
        for reason_code in reason_code_list:
            if reason_code.is_failure:
                utils.i2m_log.warning(
                    "[%s] subscribe refused - reason code : %s", self, reason_code
                )
                return
        utils.i2m_log.debug("[%s] subscribe accepted", client)
        for on_subscribe_handler in self.on_subscribe_handlers:
            on_subscribe_handler(client, userdata, mid, reason_code_list, properties)

    def subscribe_handler_add(self, handler: Callable):
        """
        Adds a subscribe handler.

        Subscribe handlers are called when a subscription is received from the MQTT broker.

        Args:
            handler (Callable): The callback function to handle the subscribe event.

        Returns:
            None
        """
        self.on_subscribe_handlers.append(handler)
