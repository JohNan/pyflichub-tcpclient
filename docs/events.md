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
