# User Guide

## Prerequisites

- Make sure your MQTT broker is running and accessible at the specified `TARGET` hostname.
- Make sure Zigbee2MQTT is up and running

## How to Get Device State

This guide explains how to retrieve and display the state of a device, specifically focusing on an air sensor's temperature and humidity.

### Example: Display Air Sensor Temperature and Humidity

The following example demonstrates how to use the `iot2mqtt` library to connect to an MQTT broker, retrieve messages from an air sensor, and display its temperature and humidity.

```python
import iot2mqtt as i2m

# Define the MQTT broker hostname
TARGET = "localhost"

def main():
    # Initialize the MQTT client helper with the specified context
    _client = i2m.mqtthelper.ClientHelper(
        i2m.mqtthelper.MQTTContext(hostname=TARGET), i2m.mqtthelper.SecurityContext()
    )
    _client.start()

    # Get the refined data queue from the central module
    _refined_queue = i2m.central.get_refined_data_queue(_client)

    # Get and print the next 3 Airsensor messages from the refined data queue
    _nb_messages = 0
    while _nb_messages < 3:
        # Retrieve the next message from the queue
        _message = _refined_queue.get()

        # Check if the message was issued by the specified Airsensor Model
        if i2m.messenger.is_type_state(_message) and _message.model == i2m.setup.Models.SN_AIRSENSOR:
            _instance: i2m.abstract.AirSensor = _message.refined
            print(f'Air sensor state changed to: {_instance.temperature} °C - {_instance.humidity} %')
            _nb_messages += 1

if __name__ == "__main__":
    main()
```

#### Explanation

- ***Initialization*** : The script initializes the MQTT client helper with the specified hostname and security context and security context and start it.
- ***Data Queue*** : It retrieves the refined data queue from the central module.
- ***Message Processing***: The script continuously processes messages from the refined data queue.
- ***Message Filtering***: It checks if the message is of type state and if it was issued by the Airsensor Model.
- ***Display***: If the conditions are met, it prints the air sensor's temperature and humidity :
  - Air sensor state changed to: 19.11 °C - 78.77 %
  - Air sensor state changed to: 19.02 °C - 78.27 %
  - Air sensor state changed to: 19.02 °C - 78.77 %

This example provides a basic template for integrating with an MQTT broker and processing messages from an air sensor. You can extend this example to handle other types of devices and messages as needed.

## How to Change the State of Any Device

This section provides examples of how to request a state change for devices using the `trigger_change_state()` method.

### Example: Changing the State of a NEO Nas Alarm

The following example demonstrates how to set the NEO Nas Alarm to ON for 10 seconds.


```python
import time
import iot2mqtt as i2m

TARGET = "localhost"

def main():
    _client = i2m.mqtthelper.ClientHelper(
        i2m.mqtthelper.MQTTContext(hostname=TARGET), i2m.mqtthelper.SecurityContext()
    )
    _client.start()

    # Create a DeviceAccessor instance with the MQTT client
    _accessor = i2m.central.DeviceAccessor(mqtt_client=_client)

    # Set Zigbee NEO Nas Alarm melody
    _state_melody = {
        "melody": 9,
    }
    _accessor.trigger_change_state(
        device_id="ALARM",
        protocol=i2m.dev.Protocol.Z2M,
        state=_state_melody,
    )
    # Define the state to set the Zigbee NEO Nas Alarm ON for 10 seconds
    _state_on = {
        "alarm": True,
        "duration": 10,
    }
    # Trigger the state change on the device
    _accessor.trigger_change_state(
        device_id="ALARM",
        protocol=i2m.dev.Protocol.Z2M,
        state=_state_on,
    )

if __name__ == "__main__":
    main()
    for _ in range(10):
        time.sleep(1)
```

#### Explanation

- ***Initialization*** : The script initializes the MQTT client helper with the specified hostname and security context and start it.
- ***Device Accessor*** : It creates a `DeviceAccessor` instance with the MQTT client.
- ***State Definition*** : It defines the state to set the NEO Nas Alarm to ON for 10 seconds.
- ***State Change*** : It triggers the state change on the device.

## How to Change the State of One or More Switches

This section provides examples of how to request a state change for devices using the `trigger_change_state()` or `switch_power_change_helper()` methods.

