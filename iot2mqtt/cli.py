# coding=utf-8
import argparse
import signal
import sys
import time

from iot2mqtt import __version__, central, dev, exceptions, messenger, mqtthelper

ANIMATION = "|/-\\"
C_GREEN = "\033[0;32m"
C_END = "\033[0m"
C_BOLD = "\033[1m"


def animate_cursor(position: int):
    _anim = ANIMATION[position % len(ANIMATION)]
    print(f"\r{C_GREEN}{_anim}{C_END}", end="")


def signal_handler(sig, frame):
    print("\nSignal received, exiting...")
    sys.exit(0)


def _format(msg: messenger.Message, verbose: bool, readable: bool = True) -> str:
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
        return {
            "device_id": msg.device_id,
            "message_type": msg.message_type.value,
            "protocol": msg.protocol.value,
            "model": msg.model,
            "raw_item": msg.raw_item,
            "refined": msg.refined,
        }
    return {
        "device_id": msg.device_id,
        "message_type": msg.message_type.value,
        "refined": msg.refined,
    }


def _handle_msg(msg: messenger.Message, devices: str, verbose: bool, readable: bool) -> None:
    if devices and msg.device_id not in devices:
        return
    print(_format(msg=msg, verbose=verbose, readable=readable))


def main():
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

    args = parser.parse_args()
    if args.brocker:
        _brocker = args.brocker
        print(f"MQTT: Using broker {_brocker}")
    else:
        _brocker = "localhost"
        print(f"MQTT: Using default broker {_brocker}")
    _client = mqtthelper.ClientHelper(
        mqtthelper.MQTTContext(hostname=_brocker), mqtthelper.SecurityContext()
    )
    try:
        _client.start()
    except exceptions.ConnectionException:
        sys.exit(1)

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
