import asyncio
import json
import logging
import pytest
from pyflichub.client import FlicHubTcpClient
from pyflichub.command import Command
from pyflichub.event import Event

logging.basicConfig(level=logging.DEBUG)


class DummyClient(FlicHubTcpClient):
    def __init__(self):
        super().__init__('127.0.0.1', 8124, asyncio.new_event_loop())
        self.events_received = []
        self.commands_received = []

    def _handle_event(self, event: Event):
        self.events_received.append(event)

    def _handle_command(self, command: Command):
        self.commands_received.append(command)


def test_data_received_partial_data():
    client = DummyClient()
    client.data_received(b'{"event": "button", "button": "aa:bb:cc", "action": "click"}')
    assert len(client.events_received) == 0
    assert client._buffer == b'{"event": "button", "button": "aa:bb:cc", "action": "click"}'

    client.data_received(b'\n')
    assert len(client.events_received) == 1
    assert client.events_received[0].event == 'button'
    assert client.events_received[0].button == 'aa:bb:cc'
    assert client.events_received[0].action == 'click'
    assert client.events_received[0].button_number is None
    assert client._buffer == b""


def test_data_received_button_number():
    client = DummyClient()
    client.data_received(b'{"event": "button", "button": "aa:bb:cc", "action": "single", "button_number": 0}\n')
    assert len(client.events_received) == 1
    assert client.events_received[0].event == 'button'
    assert client.events_received[0].button == 'aa:bb:cc'
    assert client.events_received[0].action == 'single'
    assert client.events_received[0].button_number == 0
    assert client._buffer == b""


def test_data_received_multiple_messages():
    client = DummyClient()
    client.data_received(
        b'{"event": "button", "button": "aa:bb:cc", "action": "click"}\n{"command": "serverInfo", "data": {}}\n'
    )
    assert len(client.events_received) == 1
    assert len(client.commands_received) == 1
    assert client.events_received[0].event == 'button'
    assert client.commands_received[0].command == 'serverInfo'
    assert client._buffer == b""


def test_data_received_pong():
    client = DummyClient()
    client.data_received(b'pong\n')
    assert len(client.events_received) == 0
    assert len(client.commands_received) == 0
    assert client._buffer == b""

def test_button_events_handling():
    from pyflichub.button import FlicButton

    events_received = []

    def mock_event_callback(button, event):
        events_received.append((button, event))

    client = FlicHubTcpClient('127.0.0.1', 8124, asyncio.new_event_loop(), event_callback=mock_event_callback)

    # Mock get_buttons so it doesn't try to send over TCP
    async def mock_get_buttons():
        return []

    def mock_create_task(coro):
        coro.close() # prevent coroutine was never awaited warning

    client.get_buttons = mock_get_buttons
    client._loop.create_task = mock_create_task

    btn1 = FlicButton(bdaddr="aa:bb:cc", serial_number="sn", color="black", name="test1",
                      active_disconnect=False, connected=False, ready=False, battery_status=100,
                      uuid="uuid", flic_version=2, firmware_version=1, key="key", passive_mode=False)
    client.buttons = [btn1]

    # Test buttonAdded
    client.data_received(b'{"event": "buttonAdded", "button": "xx:yy:zz"}\n')
    assert len(events_received) == 1
    assert events_received[-1][0] is None  # Unknown button
    assert events_received[-1][1].event == "buttonAdded"

    # Test buttonConnected
    client.data_received(b'{"event": "buttonConnected", "button": "aa:bb:cc"}\n')
    assert client.buttons[0].connected is True
    assert events_received[-1][0] == btn1
    assert events_received[-1][1].event == "buttonConnected"

    # Test buttonReady
    client.data_received(b'{"event": "buttonReady", "button": "aa:bb:cc"}\n')
    assert client.buttons[0].ready is True
    assert events_received[-1][0] == btn1
    assert events_received[-1][1].event == "buttonReady"

    # Test buttonDisconnected
    client.data_received(b'{"event": "buttonDisconnected", "button": "aa:bb:cc"}\n')
    assert client.buttons[0].connected is False
    assert events_received[-1][0] == btn1
    assert events_received[-1][1].event == "buttonDisconnected"

    # Test buttonDeleted
    client.data_received(b'{"event": "buttonDeleted", "button": "aa:bb:cc"}\n')
    assert len(client.buttons) == 0
    assert events_received[-1][0] == btn1
    assert events_received[-1][1].event == "buttonDeleted"


def test_play_ir():
    from unittest.mock import MagicMock
    client = DummyClient()
    client._transport = MagicMock()
    client.play_ir("test_signal")

    expected_payload = json.dumps({
        "command": "play_ir",
        "signal_id": "test_signal"
    }) + "\n"

    client._transport.write.assert_called_once_with(expected_payload.encode())


def test_data_received_invalid_json():
    client = DummyClient()
    client.data_received(b'invalid json\n')
    assert len(client.events_received) == 0
    assert len(client.commands_received) == 0
    assert client._buffer == b""
