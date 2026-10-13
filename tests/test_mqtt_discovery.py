"""Tests for publish_discovery() and publish_all_states(). These build MQTT
payloads and hand them to client.publish() - client is always a MagicMock
here, so nothing touches a real broker.
"""
import json
from unittest.mock import MagicMock


def test_publish_discovery_sends_expected_ha_discovery_payload(garden_lights_controller, sample_lights):
    garden_lights_controller.LIGHTS = sample_lights
    garden_lights_controller.client = MagicMock()

    garden_lights_controller.publish_discovery("testfence")

    garden_lights_controller.client.publish.assert_called_once()
    _, kwargs = garden_lights_controller.client.publish.call_args
    assert kwargs["topic"] == "homeassistant/light/testfence/config"
    assert kwargs["qos"] == 0
    assert kwargs["retain"] is True

    payload = json.loads(kwargs["payload"])
    assert payload["name"] == "test_fence_light"
    assert payload["unique_id"] == "test_fence_light"
    assert payload["command_topic"] == "homeassistant/light/testfence"
    assert payload["state_topic"] == "homeassistant/light/testfence/state"
    assert payload["icon"] == "mdi:lightbulb"
    assert payload["device"]["identifiers"] == ["Garden Lights"]


def test_publish_discovery_uses_correct_topics_per_light(garden_lights_controller, sample_lights):
    garden_lights_controller.LIGHTS = sample_lights
    garden_lights_controller.client = MagicMock()

    garden_lights_controller.publish_discovery("testspot")

    _, kwargs = garden_lights_controller.client.publish.call_args
    assert kwargs["topic"] == "homeassistant/light/testspot/config"
    payload = json.loads(kwargs["payload"])
    assert payload["name"] == "test_spot_light"


def test_publish_all_states_publishes_current_state_of_every_light(garden_lights_controller, sample_lights):
    sample_lights["testfence"]["state"] = "ON"
    sample_lights["testspot"]["state"] = "OFF"
    garden_lights_controller.LIGHTS = sample_lights
    garden_lights_controller.client = MagicMock()

    garden_lights_controller.publish_all_states()

    assert garden_lights_controller.client.publish.call_count == len(sample_lights)
    garden_lights_controller.client.publish.assert_any_call(
        "homeassistant/light/testfence/state", "ON", qos=0, retain=True
    )
    garden_lights_controller.client.publish.assert_any_call(
        "homeassistant/light/testspot/state", "OFF", qos=0, retain=True
    )
