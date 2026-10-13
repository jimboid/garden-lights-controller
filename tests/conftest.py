"""
Shared pytest fixtures for testing garden_lights_controller.py.

RPi.GPIO only exists on real Raspberry Pi hardware, so it's stubbed out in
sys.modules here (module import time, before any test file is collected)
using MagicMock. If RPi.GPIO genuinely is installed (e.g. running the suite
on a real Pi), we leave it alone (sys.modules.setdefault) rather than
overriding it.

No test in this suite talks to a real MQTT broker: every place the code
would call out to paho-mqtt, tests substitute a MagicMock and assert on how
it was called instead.
"""
import copy
import importlib
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

# Make sure the project root (which contains the garden_lights_controller
# package) is importable regardless of whether the project has been
# `pip install`-ed.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))


def _build_gpio_stub():
    gpio_stub = MagicMock(name="RPi.GPIO")
    # Give the pin-mode/state constants distinct, recognisable values so
    # tests can assert exactly what was passed to GPIO.setup()/output(),
    # the same way the real RPi.GPIO module exposes them as constants.
    gpio_stub.BCM = "BCM"
    gpio_stub.OUT = "OUT"
    gpio_stub.HIGH = "HIGH"
    gpio_stub.LOW = "LOW"
    return gpio_stub


_gpio_stub = _build_gpio_stub()
_rpi_stub = types.ModuleType("RPi")
_rpi_stub.GPIO = _gpio_stub

sys.modules.setdefault("RPi", _rpi_stub)
sys.modules.setdefault("RPi.GPIO", _gpio_stub)


@pytest.fixture
def gpio_stub():
    """The (stubbed, or real if running on a Pi) RPi.GPIO module, with its
    call history cleared before each test."""
    import RPi.GPIO as GPIO
    reset = getattr(GPIO, "reset_mock", None)
    if reset:
        reset()
    return GPIO


@pytest.fixture
def garden_lights_controller(gpio_stub):
    """Import garden_lights_controller fresh for each test and reset its mutable
    module-level state (CONFIG, LIGHTS, client, etc.), so state set up or
    mutated by one test can't leak into another."""
    import garden_lights_controller.garden_lights_controller as module
    importlib.reload(module)

    module.CONFIG = None
    module.MQTT_CONFIG = None
    module.STATUS_INTERVAL = 0
    module.LIGHTS = {}
    module.client = None

    return module


@pytest.fixture
def sample_lights():
    """A small, deterministic LIGHTS registry, independent of the real
    lights_config.yaml on disk."""
    return {
        "testfence": {"name": "test_fence_light", "pins": [1, 2], "state": "OFF"},
        "testspot": {"name": "test_spot_light", "pins": [3], "state": "OFF"},
    }


@pytest.fixture
def sample_config(sample_lights):
    """A parsed-YAML-shaped dict matching sample_lights, for tests that
    exercise config loading or main()."""
    return {
        "mqtt": {
            "broker": "broker.example",
            "port": 1883,
            "username": "user",
            "password": "pass",
            "client_id": "test-client",
        },
        "status_publish_interval_seconds": 45,
        "lights": [
            {"id": light_id, "name": light["name"], "pins": copy.deepcopy(light["pins"])}
            for light_id, light in sample_lights.items()
        ],
    }


@pytest.fixture
def config_path(tmp_path, sample_config):
    """Write sample_config out to a temp YAML file on disk and return its
    path, for tests that exercise --config / main() end to end."""
    import yaml

    path = tmp_path / "lights_config.yaml"
    path.write_text(yaml.dump(sample_config))
    return str(path)
