import json
import logging
import urllib.request

_LOGGER = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/pyflichub-tcpclient/json"
UPDATE_LINK = "https://hubsdk.flic.io"


def get_latest_version():
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data["info"]["version"]
    except Exception as e:
        _LOGGER.warning(f"Failed to fetch latest version from PyPI: {e}")
        return None


def is_newer(latest, current):
    try:
        return [int(x) for x in latest.split(".")] > [int(x) for x in current.split(".")]
    except (ValueError, AttributeError):
        return latest > current


def check_for_updates(current_version):
    latest_version = get_latest_version()
    if latest_version and is_newer(latest_version, current_version):
        return True, latest_version
    return False, latest_version
