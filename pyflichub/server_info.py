from dataclasses import dataclass


@dataclass
class ServerInfo:
    def __init__(self, version: str):
        self.version = version
