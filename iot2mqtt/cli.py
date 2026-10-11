# coding=utf-8
"""Command-line interface for monitoring and displaying IoT device messages from MQTT brokers.

This module provides a CLI tool that connects to an MQTT broker, listens for incoming
messages from integrated IoT protocols (starting with Zigbee2MQTT), decodes them, and
displays them in human-readable or JSON format.

Basic usage:

    iot2mqtt [-b BROKER] [-d DEVICES] [-l SECONDS] [-r] [-v] [--debug]

Options:

    -b, --brocker       MQTT broker hostname (default: localhost)
    --debug             enable DEBUG logging
    -d, --devices       Comma-separated device IDs to filter (displays all if omitted)
    -l, --loop          Run for specified number of seconds (default: runs indefinitely)
    -r, --readable      Display output as human-readable text (default: JSON format)
    -v, --verbose       Include raw data and protocol details in output

Examples:

    # Monitor all messages from default localhost broker in JSON format
    iot2mqtt

    # Monitor specific devices in readable format
    iot2mqtt -d device1,device2 -r

    # Monitor with verbose details for 60 seconds
    iot2mqtt -l 60 -v -r

    # Connect to remote broker and filter devices
    iot2mqtt -b mqtt.example.com -d sensor_kitchen -r

Main entry point: main()
"""
import argparse
import json
import logging
import signal
import sys
import time

from iot2mqtt import __version__, central, dev, exceptions, messenger, mqtthelper

ANIMATION = "|/-\\"
C_GREEN = "\033[0;32m"
C_END = "\033[0m"
C_BOLD = "\033[1m"


def animate_cursor(position: int):
    """Display animated cursor at current position."""
    _anim = ANIMATION[position % len(ANIMATION)]
    print(f"\r{C_GREEN}{_anim}{C_END}", end="")


def signal_handler(sig, frame):
    """Exit gracefully on SIGINT signal."""
    print("\nSignal received, exiting...")
    sys.exit(0)


def _format(msg: messenger.Message, verbose: bool, readable: bool = True) -> str:
    """Format message for display as human-readable text or JSON.

    Args:
        msg: Message to format.
        verbose: Include raw and protocol data if True.
        readable: Format as readable text if True, else JSON; defaults to True.

    Returns:
        Formatted message string or dict.
    """
    if readable:
        if verbose:
            return (
                f"{C_GREEN} [{msg.device_id}]{C_END} "
                f"{C_BOLD}type:{C_END} {msg.message_type}"
                f" - {C_BOLD}protocol:{C_END} {msg.protocol.value}"
                f" - {C_BOLD}model:{C_END} {msg.model}\n"
                f"\t{C_BOLD}raw:{C_END} {msg.raw_item}\n"
                f"\t{C_BOLD}refined:{C_END} {msg.refined.model_dump(mode='json')}"
            )
        return (
            f"{C_GREEN} [{msg.device_id}]{C_END} "
            f" - {C_BOLD}type:{C_END} {msg.message_type}"
            f" - {C_BOLD}model:{C_END} {msg.model}\n"
            f" - {C_BOLD}refined:{C_END} {msg.refined.model_dump(mode='json')} "
        )
    # Assuming json formatting
    if verbose:
        return json.dumps(
            {
                "device_id": msg.device_id,
                "message_type": msg.message_type.value,
                "protocol": msg.protocol.value,
                "model": msg.model,
                "raw_item": str(msg.raw_item),
                "refined": msg.refined.model_dump(mode="json"),
            }
        )
    return json.dumps(
        {
            "device_id": msg.device_id,
            "message_type": msg.message_type.value,
            "refined": msg.refined.model_dump(mode="json"),
        }
    )


def _handle_msg(msg: messenger.Message, devices: str, verbose: bool, readable: bool) -> None:
    """Filter and display a message if it matches the device filter.

    Prints the formatted message only if no device filter is set or the message's
    device_id is in the comma-separated devices list.
    """
    if devices and msg.device_id not in devices:
        return
    print(_format(msg=msg, verbose=verbose, readable=readable))


def main():
    """CLI entry point for iot2mqtt message monitoring.

    Connects to an MQTT broker, subscribes to Zigbee2MQTT topics, processes messages,
    and displays them in readable or JSON format with optional verbosity and device filtering.

    Supports the following command-line options:
    - -b/--broker: MQTT broker hostname (default: localhost)
    - --debug: enable DEBUG logging
    - -d/--devices: Comma-separated device IDs to filter
    - -l/--loop: Run for specified number of seconds
    - -r/--readable: Display as readable text (default: JSON)
    - -v/--verbose: Include raw and protocol details in output

    Exits gracefully on SIGINT (Ctrl+C).
    """
    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler)

    print(f"iot2mqtt version: {__version__}")
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--brocker", type=str, help="set the host of the broker")
    parser.add_argument(
        "-d", "--devices", type=str, help="set the devices to spy, comma separated names"
    )
    parser.add_argument(
        "-l", "--loop", type=int, help="loop for a specific number of seconds (default 10 sec.)"
    )
    parser.add_argument(
        "-r",
        "--readable",
        action="store_true",
        help="display information for biped (default is JSON)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
    parser.add_argument("--debug", action="store_true", help="enable DEBUG logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.brocker:
        _brocker = args.brocker
        print(f"MQTT: Using broker {_brocker}")
    else:
        _brocker = "localhost"
        print(f"MQTT: Using default broker {_brocker}")
    _client = mqtthelper.ClientHelper(
        mqtthelper.MQTTContext(hostname=_brocker), mqtthelper.SecurityContext()
    )
    # Uncomment next line to display paho messages (verbose):
    # _client.enable_logger()

    try:
        _client.start()
    except exceptions.ConnectionException:
        print(f"Error: Failed to connect to MQTT broker at {_brocker}", file=sys.stderr)
        sys.exit(1)

    # Listen to Zigbee device messages
    _refined_queue = central.get_refined_data_queue(_client, protocols_expected=[dev.Protocol.Z2M])

    # Configure a dispatcher to handle all incoming messages
    _dispatcher = messenger.Dispatcher(
        input_queue=_refined_queue,
        output_queue=None,
        conditional_handlers=[],
        default_handler=lambda msg: _handle_msg(msg, args.devices, args.verbose, args.readable),
    )
    # Animate cursor
    _nb_loop = 0
    while True:
        if args.loop and _nb_loop > args.loop:
            _dispatcher.force_stop()
            sys.exit(0)
        _nb_loop += 1
        if args.readable:
            animate_cursor(_nb_loop)
        time.sleep(1)
