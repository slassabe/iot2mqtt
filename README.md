# iot2mqtt: Simplifying IoT Solutions with MQTT Integration

***"Less is More"***

## Introduction

**iot2mqtt** is a versatile Python library built upon the Paho™ MQTT client. It is designed to simplify IoT application development by providing a programmatic alternative to traditional home automation platforms, without the overpromises of no-code solutions.

![Landscape](https://slassabe.github.io/iot2mqtt/_images/landscape.png)

## Description

**iot2mqtt** offers a robust and flexible solution for integrating various IoT devices using the MQTT protocol. Whether you are looking to connect directly with devices or through gateways, **iot2mqtt** provides the tools you need to build reliable and scalable IoT applications.

### Key Features

- **Programmatic Alternative**: Provides more flexibility and control compared to traditional home automation platforms like openHAB, Home Assistant, and Jeedom.
- **Reliable Communication**: Leverages the MQTT protocol to ensure reliable data transfer between devices.
- **Protocol-Agnostic**: Supports both direct device integration over MQTT (e.g., Shelly, Tasmota) and gateway integration (e.g., Zigbee2MQTT, ring to MQTT, miflora to MQTT).
- **Abstract Devices**: Comprehensive support for creating and managing abstract devices, simplifying the integration between different device models, providers, and protocols.

## Documentation

You can access the full documentation at [slassabe.github.io/iot2mqtt](https://slassabe.github.io/iot2mqtt/)

## Getting Started

To get started with **iot2mqtt**, follow these steps:

### Prerequisites

- Python 3.x
- IoT bridges if required (e.g., Zigbee2MQTT, ring to MQTT, miflora to MQTT)

### Installation

The latest stable version is available in the Python Package Index (PyPi) and can be installed using

```bash
pip3 install iot2mqtt
```

or with `virtualenv`:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip3 install iot2mqtt
```

### Installation from Github

To obtain the code, you can clone the Github repository:

1. Clone the repository:

    ```bash
    git clone https://github.com/slassabe/iot2mqtt.git
    ```

2. Navigate to the project directory:

    ```bash
    cd iot2mqtt
    ```

3. (Optional) Create and activate a virtual environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

4. Install the required dependencies:

    ```bash
    sudo pip3 install -r requirements.txt
    ```

## Test installation

To verify that the installation was successful, you can use the `cli_iot2mqtt` command. This command will help you ensure that everything is set up correctly.

1. Open your terminal.
2. Run the following command:

   ```sh
   cli_iot2mqtt
   ````

You should see output similar to the screenshot below, indicating that the command is working as expected.

![cli_iot2mqtt](https://slassabe.github.io/iot2mqtt/_images/cli_iot2mqtt.png)

## Related projects

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) : Eclipse Paho™ MQTT Python Client
- [miflora-mqtt-daemon](https://github.com/ThomDietrich/miflora-mqtt-daemon) : Xiaomi Mi Flora Plant Sensor MQTT Client/Daemon
- [ring-mqtt](https://github.com/tsightler/ring-mqtt) : Ring devices to MQTT Bridge
- [zigbee2mqtt](https://github.com/Koenkk/zigbee2mqtt) : Allows you to use your Zigbee devices without the vendor's bridge or gateway.