### Example: Changing the Switch State Knowing the Protocol and Model

The following example demonstrates how to change the switch state for devices using the `switch_power_change()` method. This method is straightforward as it does not require launching the pipeline and waiting for the devices to be discovered.


```python
import time
import iot2mqtt as i2m

TARGET = "localhost"

def main():
    _client = i2m.mqtthelper.ClientHelper(
        i2m.mqtthelper.MQTTContext(hostname=TARGET), i2m.mqtthelper.SecurityContext()
    )
    _client.start()

    _accessor = i2m.central.DeviceAccessor(mqtt_client=_client)
    # Set switch ON for 5 sec.
    _accessor.switch_power_change(
        device_ids="SWITCH_PLUG",
        protocol=i2m.dev.Protocol.Z2M,
        model=i2m.setup.Models.SN_SMART_PLUG,
        power_on=True,
        on_time=5,
    )

if __name__ == "__main__":
    main()
    for pos in range(10):
        helper.animate_cursor(pos)
        time.sleep(1)
```

#### Explanation

- ***Initialization*** : The script initializes the MQTT client helper with the specified hostname and security context and start it.
- ***Device Accessor*** : It creates a `DeviceAccessor` instance with the MQTT client.
- ***State Change*** : It triggers the state change on the switch device.
- ***Note*** : The `switch_power_change()` method is a convenience method that uses the `trigger_change_state()` method under the hood.

### Example: Changing the Switch State by Names

Alternatively, you can change the switch state for multiple devices using the `switch_power_change_helper()` method. This method is more flexible as it allows changing the state of multiple devices with different protocols or models. It requires initializing the message pipe to discover devices.


```python
import time
import iot2mqtt as i2m

TARGET = "localhost"

SWITCH1 = "0x00124b0024cb17d3" # Zigbee switch device
SWITCH2 = "tasmota_577591" # Tasmota switch device

def main():
    _client = i2m.mqtthelper.ClientHelper(
        i2m.mqtthelper.MQTTContext(hostname=TARGET), i2m.mqtthelper.SecurityContext()
    )
    _client.start()
    # Initialize the message pipe to discover devices
    i2m.central.get_refined_data_queue(_client)

    time.sleep(2)  # Wait for the MQTT client to be discovered
    _accessor = i2m.central.DeviceAccessor(mqtt_client=_client)
    # Set switch ON for 5 sec.
    _accessor.switch_power_change_helper(
        device_ids=f"{SWITCH1},{SWITCH2}",
        power_on=True,
        on_time=5,
    )

if __name__ == "__main__":
    main()
    for pos in range(10):
        time.sleep(1)
```

#### Explanation

- ***Initialization*** : The script initializes the MQTT client helper with the specified hostname and security context and start it.
- ***Message Pipe*** : It initializes the message pipe to discover devices.
- ***Wait*** : It waits 2 sec. for the MQTT client to be discovered.
- ***Device Accessor*** : It creates a `DeviceAccessor` instance with the MQTT client.
- ***State Change*** : It triggers the state change on the `Zigbee` and `Tasmota` switch devices.
- ***Note*** : The `switch_power_change_helper()` method is a convenience method that uses the `trigger_change_state()` method under the hood.

### Wrapup

- `switch_power_change()` : Use this method when you know the protocol and model of the device. It is easier to use because it does not require launching the pipeline and waiting for the devices to be discovered.
- `switch_power_change_helper()` : Use this method when you need more flexibility, such as changing the state of multiple devices with different protocols or models. This method requires initializing the message pipe to discover devices.

## How to control SOMFY shades

This section provides examples of how to control SOMFY upon ESPSomfy RTS protocol.

### Example: Opening and Closing a Shade

The following example demonstrates how to open and close a shade using the `trigger_change_state()` method.

