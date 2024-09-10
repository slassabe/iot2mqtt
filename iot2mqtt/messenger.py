#!/usr/local/bin/python3
# coding=utf-8

"""
This module defines the messaging system for the IoT framework, including message types, 
message structures, and the mechanisms for producing and dispatching messages.

Classes
-------

- MessageType: Enumeration for IoT message types.
- Item: Represents a raw data item in the IoT system.
- Message: Represents a message in the IoT system.
- QueueManager: Base class for managing input and output queues.
- Producer: Thread-safe message producer that puts messages onto an output queue.
- Dispatcher: Thread-safe message dispatcher that processes messages from an input queue
  based on specified conditional handlers.

Functions
---------

- is_type_discovery: Checks if a message is of type discovery.
- is_type_availability: Checks if a message is of type availability.
- is_type_state: Checks if a message is of type state.

Examples
--------

Here is an example of how to access incoming MQTT messages and process them using a
dispatcher according to their message type:

.. code-block:: python

    import time

    from iot2mqtt import central, mqtthelper, messenger

    TARGET = "localhost"


    def main():
        _client = mqtthelper.ClientHelper(
            mqtthelper.MQTTContext(hostname=TARGET), mqtthelper.SecurityContext()
        )
        _client.start()
        _refined_queue = central.get_refined_data_queue(_client)

        messenger.Dispatcher(
            input_queue=_refined_queue,
            output_queue=None,
            conditional_handlers=[
                (messenger.is_type_availability, 
                lambda msg: print(f"Availability: {msg.device_name} {msg.refined}")),
            ],
        )


    if __name__ == "__main__":
        main()
        for _ in range(10):
            # Wait for 10 seconds before exiting
            print(".", end="", flush=True)
            time.sleep(1)

    # Display :
    # Availability: SWITCH_CAVE is_online=True
    # Availability: SWITCH_PLUG is_online=False

"""

import enum
import queue
import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple, TypeAlias, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

from iot2mqtt import dev, utils


class MessageType(enum.Enum):
    """
    Enumeration for IOT message types.
    """

    DISCO = "discovery"
    AVAIL = "availability"
    STATE = "state"

    def __str__(self) -> str:
        return self.value


class Item(BaseModel):
    """
    Represents a raw data item in the IoT system.

    Attributes:
        data (Union[Dict, str, List[Dict]]): The data associated with the item.
            It can be a dictionary, a string, or a list of dictionaries.
        tag (Optional[str]): An optional tag for the item, which can be used
            for additional metadata or categorization.
    """

    data: Union[Dict, str, List[Dict]]
    tag: Optional[str] = None


