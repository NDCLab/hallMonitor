import os
from unittest import mock

import pandas as pd
import pytest

from hallmonitor.hmutils import (
    FILE_RECORD_COLS,
    get_file_record,
    new_file_record_df,
    write_file_record,
)

FILE_RECORD_SUBPATH = "file_record.csv"


def mock_new_file_record_df():
    return pd.DataFrame(columns=FILE_RECORD_COLS)


@pytest.fixture
def mock_dataset_dir(tmp_path):
    # Creates a temporary directory for the dataset
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    return str(dataset_dir)


# Test for get_file_record when the file exists
def test_get_file_record_exists(mock_dataset_dir):
    file_path = os.path.join(mock_dataset_dir, FILE_RECORD_SUBPATH)
    mock_df = pd.DataFrame(
        {
            "datetime": ["2024-01-01"],
            "user": ["user1"],
            "dataType": ["EEG"],
            "identifier": ["ID001"],
            "encrypted": [False],
        }
    )

    with (
        mock.patch("os.path.exists", return_value=True),
        mock.patch("pandas.read_csv", return_value=mock_df) as mock_read_csv,
        mock.patch("hallmonitor.hmutils.FILE_RECORD_SUBPATH", FILE_RECORD_SUBPATH),
    ):
        result = get_file_record(mock_dataset_dir)
        mock_read_csv.assert_called_once()
        assert mock_read_csv.call_args[0][0] == file_path
        pd.testing.assert_frame_equal(result, mock_df)


# Test for get_file_record when the file does not exist
def test_get_file_record_not_exists(mock_dataset_dir):
    with (
        # Mock os.path.exists to simulate that the file doesn't exist
        mock.patch("os.path.exists", return_value=False),
        mock.patch(
            "hallmonitor.hmutils.new_file_record_df",
            side_effect=mock_new_file_record_df,
        ),
    ):
        result = get_file_record(mock_dataset_dir)
        # Ensure it's an empty DataFrame with the correct columns
        assert result.equals(mock_new_file_record_df())


# Test for new_file_record_df returning the correct DataFrame structure
def test_new_file_record_df():
    result = new_file_record_df()
    assert list(result.columns) == FILE_RECORD_COLS
    assert result.empty  # Ensure it's an empty DataFrame


def test_write_file_record_valid(mock_dataset_dir):
    # Mock FILE_RECORD_SUBPATH for the test
    file_path = os.path.join(mock_dataset_dir, FILE_RECORD_SUBPATH)

    # Create a mock DataFrame
    df = pd.DataFrame(
        {
            "datetime": ["2024-01-01"],
            "user": ["user1"],
            "dataType": ["EEG"],
            "encrypted": [False],
            "identifier": ["ID001"],
            "subject": [1],
            "suffix": ["none"],
        }
    )

    with (
        # Mock the FILE_RECORD_SUBPATH variable
        mock.patch("hallmonitor.hmutils.FILE_RECORD_SUBPATH", FILE_RECORD_SUBPATH),
        # Mock to_csv method to avoid file I/O
        mock.patch("pandas.DataFrame.to_csv") as mock_to_csv,
    ):
        write_file_record(mock_dataset_dir, df)
        # Ensure the correct file path is used and to_csv is called with it
        mock_to_csv.assert_called_once_with(file_path, index=False)


# Test for write_file_record when DataFrame is missing required columns
def test_write_file_record_missing_columns(mock_dataset_dir):
    df = pd.DataFrame(
        {
            "datetime": ["2024-01-01"],
            "user": ["user1"],
            "identifier": ["ID001"],
            "encrypted": [False],
        }
    )  # Missing the 'dataType' column

    with pytest.raises(KeyError, match="does not contain required columns"):
        write_file_record(mock_dataset_dir, df)


# Test for write_file_record sorting
def test_write_file_record_sorting(mock_dataset_dir):
    df = pd.DataFrame(
        {
            "datetime": ["2024-01-02", "2024-01-01"],
            "user": ["user2", "user1"],
            "identifier": ["ID002", "ID001"],
            "subject": [2, 1],
            "dataType": ["dummyDataType"] * 2,
            "encrypted": [False] * 2,
            "suffix": ["none"] * 2,
        }
    )

    with mock.patch("hallmonitor.hmutils.FILE_RECORD_SUBPATH", FILE_RECORD_SUBPATH):
        write_file_record(mock_dataset_dir, df)

        # Ensure the DataFrame is sorted by 'datetime' and 'identifier'
        sorted_df = df.sort_values(by=["datetime", "identifier"]).reset_index(drop=True)

        # Retrieve the written-out DataFrame
        actual_df = pd.read_csv(os.path.join(mock_dataset_dir, FILE_RECORD_SUBPATH))
        actual_df["encrypted"] = actual_df["encrypted"].astype(bool)

        # Retrieve the actual DataFrame that called to_csv
        pd.testing.assert_frame_equal(actual_df, sorted_df)
