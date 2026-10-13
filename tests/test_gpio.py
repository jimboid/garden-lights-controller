"""Tests for lights_init() and set_light() - the functions that actually
drive GPIO pins. No real hardware involved; RPi.GPIO is stubbed in conftest.
"""
from unittest.mock import MagicMock


def test_lights_init_configures_every_pin_as_output_and_sets_it_low(garden_lights_controller, sample_lights, gpio_stub):
    garden_lights_controller.LIGHTS = sample_lights

    garden_lights_controller.lights_init()

    all_pins = [pin for light in sample_lights.values() for pin in light["pins"]]
    assert gpio_stub.setup.call_count == len(all_pins)
    for pin in all_pins:
        gpio_stub.setup.assert_any_call(pin, gpio_stub.OUT)
        gpio_stub.output.assert_any_call(pin, gpio_stub.LOW)


def test_set_light_on_drives_pins_high_updates_state_and_publishes_retained(garden_lights_controller, sample_lights, gpio_stub):
    garden_lights_controller.LIGHTS = sample_lights
    garden_lights_controller.client = MagicMock()

    garden_lights_controller.set_light("testfence", "ON")

    for pin in sample_lights["testfence"]["pins"]:
        gpio_stub.output.assert_any_call(pin, gpio_stub.HIGH)
    assert sample_lights["testfence"]["state"] == "ON"
    garden_lights_controller.client.publish.assert_called_once_with(
        "homeassistant/light/testfence/state", "ON", qos=0, retain=True
    )


def test_set_light_off_drives_pins_low_updates_state_and_publishes_retained(garden_lights_controller, sample_lights, gpio_stub):
    garden_lights_controller.LIGHTS = sample_lights
    garden_lights_controller.client = MagicMock()

    garden_lights_controller.set_light("testspot", "OFF")

    for pin in sample_lights["testspot"]["pins"]:
        gpio_stub.output.assert_any_call(pin, gpio_stub.LOW)
    assert sample_lights["testspot"]["state"] == "OFF"
    garden_lights_controller.client.publish.assert_called_once_with(
        "homeassistant/light/testspot/state", "OFF", qos=0, retain=True
    )


def test_set_light_only_drives_pins_belonging_to_that_light(garden_lights_controller, sample_lights, gpio_stub):
    garden_lights_controller.LIGHTS = sample_lights
    garden_lights_controller.client = MagicMock()

    garden_lights_controller.set_light("testspot", "ON")

    driven_high = [call.args for call in gpio_stub.output.call_args_list if call.args[1] == gpio_stub.HIGH]
    driven_pins = {args[0] for args in driven_high}
    assert driven_pins == set(sample_lights["testspot"]["pins"])
    for pin in sample_lights["testfence"]["pins"]:
        assert pin not in driven_pins
