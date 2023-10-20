from dataclasses import dataclass
from typing import Any

from pyflichub.server_command import ServerCommand


@dataclass
class Command:
    def __init__(self, command: ServerCommand, data: Any):
        self.command = command
        self.data = data
