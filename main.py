import asyncio
from asyncio import AbstractEventLoop

import async_timeout
import logging

from pyflichub.button import FlicButton
from pyflichub.client import FlicHubTcpClient
from pyflichub.command import Command
from pyflichub.event import Event
from pyflichub.flichub import FlicHubInfo

logging.basicConfig(level=logging.DEBUG)

CLIENT_READY_TIMEOUT = 10.0
HOST = ('192.168.1.64', 8124)


def event_callback(button: FlicButton, event: Event):
    print(f"Received event: {event.event}")


def command_callback(cmd: Command):
    print(f"Received command: {cmd.command}")


async def start():
    client_ready = asyncio.Event()

    async def client_connected():
        print("Connected!")
        client_ready.set()
        await client.get_server_info()

    async def client_disconnected():
        print("Disconnected!")

    client.async_on_connected = client_connected
    client.async_on_disconnected = client_disconnected

    task = asyncio.create_task(client.async_connect())

    try:
        async with async_timeout.timeout(CLIENT_READY_TIMEOUT):
            await client_ready.wait()
    except asyncio.TimeoutError:
        print(f"Client not connected after {CLIENT_READY_TIMEOUT} secs so terminating")
        exit()

    buttons: [FlicButton] = await client.get_buttons()
    for button in buttons:
        print(f"Button name: {button.name} - Connected: {button.connected}")

    network: FlicHubInfo = await client.get_hubinfo()
    if network.has_wifi():
        print(f"Wifi State: {network.wifi.state} - Connected: {network.wifi.connected}")
    if network.has_ethernet():
        print(f"Ethernet IP: {network.ethernet.ip} - Connected: {network.ethernet.connected}")


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    client = FlicHubTcpClient(*HOST, loop=loop, event_callback=event_callback, command_callback=command_callback)
    try:
        loop.run_until_complete(start())
        loop.run_forever()
    except KeyboardInterrupt:
        client.disconnect()
        loop.close()
    except Exception as exc:  # pylint: disable=broad-except
        print(exc)
