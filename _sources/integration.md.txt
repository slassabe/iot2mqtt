# Integration Guide

When devices are paired with Zigbee2MQTT, they are automatically discovered and added to the MQTT broker. However, some devices may not be configured in iot2mqtt generating warning messages in the logs.

```bash
 WARNING | iot2mqtt | processor.py:575 |  process(): [0xa4c1383fa08a72e8] Model tag='E3' not supported
```

To resolve this issue, you can integrate this device into the iot2mqtt ecosystem by creating a new device model.

## How to integrate new devices

Different concrete devices can be represented by the same abstract device. For example, the `ZBMINI-L` and `Shelly Plug S` devices share the same abstract representation `abstract.Switch`, with the same property `power`.

### How to Define an Abstract Representation of the Device

In file `iot2mqtt/model/abstract.py`, you should define an abstract representation of the device.

- by the use of new abstract properties, for example, `contact`
- and by the definition of the abstract class, for example `DoorSensor`

### How to Setup a New Device Model

In file `iot2mqtt/setup.py`, you should define a new device model model name and define , for example:

```python
E3 = "E3"
```

## How to integrate new protocols

1) Define the new protocol in enumeration `Protocol` in file `iot2mqtt/dev.py`