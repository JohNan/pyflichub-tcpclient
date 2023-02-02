import asyncio
import json
import logging
import time
from functools import partial, wraps
from typing import Union

import async_timeout
import humps

from pyflichub.command import Command
from pyflichub.event import Event
from pyflichub.button import FlicButton

_LOGGER = logging.getLogger(__name__)

DATA_READY_TIMEOUT = 10.0


def wrap(func):
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)

    return run


class FlicHubTcpClient(asyncio.Protocol):
    buttons: [FlicButton]

    def __init__(self, ip, port, loop, timeout=1.0, reconnect_timeout=10.0, event_callback=None, command_callback=None):
        self._data_ready: Union[asyncio.Event, None] = None
        self._transport = None
        self._command_callback = command_callback
        self._event_callback = event_callback
        self._loop = loop or asyncio.get_event_loop()
        self._server_address = (ip, port)
        self._tcp_check_timer = time.time()
        self._tcp_disconnect_timer = time.time()
        self._reconnect_timeout = reconnect_timeout
        self._timeout = timeout
        self._data = None
        self.on_connected = None
        self.on_disconnected = None

    async def async_connect(self):
        """Connect to the socket."""
        try:
            while True:
                _LOGGER.info("Trying to connect to %s", self._server_address)
                try:
                    await asyncio.wait_for(
                        self._loop.create_connection(lambda: self, *self._server_address),
                        self._reconnect_timeout
                    )
                    self._tcp_check_timer = time.time()
                    self._tcp_disconnect_timer = time.time()
                    self._check_connection()
                    return
                except asyncio.TimeoutError:
                    _LOGGER.error("Connecting to socket timed out for %s", self._server_address)
                    _LOGGER.info("Waiting %s secs before trying to connect again", self._reconnect_timeout)
                    await asyncio.sleep(self._reconnect_timeout, loop=self._loop)
                except OSError:
                    _LOGGER.error("Failed to connect to socket at %s", self._server_address)
                    _LOGGER.info("Waiting %s secs before trying to connect again", self._reconnect_timeout)
                    await asyncio.sleep(self._reconnect_timeout)
        except asyncio.CancelledError:
            _LOGGER.debug("Connect attempt to %s cancelled", self._server_address)

    def disconnect(self):
        if self._transport is not None:
            self._transport.close()

        if self.on_disconnected is not None:
            self.on_disconnected()

    async def connect(self):
        await self._loop.create_connection(lambda: self, *self._server_address)

    async def get_buttons(self):
        return await self._async_send_command('buttons')

    async def get_battery_status(self, bdaddr: str):
        return await self._async_send_command(f'battery;{bdaddr}')

    async def _async_send_command(self, cmd: str):
        if self._transport is not None:
            self._data_ready = asyncio.Event()
            self._transport.write(cmd.encode())
            with async_timeout.timeout(DATA_READY_TIMEOUT):
                await self._data_ready.wait()
                self._data_ready = None
                return self._data
        else:
            _LOGGER.error("Connections seems to be closed.")

    def connection_made(self, transport):
        self._transport = transport
        _LOGGER.debug("Connection made")

        if self.on_connected is not None:
            self.on_connected()

    def data_received(self, data):
        _LOGGER.debug('Data received: {!r}'.format(data.decode()))

        if data.decode() == 'pong':
            return

        msg = json.loads(data.decode())
        if 'event' in msg:
            self._handle_event(Event(**msg))
        if 'command' in msg:
            self._handle_command(Command(**msg))

    def connection_lost(self, exc):
        _LOGGER.info("Connection lost")
        self._transport = None
        self._loop.create_task(self.async_connect())

    def _handle_command(self, cmd: Command):
        command_data = cmd.data
        if cmd.command == 'buttons':
            self.buttons = [FlicButton(**button) for button in humps.decamelize(cmd.data)]
            command_data = self.buttons
            for button in self.buttons:
                _LOGGER.debug(f"Button name: {button.name} - Connected: {button.connected}")

        if self._data_ready is not None:
            self._data_ready.set()
            self._data = command_data

        if self._command_callback is not None:
            self._command_callback(cmd)

    def _handle_event(self, event: Event):
        if event.event == 'button':
            button = self._get_button(event.button)
            _LOGGER.debug(f"Button {button.name} was {event.action}")

            if self._event_callback is not None:
                self._event_callback(button, event)

    def _get_button(self, bdaddr: str) -> FlicButton:
        return next((x for x in self.buttons if x.bdaddr == bdaddr), None)

    def _check_connection(self):
        """Check if connection is alive every reconnect_timeout seconds."""
        if (self._tcp_disconnect_timer + 2 * self._reconnect_timeout) < time.time():
            self._tcp_disconnect_timer = time.time()
            raise OSError(f"No response from {self._server_address}. Disconnecting")
        if (self._tcp_check_timer + self._reconnect_timeout) >= time.time():
            return

        msg = ""
        self._transport.write(msg.encode())
        self._tcp_check_timer = time.time()