```python
import iot2mqtt as i2m

def _shade_move(
    accessor: i2m.central.DeviceAccessor, device_id: str, direction: int, to: int
):
    """ Moves the shade to the specified position. """
    _states = [
        {i2m.abstract.DIRECTION: direction},
        {i2m.abstract.TARGET: to},
    ]
    for _state in _states:
        accessor.trigger_change_state(
            device_id=device_id,
            protocol=i2m.dev.Protocol.ESPSOMFY,
            state=_state,
        )

def _shade_up(accessor: i2m.central.DeviceAccessor, device_id: str, to: int = 100):
    """Move the shade up to the specified position."""
    _shade_move(accessor, device_id, direction=-1, to=to)

def _shade_down(accessor: i2m.central.DeviceAccessor, device_id: str, to: int = 0):
    """Move the shade down to the specified position."""
    _shade_move(accessor, device_id, direction=1, to=to)

```

#### Explanation

- ***_shade_move*** : This function is a helper function that moves the shade to the specified position. It takes the following parameters:
- `accessor` (i2m.central.DeviceAccessor): The device accessor object used to trigger the state change.
- `device_id` (str): The ID of the device to which the state change should be applied.
- `direction` (int): The direction of the shade movement.
  - `-1` means the shade is moving up
  - `0` means the shade is stopped
  - `1` means the shade is moving down
- `to` (int): The target position for the shade, as a percentage of the full range.
- ***_shade_up*** : This function moves the shade up to the specified position.
- ***_shade_down*** : This function moves the shade down to the specified position.

### Example: Managing the Event Loop

```python
import time

# Define the MQTT broker hostname
TARGET = "localhost"
SHADE_ID = "2"

def main():
    def _print_shade_position(message: i2m.messenger.Message) -> None:
        """Print the current position of the shade."""
        _to_print = {k: v for k, v in message.refined if v is not None}
        print(f">>> [{message.device_id}] {message.message_type.value}: {_to_print}")
    def _message_filter(message: i2m.messenger.Message) -> bool:
        return message.message_type == i2m.messenger.MessageType.STATE

    # Initialize the MQTT client helper with the specified context
    _app_client = i2m.mqtthelper.ClientHelper(
        i2m.mqtthelper.MQTTContext(hostname=TARGET), i2m.mqtthelper.SecurityContext()
    )
    _app_client.start()
    # Initialize the refined data queue restricted to ESPSomfy devices
    _refined_queue = i2m.central.get_refined_data_queue(
        _app_client, protocols_expected=[i2m.dev.Protocol.ESPSOMFY]
    )
    _accessor = i2m.central.DeviceAccessor(mqtt_client=_app_client)
    # Initialize the main loop queue, waiting for messages
    i2m.messenger.Dispatcher(
        input_queue=_refined_queue,
        output_queue=None,
        conditional_handlers=[
            # Display shade position
            (_message_filter, _print_shade_position),
        ],
        default_handler=i2m.processor.Processor.no_op,
    )
    while True:
        # Loop moving the shade up and down
        print("Shade Down ...")
        _shade_up(_accessor, device_id=SHADE_ID, to=0)
        time.sleep(30)
        print("Shade Up ...")
        _shade_down(_accessor, device_id=SHADE_ID, to=50)
        time.sleep(30)

if __name__ == "__main__":
    main()
```

The script execution displays the following output:

```text
Shade Down ...
>>> [2] state: {'target': 0}    # Target position set to 0% (fully closed)
>>> [2] state: {'direction': -1}# Movement direction set to up (-1)
>>> [2] state: {'position': 49} # Current position updates as shade moves
...
>>> [2] state: {'position': 1} # Position approaching target
>>> [2] state: {'position': 0} # Final position reached
```

#### Explanation

The script performs the following steps:

1) Initializes the MQTT client with the security context and hostname.
2) Starts the MQTT client.
3) Create the message data queue restricted to ESPSomfy devices.
4) Initialize the main loop, waiting for processing messages:
   - Just printing the shade position found in the refined data queue.
5) Loop moving the shade up and down every 30 seconds.

#### Understanding the Event Loop Output

Each message shows:

- Device ID in brackets [2]
- Message type (state)
- Current shade parameters as key-value pairs:
  - target: Desired position (0-100%)
  - direction: Movement direction (-1=up, 0=stop, 1=down)
  - position: Current position as percentage
  
The position updates provide real-time feedback as the shade moves toward its target position.

## Script customization

The script integration allows users to specify a sequence of actions to be executed according to the state of the devices. The following sections provide examples of how to customize the script.

### Example: Changing the State of a Switch on Motion Detection

