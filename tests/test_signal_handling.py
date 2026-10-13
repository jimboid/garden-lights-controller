"""Tests for _handle_sigterm() - the handler that makes `systemctl stop` /
`restart` trigger the same clean-shutdown (GPIO.cleanup()) path as Ctrl-C.
"""
import pytest


def test_handle_sigterm_raises_system_exit_zero(garden_lights_controller):
    with pytest.raises(SystemExit) as exc_info:
        garden_lights_controller._handle_sigterm(15, None)

    assert exc_info.value.code == 0