class Message(BaseModel):
    """
    Represents a message in the IoT system.

    Attributes:
        protocol (dev.Protocol): The communication protocol used by the device.
        model (Optional[dev.Model]): The model of the device, if available.
        device_name (str): The name of the device.
        message_type (MessageType): The type of the message (e.g., discovery,
            availability, state).
        raw_item (Item): The raw data item associated with the message.
        id (UUID): A unique identifier for the message, generated by default.
        refined (Optional[Item]): An optional refined version of the raw item.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    protocol: dev.Protocol
    model: Optional[dev.Model]
    device_name: str
    message_type: MessageType
    raw_item: Item
    id: UUID = Field(default_factory=uuid4)
    refined: SerializeAsAny[Optional[Item]] = None


# Class predicate definition
def is_type_discovery(msg: Message) -> bool:
    return msg.message_type == MessageType.DISCO


def is_type_availability(msg: Message) -> bool:
    return msg.message_type == MessageType.AVAIL


def is_type_state(msg: Message) -> bool:
    return msg.message_type == MessageType.STATE


class QueueManager:
    """
    QueueManager is a base class that implements a thread-safe message queue manager.

    This class provides the basic functionality for managing input and output queues
    that can be used by derived classes to implement specific message processing logic.

    Args:
        input_queue (queue.Queue): The queue from which messages are consumed.
        output_queue (queue.Queue): The queue to which processed messages are forwarded.
    """

    def __init__(self, input_queue: queue.Queue, output_queue: queue.Queue) -> None:
        self._input_queue = input_queue
        self._output_queue = output_queue


class Producer(QueueManager):
    """
    Producer is a thread-safe message producer that puts messages onto an output queue.

    This class extends the QueueManager to provide functionality for producing messages
    and placing them onto an output queue for further processing by consumers.

    Args:
        output_queue (queue.Queue): The queue to which produced messages are forwarded.

    """

    def __init__(self, output_queue: queue.Queue) -> None:
        super().__init__(input_queue=None, output_queue=output_queue)

    def put(self, message: Union[Message, str]) -> None:
        """
        Puts a message onto the output queue.

        Args:
            message (Union[Message, str]): The message to be placed onto the output queue.

        Returns:
            None
        """
        self._output_queue.put(message, block=True, timeout=1)


Handler: TypeAlias = Callable[[Message], Optional[Message]]
HandlerList: TypeAlias = Optional[List[Handler]]

Condition: TypeAlias = Callable[[Message], bool]
ConditionalProcessing: TypeAlias = Tuple[Condition, Handler]
ConditionalProcessingList: TypeAlias = List[ConditionalProcessing]


class Dispatcher(QueueManager):
    """
    Dispatcher is a thread-safe message dispatcher that processes messages from an input queue
    based on specified conditional handlers and optionally forwards the processed messages to an
    output queue.

    Args:
        input_queue (queue.Queue): The queue from which messages are consumed.
        output_queue (Optional[queue.Queue]): The queue to which processed messages are
            forwarded.
        conditional_handlers (ConditionalProcessingList): A list of tuples where each tuple
            contains a condition function and a handler function.
        default_handler (Optional[Handler]): A default handler function to process messages
            that do not match any condition. Defaults to None.
        name (Optional[str]): An optional name for the dispatcher. If not provided, a default
            name is generated.

    Attributes:
        STOP (str): Sentinel value used to signal the dispatcher to stop processing messages.

    """

    STOP = "STOP"
    _instance_nb = 0
    _instance_nb_lock = threading.Lock()

    def __init__(
        self,
        input_queue: queue.Queue,
        output_queue: Optional[queue.Queue],
        conditional_handlers: ConditionalProcessingList,
        default_handler: Optional[Handler] = None,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(input_queue, output_queue)
        with Dispatcher._instance_nb_lock:
            self.name = name or f"Dispatcher#{Dispatcher._instance_nb}"
            Dispatcher._instance_nb += 1
        self.conditional_handlers = conditional_handlers
        self._default_handler = default_handler or self._no_handler
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop_event = threading.Event()  # Use an event for stopping
        self._thread.start()
        utils.i2m_log.debug(
            "[%s] Dispatcher started at %s", self.name, datetime.now().isoformat()
        )

    def __str__(self) -> str:
        conditional_handlers_count = (
            len(self.conditional_handlers) if self.conditional_handlers else 0
        )
        return (
            f"Dispatcher(name={self.name}, "
            f"conditional_handlers_count={conditional_handlers_count}, "
            f"input_queue_size={self._input_queue.qsize()}, "
            f"output_queue_size={self._output_queue.qsize() if self._output_queue else 'N/A'})"
        )

    def _no_handler(self, message: Message) -> Optional[Message]:
        utils.i2m_log.debug(
            "No handler set for message with ID: %s, Device: %s, Type: %s",
            message.id,
            message.device_name,
            message.message_type,
        )

    def _process_and_put(self, handler: Handler, message: Message) -> None:
        """
        Processes a message using the given handler and puts the result in the output queue.

        Args:
            handler (Handler): The handler function to process the message.
            message (Message): The message to be processed.

        Returns:
            None
        """
        _result = handler(message)
        if self._output_queue is None:
            return
        if _result is None:
            return
        self._output_queue.put(_result)

    def _run(self) -> None:
        """
        The main loop that processes messages from the input queue based on conditional handlers.

        This method runs in a separate thread and continuously processes messages from the input
        queue.
        It checks each message against the conditional handlers and processes it using the first
        matching handler.
        If no handlers match, the default handler is used. The loop stops when the stop event is
        set or a STOP message is received.

        Returns:
            None
        """
        while not self._stop_event.is_set():
            try:
                _message = self._input_queue.get(
                    timeout=1
                )  # Use timeout to periodically check the stop event
            except queue.Empty:
                continue

            if _message == self.STOP:
                utils.i2m_log.debug("[%s] Dispatcher stopped", self.name)
                break

            if _message is None:
                utils.i2m_log.error("Message is None")
                continue

            _found = False
            try:
                for _condition, _handler in self.conditional_handlers:
                    if _condition(_message):
                        if _found:
                            utils.i2m_log.warning(
                                "[%s: Ignored] Id: %s - Device: %s - Type : %s - Refined: %s",
                                self.name,
                                _message.id,
                                _message.device_name,
                                _message.message_type,
                                _message.refined,
                            )
                            break
                        _found = True
                        self._process_and_put(_handler, _message)

                if not _found:
                    self._process_and_put(self._default_handler, _message)
            except TypeError as e:
                utils.i2m_log.error(
                    "Exception evaluating conditional handler handler: %s",
                    e,
                    exc_info=True,
                )
            self._input_queue.task_done()

    def stop_loop(self) -> None:
        """Process all pending messages and stop the loop."""
        # self._input_queue.put(self.STOP, block=True, timeout=1)
        self._input_queue.put(self.STOP)
        self._thread.join()

    def force_stop(self) -> None:
        """
        Forcefully stops the dispatcher by setting the stop event.

        This method signals the dispatcher to stop processing messages by setting
        the internal stop event. It is typically used to gracefully shut down the
        dispatcher when it is no longer needed. Once the stop event is set, the
        dispatcher will complete processing any current message and then exit its
        run loop.

        Logs a debug message indicating that the dispatcher has been forcefully stopped.

        Returns:
            None
        """
        self._stop_event.set()  # Signal the stop event
        utils.i2m_log.debug("[%s] Dispatcher force stopped", self.name)