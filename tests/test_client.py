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
