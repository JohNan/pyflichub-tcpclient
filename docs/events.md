# Event Handling and Payloads

When registering an event callback with `FlicHubTcpClient`, your callback function receives two arguments: the `FlicButton` instance that triggered the event, and the `Event` payload object containing details of the action.

```python
def my_event_callback(button: FlicButton, event: Event):
    print(f"Event received for {button.name}: {event.event}")
```

## The `Event` Object

The `Event` object is structured to provide flexible attributes depending on the type of event being dispatched.

*   `event` (str): The name of the event (e.g., `'button'`, `'buttonConnected'`, `'virtualDeviceUpdate'`).
*   `button` (str): The Bluetooth address (`bdaddr`) of the physical Flic Button, if provided natively.
*   `action` (str): The button action performed (e.g., `'click'`, `'hold'`, `'double_click'`).
*   `button_number` (int): The number indicating the physical button pressed (used with multi-button devices like the Flic Twist).
*   `meta_data` (dict): Additional event-specific information.
*   `values` (dict): Contextual readings or states associated with the action.

## Virtual Device Events (`virtualDeviceUpdate`)

When a Flic Twist (or similar hardware mapped to a virtual device) issues a state change, a `virtualDeviceUpdate` event is dispatched.

The `FlicHubTcpClient` intercepts this payload, uses `event.meta_data["button_id"]` to find the registered `FlicButton`, and passes it to your callback.

### Example Payload Structure

The underlying JSON payload structure sent from the Hub looks like this:

```json
{
  "event": "virtualDeviceUpdate",
  "meta_data": {
    "button_id": "90:88:a9:5b:12:89",
    "virtual_device_id": "Virtual Light",
    "dimmable_type": "Light"
  },
  "values": {
    "brightness": 0.823853
  }
}
```

### Accessing Data in the Callback

When this JSON is converted into an `Event` object for your listener:

```python
def my_event_callback(button, event):
    if event.event == 'virtualDeviceUpdate':
        # button is the FlicButton instance linked to "90:88:a9:5b:12:89"

        virtual_device = event.meta_data.get('virtual_device_id') # "Virtual Light"
        new_brightness = event.values.get('brightness')           # 0.823853

        print(f"{button.name} updated {virtual_device} to brightness: {new_brightness}")
```

### Sending Virtual Device Updates

You can also send state updates back to the Flic Hub to synchronize the state of virtual devices (like setting the brightness of a virtual light).

Use the `send_virtual_device_update_state` method on the `FlicHubTcpClient`:

```python
# Assuming `client` is your initialized FlicHubTcpClient instance
client.send_virtual_device_update_state(
    dimmable_type="Light",
    virtual_device_id="Virtual Light",
    values={"brightness": 0.5, "state": True}
)
```

## Available Events

The following events are dispatched to your `event_callback` depending on the action or status change:

*   `button`: Fired when a button interaction occurs (e.g. click, double-click, hold). Provides the action type in `event.action` ('down', 'up', 'single', 'double', 'hold', 'idle').
*   `buttonAdded`: Fired when a new button is paired to the hub. The library will automatically try to fetch its details in the background. The `button` argument to the callback may be `None` initially.
*   `buttonDeleted`: Fired when a button is unpaired/deleted.
*   `buttonConnected`: Fired when a button makes a physical connection to the hub.
*   `buttonDisconnected`: Fired when the connection to the button drops.
*   `buttonReady`: Fired when the button connection has been fully verified and is ready for use.
*   `actionMessage`: Fired when a Flic Hub Studio message action is executed (configured as a trigger in the Flic app).
*   `virtualDeviceUpdate`: Fired when a Flic Twist rotates to control a virtual device. Contains values in `event.values` (like brightness, volume, etc.).

## Client API

The `FlicHubTcpClient` provides the following main methods for interacting with the Flic Hub:

*   `async_connect()`: Connect to the Flic Hub TCP server asynchronously.
*   `disconnect()`: Disconnect from the Flic Hub TCP server.
*   `get_buttons() -> list[FlicButton]`: Retrieve the list of all currently paired buttons from the Hub.
*   `get_server_info() -> ServerInfo | None`: Retrieve the current server information and version from the Flic Hub.
*   `get_hubinfo() -> FlicHubInfo | None`: Retrieve the networking and general information about the Flic Hub.
*   `async_check_for_updates()`: Checks if there is a newer version of the Python library or the Flic Hub `tcpserver.js` script.
*   `play_ir(signal_id: str)`: Replays an infrared signal saved on the Flic Hub using the `ir` module.
*   `send_virtual_device_update_state(dimmable_type: str, virtual_device_id: str, values: dict)`: Update the state of a virtual device (e.g., synchronizing brightness for a Flic Twist).
