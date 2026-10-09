#!/usr/local/bin/python3
# coding=utf-8

"""
Utility functions and classes for the iot2mqtt framework.

Provides singleton metaclass, parameter validation, timer management for device
polling, and metrics collection utilities.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Type, TypeVar

i2m_log = logging.getLogger("iot2mqtt")
DEBUG = True


@dataclass
class MetricsCollector:
    """Collect queue size, processing times, and message counts for monitoring."""

    queue_size_max: int = 0
    start_processing: float = 0.0
    processing_times: Dict[str, float] = field(default_factory=dict)
    message_counts: Dict[str, int] = field(default_factory=dict)

    def record_queue_size(self, size: int) -> None:
        self.queue_size_max = max(size, self.queue_size_max)

    def start_collect(self) -> None:
        self.start_processing = time.time()

    def end_collect(self, message_type: str) -> None:
        duration = time.time() - self.start_processing
        self.processing_times[message_type] = duration
        self.message_counts[message_type] = self.message_counts.get(message_type, 0) + 1

    def get_metrics(self) -> Dict:
        return {
            "queue_sizes": self.queue_size_max,
            "processing_times": self.processing_times,
            "message_counts": self.message_counts,
        }


T = TypeVar("T")


class Singleton(type):
    """Metaclass for creating singleton classes.

    Based on Python Cookbook Recipes for Mastering Python 3 by Beazley and Jones.
    Ensures only one instance of the decorated class is created.
    """

    def __init__(cls: Type[T], *args, **kwargs) -> None:
        cls.__instance = None
        super().__init__(*args, **kwargs)

    def __call__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
            return cls.__instance
        return cls.__instance


def check_parameter(name: str, value: Any, class_of: type, optional: bool = False) -> None:
    """Validate a parameter's type and optionality.

    Raises TypeError if the parameter is None when not optional, or if it doesn't
    match the expected type.

    Args:
        name: Parameter name for error messages.
        value: Value to validate.
        class_of: Expected type for the parameter.
        optional: Whether None is acceptable; defaults to False.

    Raises:
        TypeError: If validation fails.
    """
    if value is None:
        if optional:
            return
        raise TypeError(f"Not optional parameter {name} is None")
    if not isinstance(value, class_of):
        raise TypeError(f"{name} must be a {class_of}, got {value} of class {type(value).__name__}")


class TimerManager:
    """Manage timers for devices with thread safety and single-timer-per-device enforcement.

    Prevents multiple concurrent timers for the same device by cancelling existing timers
    when new ones are created. Useful for handling bouncing messages during polling.
    """

    def __init__(self):
        """Initialize timer registry with lock for thread safety."""
        self._timer_registry: Dict[str, threading.Thread] = {}
        self._timer_registry_lock = threading.Lock()

    def create_timer(
        self,
        device_id: str,
        countdown: float,
        task: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> threading.Thread:
        """Create and start a timer for a device, cancelling any existing timer.

        Only one timer per device_id is active at a time. If a timer already exists
        for the given device_id, it is cancelled before the new timer starts.

        Args:
            device_id: Identifier for the device.
            countdown: Delay in seconds before task execution.
            task: Callable to invoke when timer expires.
            args: Positional arguments for task; defaults to empty tuple.
            kwargs: Keyword arguments for task; defaults to None.

        Returns:
            The started timer thread.

        Raises:
            Exception: If timer creation or management fails.
        """
        if kwargs is None:
            kwargs = {}
        try:
            with self._timer_registry_lock:
                _previous_timer = self._timer_registry.get(device_id)
                if _previous_timer is not None:
                    i2m_log.debug("Replace previous timer for %s", device_id)
                    _previous_timer.cancel()
                else:
                    i2m_log.debug(
                        "No timer found for device '%s' in: %s",
                        device_id,
                        self._timer_registry,
                    )
                _timer = threading.Timer(countdown, task, args=args, kwargs=kwargs)
                _timer.start()
                self._timer_registry[device_id] = _timer
        except Exception as e:
            i2m_log.error("Failed to manage timer for %s: %s", device_id, str(e))
            raise


def retry_with_timer(
    timer_manager: TimerManager,
    key: str,
    countdown_base: float,
    max_retries: int,
    task: Callable[..., Any],
    retry_count: int = 0,
    args: tuple = (),
    kwargs: Optional[Dict[str, Any]] = None,
) -> bool:
    """Schedule a retry of task with linear backoff via timer_manager.

    Schedules the task to run again after countdown_base * (retry_count + 1) seconds.
    Increments retry_count automatically and passes it to task via kwargs.

    Args:
        timer_manager: TimerManager instance for scheduling.
        key: Device or operation identifier for timer registry.
        countdown_base: Base delay in seconds; multiplied by (retry_count + 1).
        max_retries: Maximum retry attempts allowed.
        task: Callable to retry.
        retry_count: Current attempt number; defaults to 0.
        args: Positional arguments for task; defaults to empty tuple.
        kwargs: Keyword arguments for task; defaults to None.

    Returns:
        True if retry was scheduled, False if max_retries exceeded (final failure).
    """
    if retry_count > max_retries:
        return False
    _kwargs = dict(kwargs or {})
    _kwargs["retry_count"] = retry_count + 1
    timer_manager.create_timer(
        device_id=key,
        countdown=countdown_base * (retry_count + 1),
        task=task,
        args=args,
        kwargs=_kwargs,
    )
    return True
