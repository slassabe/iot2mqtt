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
from paho.mqtt.enums import MQTTErrorCode

from iot2mqtt.core import exceptions, utils

OnConnectHandler = Callable[[mqtt.Client, Any, Any, Any, Any], None]

@dataclasses.dataclass
class MQTTContext:
    """Configuration and state for MQTT client connection.

    Attributes:
        hostname: Hostname or IP address of MQTT broker (default: 127.0.0.1).
        client_id: MQTT client identifier (default: ""; broker will assign if empty).
        port: MQTT broker port (default: 1883; use 8883 for TLS).
        keepalive: Keep-alive interval in seconds (default: 60).
        clean_start: Start with clean session flag (default: False).

    State fields (initialized in __post_init__):
        connected: True if currently connected to broker; False otherwise.
        started: True if network loop has been started; False otherwise.
        loop_forever_used: True if loop_forever() was called; False if loop_start() was used.

    Note:
        State fields are mutable and updated by ClientHelper during connection lifecycle.
        Should not be modified directly after ClientHelper initialization.
    """
    hostname: str = "127.0.0.1"
    client_id: str = ""
    port: int = 1883
    keepalive: int = 60
    clean_start: bool = False
    
    # State fields with proper field declaration
    connected: bool = dataclasses.field(default=False, init=False, repr=False)
    started: bool = dataclasses.field(default=False, init=False, repr=False)
    loop_forever_used: bool = dataclasses.field(default=False, init=False, repr=False)
    
    def __post_init__(self) -> None:
        # Validation only
        utils.check_parameter("client_id", self.client_id, str)
        utils.check_parameter("hostname", self.hostname, str)
        utils.check_parameter("port", self.port, int)
        utils.check_parameter("keepalive", self.keepalive, int)
        utils.check_parameter("clean_start", self.clean_start, bool)



@dataclasses.dataclass
class SecurityContext:
    """Security configuration for MQTT client including TLS and authentication."""

    tls: bool = False
    user_name: Optional[str] = None
    user_pwd: Optional[str] = None

    def __post_init__(self) -> None:
        utils.check_parameter("tls", self.tls, bool)
        utils.check_parameter("user_name", self.user_name, str, optional=True)
        utils.check_parameter("user_pwd", self.user_pwd, str, optional=True)


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
        self.on_connect_handlers: List[OnConnectHandler] = []
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

    def loop_forever(self, *args, **kwargs) -> MQTTErrorCode:
        """Start a new thread to run the network loop."""
        self._context.loop_forever_used = True
        return super().loop_forever(*args, **kwargs)

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
            _connection_result = self._do_connect()
            loop_start_result = self.loop_start()
            if loop_start_result != mqtt.MQTT_ERR_SUCCESS:
                utils.i2m_log.error(
                    "[%s] loop_start failed : %s",
                    self,
                    mqtt.error_string(loop_start_result),  # Correct: logs actual error
                )
                raise RuntimeError("loop_start failed")
            self._context.started = True
            return _connection_result
        except (ConnectionRefusedError, socket.timeout) as connection_error:
            utils.i2m_log.fatal(
                "[%s] cannot connect to %s:%d (%s)",
                self,
                self._context.hostname,
                self._context.port,
                connection_error.__class__.__name__,
            )
            raise exceptions.ConnectionException(
                f"Connection refused for {self._context.hostname}:{self._context.port}"
            ) from connection_error

    def stop(self) -> MQTTErrorCode:
        """Stop the MQTT client connection and network loop if needed.

        Returns:
            Result code from disconnect() or loop_stop().

        Raises:
            RuntimeError: If loop_stop fails.
        """
        if not self._context.connected:
            utils.i2m_log.warning("[%s] Unable to stop disconnected client", self)
            return mqtt.MQTT_ERR_SUCCESS
        _result_code = self.disconnect()
        if not self._context.loop_forever_used:
            _result_code = self.loop_stop()
            if _result_code != mqtt.MQTT_ERR_SUCCESS:
                utils.i2m_log.error(
                    'loop_stop failed - [%s] "%s"',
                    _result_code,
                    mqtt.error_string(_result_code),
                )
                raise RuntimeError("Unable to stop loop")
            self._context.started = False
        return _result_code

    def _do_connect(self) -> MQTTErrorCode:
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
                _connection_result = self.connect(
                    self._context.hostname,
                    port=self._context.port,
                    keepalive=self._context.keepalive,
                    clean_start=self._context.clean_start,
                    properties=None,
                )
                return _connection_result
            except (socket.gaierror, socket.timeout) as connection_error:
                if attempt < ConnectionRetryPolicy.MAX_RETRY - 1:
                    utils.i2m_log.warning(  # Attempt failed, but will retry
                        "[%s] Connection attempt %d/%d failed: %s",
                        self,
                        attempt + 1,
                        ConnectionRetryPolicy.MAX_RETRY,
                        connection_error,
                    )
                    time.sleep(ConnectionRetryPolicy.RETRY_DELAY)
                else:
                    utils.i2m_log.fatal(  # All retries exhausted
                        "[%s] Connection failed after %d attempts",
                        self,
                        ConnectionRetryPolicy.MAX_RETRY,
                    )
                    raise exceptions.ConnectionException(
                        f"Connection failed after {ConnectionRetryPolicy.MAX_RETRY} attempts"
                    ) from connection_error
        # Only reachable if MAX_RETRY < 1; makes the return contract explicit for type checkers.
        raise exceptions.ConnectionException("No connection attempt was made")


    def _handle_on_connect(  # pylint: disable=too-many-arguments
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        """Default connect callback: update connection state and invoke registered handlers."""
        if reason_code == mqtt.MQTT_ERR_SUCCESS:
            self._context.connected = True
        for on_connect_handler in self.on_connect_handlers:
            on_connect_handler(client, userdata, flags, reason_code, properties)

    def connect_handler_add(self, handler: Callable) -> None:
        """Register a callback to invoke when client successfully connects to broker.
        
        Args:
            handler: Callable with signature (client, userdata, flags, reason_code, properties) -> None
        
        Raises:
            TypeError: If handler is not callable.
        """
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler).__name__}")
        self.on_connect_handlers.append(handler)

    def disconnect(self, *argc, **argv) -> MQTTErrorCode:
        """Disconnect from broker and log the result.

        Overrides parent disconnect() to add logging. Arguments are passed through
        to the parent class method.

        Returns:
            Disconnection result code.
        """
        _result_code = super().disconnect(*argc, **argv)
        utils.i2m_log.debug("[%s] Disconnection request returns : %s", self, _result_code)
        return _result_code

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


