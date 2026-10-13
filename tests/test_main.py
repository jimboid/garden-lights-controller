"""Integration-style tests for main(): CLI parsing, wiring up the mqtt
client, and the shutdown path. mqtt.Client and RPi.GPIO are both mocked so
nothing here touches a real broker or real hardware.
"""
import sys
from unittest.mock import MagicMock


def _mock_forever_client(monkeypatch, garden_lights_controller):
    """A fake paho-mqtt client whose loop_forever() raises immediately,
    standing in for Ctrl-C / SIGTERM so main() doesn't actually block."""
    fake_client = MagicMock()
    fake_client.loop_forever.side_effect = KeyboardInterrupt
    monkeypatch.setattr(garden_lights_controller.mqtt, "Client", MagicMock(return_value=fake_client))
    return fake_client


def test_main_loads_config_from_cli_arg_and_wires_up_the_client(
    garden_lights_controller, config_path, sample_config, monkeypatch, gpio_stub
):
    monkeypatch.setattr(sys, "argv", ["mqtt-lights", "--config", config_path])
    fake_client = _mock_forever_client(monkeypatch, garden_lights_controller)
    monkeypatch.setattr(garden_lights_controller.threading, "Timer", MagicMock())

    garden_lights_controller.main()

    assert garden_lights_controller.CONFIG == sample_config
    assert set(garden_lights_controller.LIGHTS) == {"testfence", "testspot"}

    garden_lights_controller.mqtt.Client.assert_called_once_with("test-client")
    assert fake_client.on_connect is garden_lights_controller.on_connect
    assert fake_client.on_message is garden_lights_controller.on_message
    fake_client.username_pw_set.assert_called_once_with(username="user", password="pass")
    fake_client.connect.assert_called_once_with("broker.example", 1883, 60)
    fake_client.loop_forever.assert_called_once()

    gpio_stub.setmode.assert_called_once_with(gpio_stub.BCM)


def test_main_cleans_up_gpio_when_loop_forever_is_interrupted(
    garden_lights_controller, config_path, monkeypatch, gpio_stub
):
    monkeypatch.setattr(sys, "argv", ["mqtt-lights", "--config", config_path])
    _mock_forever_client(monkeypatch, garden_lights_controller)
    monkeypatch.setattr(garden_lights_controller.threading, "Timer", MagicMock())

    garden_lights_controller.main()

    # loop_forever() raised KeyboardInterrupt; main() should have caught it
    # and cleaned up the GPIO pins rather than letting it propagate.
    gpio_stub.cleanup.assert_called_once()


def test_main_registers_a_sigterm_handler_for_clean_systemd_shutdowns(
    garden_lights_controller, config_path, monkeypatch
):
    monkeypatch.setattr(sys, "argv", ["mqtt-lights", "--config", config_path])
    _mock_forever_client(monkeypatch, garden_lights_controller)
    monkeypatch.setattr(garden_lights_controller.threading, "Timer", MagicMock())

    registered = {}
    monkeypatch.setattr(
        garden_lights_controller.signal,
        "signal",
        lambda signum, handler: registered.__setitem__(signum, handler),
    )

    garden_lights_controller.main()

    assert registered.get(garden_lights_controller.signal.SIGTERM) is garden_lights_controller._handle_sigterm


def test_main_starts_periodic_status_publish_with_the_configured_interval(
    garden_lights_controller, config_path, sample_config, monkeypatch
):
    monkeypatch.setattr(sys, "argv", ["mqtt-lights", "--config", config_path])
    _mock_forever_client(monkeypatch, garden_lights_controller)

    timer_cls = MagicMock()
    monkeypatch.setattr(garden_lights_controller.threading, "Timer", timer_cls)

    garden_lights_controller.main()

    interval = sample_config["status_publish_interval_seconds"]
    timer_cls.assert_called_once_with(
        interval, garden_lights_controller.periodic_status_publish, args=(interval,)
    )
