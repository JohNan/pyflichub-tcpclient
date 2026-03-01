import asyncio
import json
from pyflichub.client import FlicHubTcpClient
from pyflichub.server_command import ServerCommand

class MockTransport:
    def __init__(self):
        self.sent_data = []

    def write(self, data):
        self.sent_data.append(data)

    def close(self):
        pass

async def test_play_ir():
    loop = asyncio.get_event_loop()
    client = FlicHubTcpClient("127.0.0.1", 8124, loop)
    transport = MockTransport()
    client.connection_made(transport)

    # Test play_ir
    signal = "0000 006d 0022 0002 0155 00aa 0015 0015 0015 0015 0015 0040 0015 0015 0015 0015 0015 0015 0015 0015 0015 0015 0015 0040 0015 0040 0015 0015 0015 0040 0015 0040 0015 0040 0015 0040 0015 0040 0015 0015 0015 0015 0015 0015 0015 0040 0015 0015 0015 0015 0015 0015 0015 0015 0015 0040 0015 0040 0015 0040 0015 0015 0015 0040 0015 0040 0015 0040 0015 0040 0015 0606 0155 0055 0015 0e40"
    await client.play_ir(signal)

    expected_payload = json.dumps({"command": "play_ir", "data": signal}) + "\n"
    assert transport.sent_data[0].decode() == expected_payload
    print("test_play_ir passed!")

    # Test other commands still work as strings
    transport.sent_data = []
    client._async_send_command(ServerCommand.BUTTONS)
    assert transport.sent_data[0].decode() == "buttons\n"
    print("test_plain_command passed!")

if __name__ == "__main__":
    asyncio.run(test_play_ir())
