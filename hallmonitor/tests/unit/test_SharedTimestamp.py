import datetime
from unittest import mock

import pytest

from hallmonitor.hmutils import DT_FORMAT, SharedTimestamp, get_timestamp


def setup_function():
    SharedTimestamp._ts = None


def test_get_timestamp_format():
    with mock.patch("hallmonitor.hmutils.datetime") as mock_datetime:
        mock_dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = mock_dt

        # Ensure the timestamp is returned in the correct format
        expected_timestamp = mock_dt.strftime(DT_FORMAT)
        assert get_timestamp() == expected_timestamp


def test_shared_timestamp_singleton():
    ts1 = SharedTimestamp()
    ts2 = SharedTimestamp()

    # Ensure that both instances share the same timestamp
    assert ts1 == ts2


def test_shared_timestamp_singleton_identity():
    ts1 = SharedTimestamp()
    ts2 = SharedTimestamp()

    # Ensure that both variables point to the same object in memory
    assert ts1 is ts2


def test_shared_timestamp_generated_once():
    with mock.patch("hallmonitor.hmutils.get_timestamp") as mock_get_timestamp:
        mock_get_timestamp.return_value = "2024-01-01T12:00:00"

        # First call should generate the timestamp
        ts1 = SharedTimestamp()
        mock_get_timestamp.assert_called_once()

        # Subsequent calls should not call get_timestamp again
        ts2 = SharedTimestamp()
        mock_get_timestamp.assert_called_once()  # Still only one call
        assert ts1 == ts2


def test_shared_timestamp_reset():
    with mock.patch("hallmonitor.hmutils.get_timestamp") as mock_get_timestamp:
        mock_get_timestamp.side_effect = ["2024-01-01T12:00:00", "2024-01-01T12:01:00"]

        # First instance should get the first timestamp
        ts1 = SharedTimestamp()
        assert ts1 == "2024-01-01T12:00:00"

        # Reset the class-level timestamp
        SharedTimestamp._ts = None

        # Second instance should get a new timestamp
        ts2 = SharedTimestamp()
        assert ts2 == "2024-01-01T12:01:00"


def test_shared_timestamp_format():
    ts = SharedTimestamp()

    # Ensure the timestamp follows the correct format
    try:
        datetime.datetime.strptime(ts, DT_FORMAT)
    except ValueError:
        pytest.fail(f"Timestamp {ts} does not match the format {DT_FORMAT}")
