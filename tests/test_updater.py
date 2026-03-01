from unittest.mock import patch, MagicMock
from pyflichub.updater import check_for_updates, is_newer


def test_is_newer():
    assert is_newer("0.1.12", "0.1.11") is True
    assert is_newer("1.0.0", "0.1.11") is True
    assert is_newer("0.1.11", "0.1.11") is False
    assert is_newer("0.1.10", "0.1.11") is False
    assert is_newer("0.2.0", "0.1.11") is True


@patch("urllib.request.urlopen")
def test_check_for_updates_available(mock_urlopen):
    # Mock the response from PyPI
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"info": {"version": "0.1.12"}}'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    update_available, latest_version = check_for_updates("0.1.11")

    assert update_available is True
    assert latest_version == "0.1.12"


@patch("urllib.request.urlopen")
def test_check_for_updates_not_available(mock_urlopen):
    # Mock the response from PyPI
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"info": {"version": "0.1.11"}}'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    update_available, latest_version = check_for_updates("0.1.11")

    assert update_available is False
    assert latest_version == "0.1.11"


@patch("urllib.request.urlopen")
def test_check_for_updates_error(mock_urlopen):
    # Mock an error during the request
    mock_urlopen.side_effect = Exception("Network error")

    update_available, latest_version = check_for_updates("0.1.11")

    assert update_available is False
    assert latest_version is None
