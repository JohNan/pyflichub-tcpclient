from dataclasses import dataclass
from datetime import datetime


@dataclass
class FlicButton():
    def __init__(self, bdaddr: str, serial_number: str, color: str, name: str, active_disconnect: bool, connected: bool,
                 ready: bool, battery_status: int, uuid: str, flic_version: int, firmware_version: int, key: str,
                 passive_mode: bool, battery_timestamp: datetime = None) -> None:
        self.bdaddr = bdaddr
        self.serial_number = serial_number
        self.color = color
        self.name = name
        self.active_disconnect = active_disconnect
        self.connected = connected
        self.ready = ready
        self.battery_status = battery_status
        self.uuid = uuid
        self.flic_version = flic_version
        self.firmware_version = firmware_version
        self.key = key
        self.passive_mode = passive_mode
        self.battery_timestamp = battery_timestamp
