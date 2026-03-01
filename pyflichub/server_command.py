from enum import StrEnum


class ServerCommand(StrEnum):
    BUTTONS = "buttons"
    SERVER_INFO = "server"
    HUB_INFO = "network"
    PLAY_IR = "play_ir"
