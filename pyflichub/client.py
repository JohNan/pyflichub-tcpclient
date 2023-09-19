import asyncio
import json
import logging
import time
from datetime import datetime
from functools import partial, wraps
from typing import Union

import async_timeout
import humps

from pyflichub.command import Command
from pyflichub.event import Event
from pyflichub.button import FlicButton
from pyflichub.flichub import FlicHubInfo

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
    buttons: [FlicButton] = []
    network: FlicHubInfo

    def __init__(self, ip, port, loop, timeout=1.0, reconnect_timeout=10.0, event_callback=None, command_callback=None):
        self._data_ready: Union[asyncio.Event, None] = None
        self._transport = None
        self._command_callback = command_callback
        self._event_callback = event_callback
        self._loop = loop
        self._server_address = (ip, port)
        self._tcp_check_timer = time.time()
        self._tcp_disconnect_timer = time.time()
        self._reconnect_timeout = reconnect_timeout
        self._timeout = timeout
        self._data = None
        self.on_connected = None
        self.on_disconnected = None
        self._connecting = False

    async def async_connect(self):
        self._connecting = True
        """Connect to the socket."""
        try:
            while self._connecting:
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
                    await asyncio.sleep(self._reconnect_timeout)
                except OSError:
                    _LOGGER.error("Failed to connect to socket at %s", self._server_address)
                    _LOGGER.info("Waiting %s secs before trying to connect again", self._reconnect_timeout)
                    await asyncio.sleep(self._reconnect_timeout)
        except asyncio.CancelledError:
            _LOGGER.debug("Connect attempt to %s cancelled", self._server_address)

    def disconnect(self):
        _LOGGER.info("Disconnected")
        self._connecting = False

        if self._transport is not None:
            self._transport.close()

        if self.on_disconnected is not None:
            self.on_disconnected()

    async def connect(self):
        await self._loop.create_connection(lambda: self, *self._server_address)

    async def get_buttons(self):
        return await self._async_send_command('buttons')

    async def get_hubinfo(self):
        return await self._async_send_command('network')

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
        decoded_data = data.decode()
        _LOGGER.debug('Data received: {!r}'.format(decoded_data))
        for data_part in [data_part for data_part in decoded_data.split("\n") if data_part.strip()]:
            if data_part == 'pong':
                pass

            try:
                msg = json.loads(data_part, cls=_JSONDecoder)
                if 'event' in msg:
                    self._handle_event(Event(**msg))
                if 'command' in msg:
                    self._handle_command(Command(**msg))
            except Exception as e:
                _LOGGER.warning(e, exc_info = True)
                _LOGGER.warning('Unable to decode received data')


    def connection_lost(self, exc):
        _LOGGER.info("Connection lost")
        self._transport = None
        self._loop.create_task(self.async_connect())

    def _handle_command(self, cmd: Command):
        command_data = cmd.data
        if cmd.command == 'buttons':
            self.buttons = [FlicButton(**button) for button in humps.decamelize(cmd.data)]
            command_data = cmd.data = self.buttons
            for button in self.buttons:
                _LOGGER.debug(f"Button name: {button.name} - Connected: {button.connected}")
        if cmd.command == 'network':
            self.network = FlicHubInfo(**humps.decamelize(cmd.data))
            command_data = cmd.data = self.network
            if self.network.has_wifi():
                _LOGGER.debug(f"Wifi State: {self.network.wifi.state} - Connected: {self.network.wifi.connected}")
            if self.network.has_ethernet():
                _LOGGER.debug(f"Ethernet IP: {self.network.ethernet.ip} - Connected: {self.network.ethernet.connected}")

        if self._data_ready is not None:
            self._data_ready.set()
            self._data = command_data

        if self._command_callback is not None:
            self._command_callback(cmd)

    def _handle_event(self, event: Event):
        button = None
        if event.event == 'button':
            button = self._get_button(event.button)
            _LOGGER.debug(f"Button {button.name} was {event.action}")

        if self._event_callback is not None and button is not None:
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

class _JSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(
            self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        ret = {}
        for key, value in obj.items():
            if key in {'batteryTimestamp'}:
                ret[key] = datetime.fromtimestamp(value/1000)
            else:
                ret[key] = value
        return ret