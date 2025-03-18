#!/usr/local/bin/python3
# coding=utf-8

"""
This module provides utility functions and classes for the iot2mqtt framework.

Classes
-------

- Singleton: A metaclass for creating singleton classes.

Constants
---------

- i2m_log: Logger instance for the iot2mqtt module.
- DEBUG: Boolean flag indicating whether debugging is enabled.

"""
import functools
import logging
import os
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, TypeVar

i2m_log = logging.getLogger("iot2mqtt")
DEBUG = True


@dataclass
class MetricsCollector:
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


LOGIT = True
if LOGIT:
    TIMEIT_INDENT = 1


def logit():
    """
    Decorator to log the function call and its parameters.
    """

    def decorator(func):
        # caller = getframeinfo(_stack[1][0])
        # _caller_frame = currentframe().f_back
        _caller_frame = sys._getframe().f_back
        _caller = _caller_frame.f_code.co_name
        _caller_info = traceback.extract_stack(f=_caller_frame, limit=1)[0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            args_repr = [str(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            global TIMEIT_INDENT
            # mes = f'{"-" * _TIMEIT_INDENT}> params: ({signature})'
            mes = f'{"-" * TIMEIT_INDENT}> caller: {_caller} - params: ({signature})'

            _name = func.__name__
            _filename = os.path.basename(_caller_info[0])
            _lineno = _caller_info[1]

            i2m_log.debug(
                mes,
                extra={
                    "name_override": _name,
                    "file_override": _filename,
                    "line_override": _lineno,
                },
            )
            _exc_start = time.perf_counter()
            TIMEIT_INDENT += 1
            result = func(*args, **kwargs)
            TIMEIT_INDENT -= 1
            _exc_end = time.perf_counter()
            i2m_log.debug(
                f'<{"-"*TIMEIT_INDENT} {result} [elapsed : {(_exc_end - _exc_start) * 1000:.2f} ms.]',
                extra={
                    "name_override": _name,
                    "file_override": _filename,
                    "line_override": _lineno,
                },
            )
            return result

        return wrapper

    def no_decorator(func):
        return func

    return decorator if LOGIT else no_decorator


STACK_INDENT = 4 * " "


def stacktrace(func):
    """
    Decorator to print the stack trace of the function call.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwds):
        callstack = "\n".join(
            [STACK_INDENT + line.strip() for line in traceback.format_stack()][:-1]
        )
        i2m_log.debug("---> %s:\n%s", func.__name__, callstack)
        return func(*args, **kwds)

    return wrapped


class TimerManager:
    """
    A class to manage timers for devices, ensuring thread safety and preventing multiple timers
    from being active for the same device in case of bouncing messages
    """

    def __init__(self):
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
        """
        Manages a timer for a specific device, ensuring that only one timer is active per device.

        This method creates and starts a new timer for the given device. If a timer for the device
        already exists, it cancels the existing timer before starting a new one. The timer will call
        the specified function (`task`) with the provided arguments (`args` and `kwargs`) after
        the countdown period.

        Args:
            device_id (str): The id of the device for which the timer is being managed.
            countdown (float): The countdown period in seconds after which the `task` function
                will be executed.
            task (Callable[..., Any]): The function to be called when the timer expires.
            args (tuple, optional): Positional arguments to be passed to the `task` function.
                Defaults to ().
            kwargs (Optional[Dict[str, Any]], optional): Keyword arguments to be passed to the
                `task` function. Defaults to None.

        Returns:
            threading.Thread: The newly created and started timer thread.
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
