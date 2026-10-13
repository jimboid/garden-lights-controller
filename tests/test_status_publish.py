"""Tests for periodic_status_publish(). threading.Timer is mocked so no
real background thread or wait is involved.
"""
from unittest.mock import MagicMock, patch


def test_periodic_status_publish_does_nothing_when_interval_is_zero(garden_lights_controller):
    with patch.object(garden_lights_controller, "publish_all_states") as publish_all_states, \
         patch.object(garden_lights_controller.threading, "Timer") as timer_cls:
        garden_lights_controller.periodic_status_publish(0)

    publish_all_states.assert_not_called()
    timer_cls.assert_not_called()


def test_periodic_status_publish_does_nothing_when_interval_is_negative(garden_lights_controller):
    with patch.object(garden_lights_controller, "publish_all_states") as publish_all_states, \
         patch.object(garden_lights_controller.threading, "Timer") as timer_cls:
        garden_lights_controller.periodic_status_publish(-5)

    publish_all_states.assert_not_called()
    timer_cls.assert_not_called()


def test_periodic_status_publish_publishes_now_and_schedules_next_run(garden_lights_controller):
    with patch.object(garden_lights_controller, "publish_all_states") as publish_all_states, \
         patch.object(garden_lights_controller.threading, "Timer") as timer_cls:
        timer_instance = MagicMock()
        timer_cls.return_value = timer_instance

        garden_lights_controller.periodic_status_publish(60)

    publish_all_states.assert_called_once()
    timer_cls.assert_called_once_with(60, garden_lights_controller.periodic_status_publish, args=(60,))
    assert timer_instance.daemon is True
    timer_instance.start.assert_called_once()
