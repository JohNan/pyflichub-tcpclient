# Guidelines for AI Coding Agents

Welcome to the `pyflichub-tcpclient` project! This file outlines technical context, testing guidelines, and specific implementation details to assist AI coding agents when working on this repository.

## Project Structure

This project is an Asynchronous Python TCP Client for the FlicHub (`pyflichub-tcpclient`). It connects to a `tcpserver.js` script running on the Flic Hub device to receive events and send commands.

- `pyflichub/`: Python library source code.
- `pyflichub/client.py`: Core client implementation (`FlicHubTcpClient`).
- `pyflichub/button.py`, `pyflichub/event.py`: Dataclasses for buttons and events.
- `tcpserver.js`: The JavaScript TCP server script designed to be executed directly on the Flic Hub device using the Flic Hub SDK.
- `docs/`: Documentation.
- `tests/`: Pytest suite.

## Dependency Management

- Core project dependencies are managed via pip and listed in `requirements.txt`.
- Test-specific dependencies are located in `requirements_test.txt`.
- Install all development and test dependencies using `pip install -r requirements.txt -r requirements_test.txt`.

## Code Formatting

- The project uses Black for code formatting.
- The configured line-length is 120 characters.

## Testing Guidelines

- The project uses `pytest` for testing.
- **Important**: To run tests successfully and avoid module discovery issues, use `python -m pytest --import-mode=append tests/` or set `PYTHONPATH=.` before running `pytest`.
- The GitHub Actions CI workflow (`unit_test`) executes pytest explicitly against the `tests/` directory using this command.
- When mocking `asyncio` task creation (like `client._loop.create_task`) in tests, call `.close()` on the unawaited coroutine argument to prevent 'coroutine was never awaited' warnings.
- In tests involving asyncio, use `asyncio.new_event_loop()` instead of `asyncio.get_event_loop()` to ensure compatibility with Python 3.10+ and avoid 'missing current event loop' `RuntimeError`s.

## Implementation Details & "Gotchas"

### Python Client (`pyflichub/client.py`)
- The `_handle_event` method maintains an internal `self.buttons` list. It dynamically updates button state by removing buttons on `buttonDeleted`, toggling connectivity on `buttonConnected`/`buttonDisconnected`, and fetching updated lists on `buttonAdded`.
- The `_handle_event` method dispatches lifecycle events (like `buttonAdded`, `buttonDeleted`, `buttonConnected`) to `_event_callback` even if the `button` instance is not yet cached internally, passing `None` as the button argument in such cases.
- `virtualDeviceUpdate` events contain a `button_id` within the `meta_data` payload that must be explicitly resolved using `self._get_button()` to correctly associate the event with its physical Flic button for the event listeners.

### JavaScript Hub Script (`tcpserver.js`)
- The `tcpserver.js` script handles incoming data by attempting to parse it as JSON first; if parsing fails, it falls back to processing the message as a legacy plain-text string command for backward compatibility.
- Format JSON event payloads using snake_case keys directly within `tcpserver.js` to align with Python conventions in `pyflichub/client.py` and minimize extra parsing dependencies like `humps`.
- Flic Duo buttons include a `buttonNumber` property (0 or 1) in their Hub SDK JavaScript API events. When handling this property in `tcpserver.js`, it must be checked strictly against `undefined` (e.g., `!== undefined`) because `0` evaluates to falsy.
- In the Flic Hub SDK, `buttons` module events pass a payload object to handlers, not a direct Button object. The `buttonAdded` event payload contains a nested `button` object (accessed via `obj.button.bdaddr`), while lifecycle events like `buttonConnected`, `buttonReady`, `buttonDeleted`, and `buttonDisconnected` pass an object containing `bdaddr` directly (accessed via `obj.bdaddr`).
- The Flic Hub TCP server implementation utilizes the Hub SDK's `ir` module to support infrared signal playback via the `play_ir` command, which requires a `signal_id` parameter in the JSON payload.

### Versioning and Updates
- The package name is `pyflichub-tcpclient` and uses `setuptools_scm` to manage versioning, writing the version string to `pyflichub/version.py`.
- The project includes an update check mechanism in `pyflichub/updater.py` that retrieves the latest version from PyPI and compares it against the local library and Hub-side script versions.
