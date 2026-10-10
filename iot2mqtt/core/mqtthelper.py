#!/usr/local/bin/python3
# coding=utf-8

"""
MQTT client helpers using paho.mqtt.client library.

Provides context and security configuration classes, connection retry policies,
and a ClientHelper class that extends paho's MQTT client with connection management
and event handler registration.
"""

import dataclasses
import socket
import time
from typing import Any, Callable, List, Optional

import certifi
import paho.mqtt.client as mqtt

from iot2mqtt.core import exceptions, utils


@dataclasses.dataclass
class MQTTContext:
    """Configuration for MQTT client connection parameters and state.

    Connection state fields (connected, started, loop_forever_used) are initialized
    in __post_init__ and track the client's runtime state.
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
    """Security configuration for MQTT client including TLS and authentication."""

    tls: bool = False
    user_name: Optional[str] = None
    user_pwd: Optional[str] = None

    def __post_init__(self) -> None:
        utils.check_parameter("tls", self.tls, bool)
        # utils.check_parameter("user_name", self.user_name, str, optional=True)
        # utils.check_parameter("user_pwd", self.user_pwd, str, optional=True)


class ConnectionRetryPolicy:
    """Connection retry policy with maximum attempts and delay between retries."""

    MAX_RETRY = 5
    RETRY_DELAY = 5  # seconds


class ClientHelper(mqtt.Client):
    """MQTT client helper extending paho.mqtt.client.Client with connection management.

    Sets up the MQTT client with connection and disconnection handlers that can be
    registered via connect_handler_add() and disconnect_handler_add().
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

    def loop_forever(self, *argv, **kwargs) -> int:
        """Start a new thread to run the network loop."""
        self._context.loop_forever_used = True
        return super().loop_forever(*argv, **kwargs)

    def start(self) -> int:
        """Start the MQTT client network loop and connect to the broker.

        Returns:
            Result code from loop_start() or connection attempt.

        Raises:
            RuntimeError: If loop_start fails.
            ConnectionException: If connection is refused or times out.
        """
        if self._context.started:
            utils.i2m_log.warning("[%s] already started", self)
            return mqtt.MQTT_ERR_SUCCESS
        try:
            _rc = self._do_connect()
            if self.loop_start() != mqtt.MQTT_ERR_SUCCESS:
                utils.i2m_log.error(
                    "[%s] loop_start failed : %s",
                    self,
                    mqtt.error_string(mqtt.MQTT_ERR_SUCCESS),
                )
                raise RuntimeError("loop_start failed")
            self._context.started = True
            return _rc
        except (ConnectionRefusedError, socket.timeout) as exp:
            utils.i2m_log.fatal("[%s] cannot connect host %s", exp, self._context.hostname)
            raise exceptions.ConnectionException("[%s] connection refused") from exp

    def stop(self) -> int:
        """Stop the MQTT client connection and network loop if needed.

        Returns:
            Result code from disconnect() or loop_stop().

        Raises:
            RuntimeError: If loop_stop fails.
        """
        if not self._context.connected:
            utils.i2m_log.warning("[%s] Unable to stop disconnected client", self)
            return mqtt.MQTT_ERR_SUCCESS
        _rc = self.disconnect()
        if not self._context.loop_forever_used:
            _rc = self.loop_stop()
            if _rc != mqtt.MQTT_ERR_SUCCESS:
                utils.i2m_log.error(
                    'loop_stop failed - [%s] "%s"',
                    _rc,
                    mqtt.error_string(_rc),
                )
                raise RuntimeError("Unable to stop loop")
            self._context.started = False
        return _rc

    def _do_connect(self) -> int:
        """Connect to the MQTT broker with retry logic for DNS resolution failures.

        Attempts up to MAX_RETRY connections, retrying after RETRY_DELAY seconds
        if socket.gaierror or socket.timeout is encountered.

        Returns:
            Connection result code.

        Raises:
            ConnectionException: If all retry attempts fail.
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
            except (socket.gaierror, socket.timeout) as exp:
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
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        """Default connect callback: update connection state and invoke registered handlers."""
        if reason_code == 0:
            self._context.connected = True
        for on_connect_handler in self.on_connect_handlers:
            on_connect_handler(client, userdata, flags, reason_code, properties)

    def connect_handler_add(self, handler: Callable) -> None:
        """Register a callback to invoke when client successfully connects to broker."""
        self.on_connect_handlers.append(handler)

    def disconnect(self, *argc, **argv) -> int:
        """Disconnect from broker and log the result.

        Overrides parent disconnect() to add logging. Arguments are passed through
        to the parent class method.

        Returns:
            Disconnection result code.
        """
        _rc = super().disconnect(*argc, **argv)
        utils.i2m_log.debug("[%s] Disconnection request returns : %s", self, _rc)
        return _rc

    def _handle_on_disconnect(  # pylint: disable=too-many-arguments
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        """Default disconnect callback: update connection state and invoke registered handlers."""
        self._context.connected = False
        for on_disconnect_handler in self.on_disconnect_handlers:
            on_disconnect_handler(client, userdata, disconnect_flags, reason_code, properties)

    def disconnect_handler_add(self, handler: Callable) -> None:
        """Register a callback to invoke when client disconnects from broker."""
        self.on_disconnect_handlers.append(handler)


class MQTTClientDeprecated(ClientHelper):
    """Extended MQTT client with message and subscribe event handling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_message = self._handle_on_message_helper
        self.on_subscribe = self._handle_on_subscribe_helper

        self._default_message_callbacks: List[Callable] = []
        self.on_subscribe_handlers: List[Callable] = []

    def _handle_on_message_helper(
        self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
    ) -> None:
        """Invoke all registered message handlers for received message."""
        for on_message_handler in self._default_message_callbacks:
            on_message_handler(client, userdata, message)

    def default_message_callback_add(self, callback: Callable) -> None:
        """Register a callback to invoke when message is received."""
        self._default_message_callbacks.append(callback)

    def publish_and_wait(
        self, topic: str, payload: str, timeout: float, **kwargs
    ) -> mqtt.MQTTMessageInfo:
        """Publish a message and wait for confirmation up to timeout seconds.

        Args:
            topic: Topic to publish to.
            payload: Message payload.
            timeout: Maximum seconds to wait for publication confirmation.
            **kwargs: Additional arguments passed to publish().

        Returns:
            Message info object with publication status.

        Raises:
            ValueError: If parameters are of incorrect type.
        """

        def timed_out() -> bool:
            return False if timeout_time is None else time.time() > timeout_time

        utils.check_parameter("topic", topic, str)
        utils.check_parameter("payload", payload, str)
        utils.check_parameter("timeout", timeout, (float, int))

        timeout_time = None if timeout is None else time.time() + timeout
        timeout_tenth = None if timeout is None else timeout / 10.0

        utils.i2m_log.warning("Outgoing message on %s(%s) : %s", topic, type(payload), payload)
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
        reason_code_list: List[Any],
        properties: Any,
    ) -> None:
        """Default subscribe callback: log status and invoke registered handlers."""
        for reason_code in reason_code_list:
            if hasattr(reason_code, "is_failure") and reason_code.is_failure:
                utils.i2m_log.warning(
                    "[%s] subscribe refused - reason code : %s", self, reason_code
                )
                return
        utils.i2m_log.debug("[%s] subscribe accepted", client)
        for on_subscribe_handler in self.on_subscribe_handlers:
            on_subscribe_handler(client, userdata, mid, reason_code_list, properties)

    def subscribe_handler_add(self, handler: Callable):
        """Register a callback to invoke when subscription is acknowledged by broker."""
        self.on_subscribe_handlers.append(handler)
