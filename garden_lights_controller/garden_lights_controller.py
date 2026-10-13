#!/usr/bin/env python3
import argparse
import json
import os
import signal
import threading

import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import yaml

# Default path to the YAML config file, used only if --config is not passed
# on the command line. Falls back to $MQTT_LIGHTS_CONFIG, then to
# lights_config.yaml next to this script.
DEFAULT_CONFIG_PATH = os.environ.get(
    "MQTT_LIGHTS_CONFIG",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "lights_config.yaml"),
)

# Populated in main() once the config file has been loaded and parsed;
# referenced as module globals by the callbacks and helpers below.
CONFIG = None
MQTT_CONFIG = None
STATUS_INTERVAL = 0
LIGHTS = {}
client = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="MQTT bridge for garden lights on Raspberry Pi GPIO, "
                     "with Home Assistant MQTT discovery."
    )
    parser.add_argument(
        "-c", "--config",
        default=DEFAULT_CONFIG_PATH,
        help="Path to the YAML config file "
             "(default: %(default)s, or $MQTT_LIGHTS_CONFIG if set).",
    )
    return parser.parse_args()


def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def lights_init():
    """Set up all configured pins as outputs, initially off."""
    for light in LIGHTS.values():
        for pin in light["pins"]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)


def set_light(light_id, state):
    """Drive the GPIO pins for a light group and publish its new state."""
    light = LIGHTS[light_id]
    gpio_state = GPIO.HIGH if state == "ON" else GPIO.LOW

    for pin in light["pins"]:
        GPIO.output(pin, gpio_state)

    light["state"] = state

    # retain=True so that Home Assistant (or anything else) subscribing
    # after this point immediately gets the last known state, instead of
    # showing "unknown" until the light is next toggled.
    client.publish(
        f"homeassistant/light/{light_id}/state",
        state,
        qos=0,
        retain=True,
    )


def publish_discovery(light_id):
    """(Re-)publish the MQTT discovery config for a single light group."""
    light = LIGHTS[light_id]
    client.publish(
        topic=f"homeassistant/light/{light_id}/config",
        payload=json.dumps({
            "name": light["name"],
            "unique_id": light["name"],
            "device": {
                "identifiers": ["Garden Lights"],
                "name": "Garden Lights",
                "model": "RPI",
                "manufacturer": "Jimboid",
            },
            "command_topic": f"homeassistant/light/{light_id}",
            "state_topic": f"homeassistant/light/{light_id}/state",
            "icon": "mdi:lightbulb",
        }),
        qos=0,
        retain=True,
    )


def publish_all_states():
    """Re-publish the current (retained) state of every light."""
    for light_id, light in LIGHTS.items():
        client.publish(
            f"homeassistant/light/{light_id}/state",
            light["state"],
            qos=0,
            retain=True,
        )


def periodic_status_publish(interval):
    """Re-publish all light states every `interval` seconds in the
    background, so Home Assistant self-heals even if it misses a birth
    message or a retained message gets lost. No-op if interval <= 0."""
    if interval <= 0:
        return
    publish_all_states()
    timer = threading.Timer(interval, periodic_status_publish, args=(interval,))
    timer.daemon = True
    timer.start()


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    for light_id in LIGHTS:
        publish_discovery(light_id)
        client.subscribe(f"homeassistant/light/{light_id}/#")

    # Home Assistant publishes "online" to this topic on startup/restart
    # (and "offline" on clean shutdown). Subscribing lets us re-announce our
    # current state as soon as HA comes back, instead of it showing
    # "unknown" until a light is next toggled.
    client.subscribe("homeassistant/status")

    publish_all_states()


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):

    # Get the payload and topic.
    payload = str(msg.payload.decode("utf-8"))
    topic = msg.topic

    if topic == "homeassistant/status":
        if payload == "online":
            print("Home Assistant came online, re-publishing state")
            for light_id in LIGHTS:
                publish_discovery(light_id)
            publish_all_states()
        return

    for light_id in LIGHTS:
        if topic == f"homeassistant/light/{light_id}" and payload in ("ON", "OFF"):
            set_light(light_id, payload)
            break


def _handle_sigterm(signum, frame):
    # systemd's default stop signal is SIGTERM, which Python does not turn
    # into a KeyboardInterrupt on its own. Without this, `systemctl stop` /
    # `restart` would bypass the except block below and skip GPIO.cleanup().
    raise SystemExit(0)


def main():
    global CONFIG, MQTT_CONFIG, STATUS_INTERVAL, LIGHTS, client

    args = parse_args()
    CONFIG = load_config(args.config)
    MQTT_CONFIG = CONFIG["mqtt"]
    STATUS_INTERVAL = CONFIG.get("status_publish_interval_seconds", 0)
    LIGHTS = {
        light["id"]: {
            "name": light["name"],
            "pins": light["pins"],
            "state": "OFF",
        }
        for light in CONFIG["lights"]
    }

    signal.signal(signal.SIGTERM, _handle_sigterm)

    # We are using BCM numbering scheme for pins.
    GPIO.setmode(GPIO.BCM)

    try:
        # Initialise lights.
        lights_init()

        # MQTT connect and listen.
        client = mqtt.Client(MQTT_CONFIG.get("client_id", "gardenlights"))
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(
            username=MQTT_CONFIG["username"],
            password=MQTT_CONFIG["password"],
        )
        client.connect(MQTT_CONFIG["broker"], MQTT_CONFIG.get("port", 1883), 60)

        # Start the periodic status re-publish (runs in its own thread, safe
        # to call alongside loop_forever()).
        periodic_status_publish(STATUS_INTERVAL)

        client.loop_forever()

    except (KeyboardInterrupt, SystemExit):
        GPIO.cleanup()


if __name__ == "__main__":
    main()
