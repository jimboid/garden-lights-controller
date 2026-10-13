"""Tests for on_connect() and on_message(). A fake message object stands in
for paho-mqtt's MQTTMessage, and client is always a MagicMock - no real
broker connection is made anywhere in this file.
"""
from unittest.mock import MagicMock


class FakeMessage:
    """Minimal stand-in for paho.mqtt.client.MQTTMessage."""

    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload.encode("utf-8")


def _topics_subscribed(mock_client):
    return [call.args[0] for call in mock_client.subscribe.call_args_list]


def _topics_published(mock_client):
    topics = []
    for call in mock_client.publish.call_args_list:
        if call.args:
            topics.append(call.args[0])
        else:
            topics.append(call.kwargs.get("topic"))
    return topics


def test_on_connect_publishes_discovery_subscribes_to_each_light_and_status(garden_lights_controller, sample_lights):
    garden_lights_controller.LIGHTS = sample_lights
    mock_client = MagicMock()
    garden_lights_controller.client = mock_client

    garden_lights_controller.on_connect(mock_client, None, None, 0)

    subscribed = _topics_subscribed(mock_client)
    assert "homeassistant/light/testfence/#" in subscribed
    assert "homeassistant/light/testspot/#" in subscribed
    assert "homeassistant/status" in subscribed

    published = _topics_published(mock_client)
    assert "homeassistant/light/testfence/config" in published
    assert "homeassistant/light/testspot/config" in published
    assert "homeassistant/light/testfence/state" in published
    assert "homeassistant/light/testspot/state" in published


def test_on_message_status_online_republishes_discovery_and_all_states(garden_lights_controller, sample_lights, monkeypatch):
    garden_lights_controller.LIGHTS = sample_lights
    garden_lights_controller.client = MagicMock()

    calls = []
    monkeypatch.setattr(garden_lights_controller, "publish_discovery", lambda light_id: calls.append(("discovery", light_id)))
    monkeypatch.setattr(garden_lights_controller, "publish_all_states", lambda: calls.append(("all_states",)))

    msg = FakeMessage("homeassistant/status", "online")
    garden_lights_controller.on_message(garden_lights_controller.client, None, msg)

    assert ("discovery", "testfence") in calls
    assert ("discovery", "testspot") in calls
    assert ("all_states",) in calls


def test_on_message_status_offline_does_not_republish_anything(garden_lights_controller, sample_lights, monkeypatch):
    garden_lights_controller.LIGHTS = sample_lights
    garden_lights_controller.client = MagicMock()

    calls = []
    monkeypatch.setattr(garden_lights_controller, "publish_discovery", lambda light_id: calls.append(light_id))
    monkeypatch.setattr(garden_lights_controller, "publish_all_states", lambda: calls.append("all_states"))

    msg = FakeMessage("homeassistant/status", "offline")
    garden_lights_controller.on_message(garden_lights_controller.client, None, msg)

    assert calls == []


def test_on_message_on_payload_delegates_to_set_light(garden_lights_controller, sample_lights, monkeypatch):
    garden_lights_controller.LIGHTS = sample_lights
    calls = []
    monkeypatch.setattr(garden_lights_controller, "set_light", lambda light_id, state: calls.append((light_id, state)))

    msg = FakeMessage("homeassistant/light/testfence", "ON")
    garden_lights_controller.on_message(garden_lights_controller.client, None, msg)

    assert calls == [("testfence", "ON")]


def test_on_message_off_payload_delegates_to_set_light(garden_lights_controller, sample_lights, monkeypatch):
    garden_lights_controller.LIGHTS = sample_lights
    calls = []
    monkeypatch.setattr(garden_lights_controller, "set_light", lambda light_id, state: calls.append((light_id, state)))

    msg = FakeMessage("homeassistant/light/testspot", "OFF")
    garden_lights_controller.on_message(garden_lights_controller.client, None, msg)

    assert calls == [("testspot", "OFF")]


def test_on_message_ignores_topic_for_unknown_light(garden_lights_controller, sample_lights, monkeypatch):
    garden_lights_controller.LIGHTS = sample_lights
    calls = []
    monkeypatch.setattr(garden_lights_controller, "set_light", lambda *args: calls.append(args))

    msg = FakeMessage("homeassistant/light/doesnotexist", "ON")
    garden_lights_controller.on_message(garden_lights_controller.client, None, msg)

    assert calls == []


def test_on_message_ignores_unrecognised_payload(garden_lights_controller, sample_lights, monkeypatch):
    garden_lights_controller.LIGHTS = sample_lights
    calls = []
    monkeypatch.setattr(garden_lights_controller, "set_light", lambda *args: calls.append(args))

    msg = FakeMessage("homeassistant/light/testfence", "TOGGLE")
    garden_lights_controller.on_message(garden_lights_controller.client, None, msg)

    assert calls == []
