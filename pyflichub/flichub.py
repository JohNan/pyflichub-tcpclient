from dataclasses import dataclass


@dataclass
class WifiInfo:
    state: str
    ssid: str

    def __init__(self, connected, ip, mac):
        self.connected = connected
        self.ip = ip
        self.mac = mac


@dataclass
class EthernetInfo:
    def __init__(self, connected, ip, mac):
        self.connected = connected
        self.ip = ip
        self.mac = mac


@dataclass
class DhcpInfo:
    def __init__(self, wifi=None, ethernet=None):
        self.wifi = WifiInfo(**wifi) if wifi else None
        self.ethernet = EthernetInfo(**ethernet) if ethernet else None


@dataclass
class _WifiState:
    def __init__(self, state, ssid):
        self.state = state
        self.ssid = ssid


def _decode_ssid(ssid):
    if ssid is None:
        return None
    return ''.join(chr(byte) for byte in ssid)


@dataclass
class FlicHubInfo:
    def __init__(self, dhcp, wifi_state=None):
        self._dhcp = DhcpInfo(**dhcp)
        self._dhcp.wifi.state = wifi_state.get('state', None) if wifi_state else None
        self._dhcp.wifi.ssid = _decode_ssid(wifi_state.get('ssid', None)) if wifi_state else None

    def has_wifi(self) -> bool:
        return self._dhcp.wifi is not None

    def has_ethernet(self) -> bool:
        return self._dhcp.ethernet is not None

    @property
    def wifi(self) -> WifiInfo:
        return self._dhcp.wifi

    @property
    def ethernet(self) -> EthernetInfo:
        return self._dhcp.ethernet
