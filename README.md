# Asynchronous Python TCP Client for FlicHub

Get events from the FlicHub when a Flic/Twist Button is clicked and send them to [home-assistant-flichub](https://github.com/JohNan/home-assistant-flichub).

To be able to use this client you need to enable the Flic Hub SDK described on [this](https://flic.io/flic-hub-sdk) page.

Create a new module and name it pyflichub-tcpclient (or any name) and paste the code found in `tcpserver.js` in the editor and press play. Check the box "Restart after crash or reboot."

This will open a TCP Server on port `8124` (configurable by changing `PORT`)

## Usage

```python
import asyncio
from pyflichub.client import FlicHubTcpClient
from pyflichub.button import FlicButton
from pyflichub.event import Event

def event_callback(button: FlicButton, event: Event):
    print(f"Received event: {event.event}")
    if button:
        print(f"Button: {button.name} ({button.bdaddr})")

    if event.event == 'button':
        print(f"Action: {event.action}")

def command_callback(cmd):
    print(f"Received command: {cmd.command}")

async def main():
    loop = asyncio.get_event_loop()
    client = FlicHubTcpClient(
        ip='192.168.1.100',
        port=8124,
        loop=loop,
        event_callback=event_callback,
        command_callback=command_callback
    )

    await client.async_connect()

    # Retrieve all buttons
    buttons = await client.get_buttons()
    print(f"Found {len(buttons)} buttons.")

    # Keep the connection alive
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
```

### Emitted Events

The following events are explicitly dispatched to the `event_callback` provided during initialization:

- `button`: Fired when a button interaction occurs (e.g. click, double-click, hold). Provides the action type in `event.action` ('down', 'up', 'single', 'double', 'hold', 'idle').
- `buttonAdded`: Fired when a new button is paired to the hub. The library will automatically try to fetch its details in the background. The `button` argument to the callback may be `None` initially.
- `buttonDeleted`: Fired when a button is unpaired/deleted.
- `buttonConnected`: Fired when a button makes a physical connection to the hub.
- `buttonDisconnected`: Fired when the connection to the button drops.
- `buttonReady`: Fired when the button connection has been fully verified and is ready for use.
- `actionMessage`: Fired when a Flic Hub Studio message action is executed (configured as a trigger in the Flic app).
- `virtualDeviceUpdate`: Fired when a Flic Twist rotates to control a virtual device. Contains values in `event.values` (like brightness, volume, etc.).

### Handling Twist Jitter/Sensitivity

When working with virtual device outputs mapping to Flic Twist, you may find the outputs to be twitchy or experience jitter. To resolve this, you can utilize the provided `RateDetentController` utility. This allows variable-speed adjusters with features like sticky neutral and debounce to smooth out inputs.

```python
from pyflichub.twist_controller import RateDetentController

# Inside your application...
def on_volume_change(new_volume_pct):
    print(f"Setting volume to: {new_volume_pct}%")

# Create a controller once for the button
volume_controller = RateDetentController(
    cfg={"minOutPct": 0, "maxOutPct": 100},
    on_change_callback=on_volume_change
)

def event_callback(button: FlicButton, event: Event):
    if event.event == 'virtualDeviceUpdate':
        # Push raw values through the controller
        # Make sure you only pass value updates matching the button and device
        volume_controller.update_raw(event.values['volume'] * 100)
```

### Disclaimer
This python library was not made by Flic. It is not official, not developed, and not supported by Flic.
