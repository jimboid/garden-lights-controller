"""Tests for load_config() and parse_args()."""
import sys
import textwrap

import pytest


def _write_yaml(tmp_path, text):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(textwrap.dedent(text))
    return str(config_file)


def test_load_config_reads_yaml_into_a_dict(garden_lights_controller, tmp_path):
    path = _write_yaml(tmp_path, """\
        mqtt:
          broker: 10.0.0.5
          port: 1883
          username: u
          password: p
          client_id: cid
        status_publish_interval_seconds: 42
        lights:
          - id: a
            name: light_a
            pins: [1]
    """)

    config = garden_lights_controller.load_config(path)

    assert config["mqtt"]["broker"] == "10.0.0.5"
    assert config["mqtt"]["port"] == 1883
    assert config["status_publish_interval_seconds"] == 42
    assert config["lights"] == [{"id": "a", "name": "light_a", "pins": [1]}]


def test_load_config_missing_file_raises_file_not_found(garden_lights_controller, tmp_path):
    missing_path = str(tmp_path / "does-not-exist.yaml")

    with pytest.raises(FileNotFoundError):
        garden_lights_controller.load_config(missing_path)


def test_parse_args_defaults_to_default_config_path_when_no_flag_given(garden_lights_controller, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mqtt-lights"])

    args = garden_lights_controller.parse_args()

    assert args.config == garden_lights_controller.DEFAULT_CONFIG_PATH


def test_parse_args_accepts_long_config_flag(garden_lights_controller, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mqtt-lights", "--config", "/tmp/custom.yaml"])

    args = garden_lights_controller.parse_args()

    assert args.config == "/tmp/custom.yaml"


def test_parse_args_accepts_short_config_flag(garden_lights_controller, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mqtt-lights", "-c", "/tmp/custom2.yaml"])

    args = garden_lights_controller.parse_args()

    assert args.config == "/tmp/custom2.yaml"
