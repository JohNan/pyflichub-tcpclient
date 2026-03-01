from dataclasses import dataclass
from typing import Optional


@dataclass
class Event:
    def __init__(self, event: str, button: Optional[str] = None, action: Optional[str] = None, meta_data: Optional[dict] = None, values: Optional[dict] = None):
        self.event = event
        self.button = button
        self.action = action
        self.meta_data = meta_data
        self.values = values
