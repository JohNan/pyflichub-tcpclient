import asyncio
import json
import logging
import time
from datetime import datetime
from functools import partial, wraps
from typing import Union

import async_timeout
import humps

from pyflichub.button import FlicButton
from pyflichub.command import Command
from pyflichub.event import Event
from pyflichub.flichub import FlicHubInfo
from pyflichub.server_command import ServerCommand
from pyflichub.server_info import ServerInfo
from pyflichub.updater import check_for_updates, UPDATE_LINK

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
    buttons: list[FlicButton] = []
    network: FlicHubInfo

    def __init__(self, ip, port, loop, timeout=1.0, reconnect_timeout=10.0, event_callback=None, command_callback=None):
        self._data_ready: dict[str: Union[asyncio.Event, None]] = {}
        self._transport = None
        self._command_callback = command_callback
        self._event_callback = event_callback
        self._loop = loop
        self._server_address = (ip, port)
        self._tcp_check_timer = time.time()
        self._tcp_disconnect_timer = time.time()
        self._reconnect_timeout = reconnect_timeout
        self._timeout = timeout
        self._data: dict = {}
        self._buffer = b""
        self._connecting = False
        self._forced_disconnect = False
        self.async_on_connected = None
        self.async_on_disconnected = None

    async def _async_connect(self):
        """Connect to the socket."""
        try:
            while self._connecting and not self._forced_disconnect:
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
        self._forced_disconnect = True

        if self._transport is not None:
            self._transport.close()

        if self.async_on_disconnected is not None:
            self._loop.create_task(self.async_on_disconnected())

    async def async_connect(self):
        self._connecting = True
        self._forced_disconnect = False
        await self._async_connect()

    def send_command(self, cmd: ServerCommand):
        return self._async_send_command(cmd)

    def send_virtual_device_update_state(self, dimmable_type: str, virtual_device_id: str, values: dict):
        payload = json.dumps({
            "command": "virtualDeviceUpdateState",
            "dimmableType": dimmable_type,
            "virtualDeviceId": virtual_device_id,
            "values": values
        })
        if self._transport is not None:
            self._transport.write(f"{payload}\n".encode())
        else:
            _LOGGER.error("Connections seems to be closed.")

    async def get_buttons(self) -> list[FlicButton]:
        command: Command = await self._async_send_command_and_wait_for_data(ServerCommand.BUTTONS)
        return command.data if command is not None else []

    async def get_server_info(self) -> ServerInfo | None:
        command: Command = await self._async_send_command_and_wait_for_data(ServerCommand.SERVER_INFO)
        return command.data

    async def get_hubinfo(self) -> FlicHubInfo | None:
        command: Command = await self._async_send_command_and_wait_for_data(ServerCommand.HUB_INFO)
        return command.data

    async def async_check_for_updates(self):
        try:
            # Check library version
            from .version import __version__
        except ImportError:
            __version__ = "0.0.0"

        update_available, latest_version = await self._loop.run_in_executor(None, check_for_updates, __version__)
        if update_available:
            print(f"A new version of pyflichub-tcpclient is available: {latest_version} (current: {__version__})")
            print(f"Please update the library and the code in your Flic Hub: {UPDATE_LINK}")
            return

        # Check Hub version
        server_info = await self.get_server_info()
        if server_info and server_info.version:
            update_available, latest_version = await self._loop.run_in_executor(None, check_for_updates, server_info.version)
            if update_available:
                print(f"A new version of the Flic Hub script is available: {latest_version} (current: {server_info.version})")
                print(f"Please update the code in your Flic Hub: {UPDATE_LINK}")

    def _async_send_command(self, cmd: ServerCommand):
        if self._transport is not None:
            self._transport.write(f"{cmd}\n".encode())
        else:
            _LOGGER.error("Connections seems to be closed.")

    async def _async_send_command_and_wait_for_data(self, cmd: ServerCommand) -> Command | None:
        if self._transport is not None:
            self._data_ready[cmd] = asyncio.Event()
            self._transport.write(f"{cmd}\n".encode())
            try:
                with async_timeout.timeout(DATA_READY_TIMEOUT):
                    await self._data_ready[cmd].wait()
                    self._data_ready[cmd] = None
                    return self._data[cmd]
            except asyncio.TimeoutError:
                _LOGGER.warning(f"Waited for '{cmd}' data for {DATA_READY_TIMEOUT} secs.")
                return None
        else:
            _LOGGER.error("Connections seems to be closed.")

    def connection_made(self, transport):
        self._transport = transport
        _LOGGER.debug("Connection made")

        if self.async_on_connected is not None:
            self._loop.create_task(self.async_on_connected())

    def data_received(self, data):
        self._buffer += data
               
        _LOGGER.debug('Data received: {!r}'.format(data.decode('utf-8', errors='replace')))

        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            decoded_line = line.decode().strip()
            if not decoded_line:
                continue

            if decoded_line == 'pong':
                pass

            try:
                msg = json.loads(decoded_line, cls=_JSONDecoder)
                if 'event' in msg:
                    self._handle_event(Event(**msg))
                if 'command' in msg:
                    self._handle_command(Command(**msg))
            except Exception as e:
                _LOGGER.warning(e, exc_info=True)
                _LOGGER.warning('Unable to decode received data')

    def connection_lost(self, exc):
        _LOGGER.info("Connection lost")
        self._connecting = True
        self._transport = None
        self._loop.create_task(self._async_connect())

    def _handle_command(self, cmd: Command):
        if cmd.command == ServerCommand.SERVER_INFO:
            cmd.data = ServerInfo(**humps.decamelize(cmd.data))
        elif cmd.command == ServerCommand.BUTTONS:
            self.buttons = [FlicButton(**button) for button in humps.decamelize(cmd.data)]
            cmd.data = self.buttons
        elif cmd.command == ServerCommand.HUB_INFO:
            cmd.data = FlicHubInfo(**humps.decamelize(cmd.data))

        if self._data_ready[cmd.command] is not None and cmd.data is not None:
            self._data_ready[cmd.command].set()
            self._data[cmd.command] = cmd

        if self._command_callback is not None:
            self._command_callback(cmd)

    def _handle_event(self, event: Event):
        button = None
        if event.event == 'button':
            button = self._get_button(event.button)
            if button:
                _LOGGER.debug(f"Button {button.name} was {event.action}")

        elif event.event == 'buttonConnected':
            button = self._get_button(event.button)
            if button:
                _LOGGER.debug(f"Button {button.name} is connected")

        elif event.event == 'buttonReady':
            button = self._get_button(event.button)
            if button:
                _LOGGER.debug(f"Button {button.name} is ready")

        elif event.event == 'actionMessage':
            _LOGGER.debug(f"Action message received: {event.action}")

        elif event.event == 'virtualDeviceUpdate':
            if event.meta_data and 'virtual_device_id' in event.meta_data:
                _LOGGER.debug(f"Virtual device update received: {event.meta_data['virtual_device_id']}")

        if self._event_callback is not None:
            if event.event in ['actionMessage', 'virtualDeviceUpdate']:
                self._event_callback(button, event)
            elif button is not None:
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
                ret[key] = datetime.fromtimestamp(value / 1000)
            else:
                ret[key] = value
        return ret