This example demonstrates how to create a script that changes the state of a switch when motion is detected. The switch will remain on for 15 seconds before turning off.

```python
import iot2mqtt as i2m
# Define the MQTT broker hostname
TARGET = "localhost"

# Define the switch and motion device names
SWITCH = "SWITCH_CAVE"
MOTION_DEVICE = "MOTION_CAVE"

# Define the duration (in seconds) for which the switch should remain on
SHORT_TIME = 15 

def main():
    # Initialize the MQTT client helper with the specified context
    _client = i2m.mqtthelper.ClientHelper(
        i2m.mqtthelper.MQTTContext(hostname=TARGET), i2m.mqtthelper.SecurityContext()
    )
    _client.start()

    # Get the refined data queue from the central module
    _refined_queue = i2m.central.get_refined_data_queue(_client)

    # Create a device accessor to interact with the devices
    _accessor = i2m.central.DeviceAccessor(mqtt_client=_client)

    # Continuously process messages to find motion detection messages
    while True:
        # Retrieve the next message from the queue
        _message = _refined_queue.get()

        # Check if the message indicates motion detection for the specified device
        if i2m.processor.is_motion_detected(_message, MOTION_DEVICE):
            print(
                f'Motion detected, turning switches on for {SHORT_TIME} sec.')

            # Change the state of the switch to 'on' for the specified duration
            _accessor.switch_power_change_helper(
                device_ids=SWITCH, power_on=True, on_time=SHORT_TIME,
            )
            # End loop
            return

if __name__ == "__main__":
    main()
```

#### Explanation

The script performs the following steps:

1. Connects to the MQTT broker.
2. Continuously listens for motion detection messages.
3. Turns on the switch when motion is detected and keeps it on for a specified duration.
4. Ends the loop when motion is detected.

### Example: Changing the State of a Switch on Button Action

This example demonstrates how to create a script that changes the state of a switch when a button action is detected. The switch will remain on for a specified duration before turning off.

```python
import iot2mqtt as i2m
# Define the MQTT broker hostname
TARGET = "localhost"

# Define the switch and button device names
SWITCH = "SWITCH_CAVE"
BUTTON_DEVICE = "INTER_CAVE"

# Define the duration (in seconds) for which the switch should remain on
SHORT_TIME = 15  
MEDIUM_TIME = 30  
LONG_TIME = 60  

def main():
    # Initialize the MQTT client helper with the specified context
    _client = i2m.mqtthelper.ClientHelper(
        i2m.mqtthelper.MQTTContext(hostname=TARGET), i2m.mqtthelper.SecurityContext()
    )
    _client.start()

    # Get the refined data queue from the central module
    _refined_queue = i2m.central.get_refined_data_queue(_client)

    # Create a device accessor to interact with the devices
    _accessor = i2m.central.DeviceAccessor(mqtt_client=_client)

    def handle_button_action(message, device, action, switch, on_time=None, power_on=True):
        if i2m.processor.is_button_action_expected(message, device, action):
            action_desc = 'on' if power_on else 'off'
            print(f'Button {action} pressed, turning switches {action_desc} for {on_time} sec.')
            _accessor.switch_power_change_helper(
                device_ids=switch, power_on=power_on, on_time=on_time)
            return True
        return False
    # Continuously process messages from the refined data queue
    while True:
        # Retrieve the next message from the queue
        _message = _refined_queue.get()

        # Check if the message indicates button press for the specified device
        if handle_button_action(
            _message, BUTTON_DEVICE, i2m.abstract.ButtonValues.SINGLE_ACTION, SWITCH, MEDIUM_TIME
        ):
            continue
        if handle_button_action(
            _message, BUTTON_DEVICE, i2m.abstract.ButtonValues.DOUBLE_ACTION, SWITCH, LONG_TIME
        ):
            continue
        if handle_button_action(
            _message, BUTTON_DEVICE, i2m.abstract.ButtonValues.LONG_ACTION, SWITCH, power_on=False
        ):
            continue

if __name__ == "__main__":
    main()
```

#### Explanation

The script performs the following steps:

1. Connects to the MQTT broker.
2. Continuously listens for button action messages.
3. Turns on the switch when button press is detected and keeps it on for a specified duration.

