import datetime

import pandas as pd
import pytest
import pytz

from hallmonitor.hmutils import get_timestamp, get_variable_datatype


@pytest.fixture
def mock_datadict(monkeypatch):
    dd_df = pd.DataFrame(
        {
            "variable": ["eeg", "psychopy", "var3"],
            "expectedFileExt": ['".eeg,.vmrk,.vhdr"', '".txt,.csv"', '""'],
            "dataType": ["visit_data", "other", "visit_data"],
            "encrypted": [False] * 3,
            "provenance": ["variables: eeg, psychopy", "variables: var3", ""],
        }
    )
    monkeypatch.setattr("hallmonitor.hmutils.get_datadict", lambda _: dd_df)


# test get_timestamp(), DT_FORMAT, and TZ_INFO

MOCK_TIME = datetime.datetime(year=2024, month=3, day=14, hour=7, minute=29, second=42)


@pytest.fixture
def mock_datetime_now(monkeypatch):
    class mock_datetime(datetime.datetime):
        @classmethod
        def now(cls, tzinfo=None):
            return MOCK_TIME.astimezone(tzinfo)

    monkeypatch.setattr(datetime, "datetime", mock_datetime)


@pytest.fixture
def mock_dt_format(monkeypatch):
    dt_format = "%Y-%m-%d %H:%M"
    monkeypatch.setattr("hallmonitor.hmutils.DT_FORMAT", dt_format)


@pytest.fixture
def mock_tz_info(monkeypatch):
    tz_info = pytz.timezone("US/Eastern")
    monkeypatch.setattr("hallmonitor.hmutils.TZ_INFO", tz_info)


def test_get_timestamp(mock_datetime_now, mock_dt_format, mock_tz_info):
    assert get_timestamp() == "2024-03-14 07:29"


def test_get_timestamp_different_format(mock_datetime_now, monkeypatch, mock_tz_info):
    # Change the date format
    monkeypatch.setattr("hallmonitor.hmutils.DT_FORMAT", "%Y/%m/%d")
    assert get_timestamp() == "2024/03/14"


def test_get_timestamp_different_timezone(
    mock_datetime_now, mock_dt_format, monkeypatch
):
    # Change the timezone
    est = pytz.timezone("US/Eastern")
    monkeypatch.setattr("hallmonitor.hmutils.TZ_INFO", est)

    # Assert that the timestamp is adjusted to the new timezone
    assert (
        get_timestamp() == "2024-03-14 07:29"
    )  # The time is the same as MOCK_TIME in this timezone


def test_get_timestamp_different_time(monkeypatch, mock_dt_format, mock_tz_info):
    # Change the MOCK_TIME to a different datetime
    new_time = datetime.datetime(
        year=2023, month=12, day=25, hour=12, minute=0, second=0
    )

    class mock_datetime(datetime.datetime):
        @classmethod
        def now(cls, tzinfo=None):
            return new_time.astimezone(tzinfo)

    monkeypatch.setattr(datetime, "datetime", mock_datetime)

    # Assert that the timestamp matches the new MOCK_TIME
    assert get_timestamp() == "2023-12-25 12:00"


def test_get_variable_datatype(mock_datadict):
    assert get_variable_datatype("", "eeg") == "visit_data"
    assert get_variable_datatype("", "psychopy") == "other"
