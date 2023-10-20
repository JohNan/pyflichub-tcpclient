from dataclasses import dataclass


@dataclass
class Event:
    def __init__(self, event: str, button: str, action: str):
        self.event = event
        self.button = button
        self.action = action
