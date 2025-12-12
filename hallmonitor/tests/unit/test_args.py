import argparse
import datetime
from unittest import mock

import pytest

from hallmonitor.hmutils import (
    get_args,
    validated_dataset,
    validated_redcap_map,
    validated_redcap_replace,
)

# examples to test dataset validation
DATASET_DIR = "/datasets"
VALID_DATASET = f"{DATASET_DIR}/some_dataset"


@pytest.fixture
def mock_dataset_dir(monkeypatch):
    # Set a mock dataset directory
    monkeypatch.setattr("hallmonitor.hmutils.DATASET_DIR", DATASET_DIR)


# --- test dataset validation ---


def test_validated_dataset_valid(mock_dataset_dir):
    # should not raise an error
    validated_dataset(VALID_DATASET)


def test_validated_dataset_invalid(mock_dataset_dir):
    # Mock an invalid dataset path
    invalid_path = "/some/other/directory"
    with pytest.raises(argparse.ArgumentTypeError):
        validated_dataset(invalid_path)


# make sure validated_dataset checks the passed dataset's absolute path
def test_validated_dataset_realpath(mock_dataset_dir):
    with mock.patch("os.getcwd", return_value=f"{DATASET_DIR}/subdir"):
        assert validated_dataset("../some_dataset") == VALID_DATASET

        # test with invalid dataset path
        with pytest.raises(argparse.ArgumentTypeError):
            validated_dataset("../../invalid_dataset")


def test_validated_dataset_is_dataset_dir(mock_dataset_dir):
    # passing DATASET_DIR itself should raise an error
    with pytest.raises(argparse.ArgumentTypeError):
        validated_dataset(DATASET_DIR)


def test_validated_dataset_trailing_slash(mock_dataset_dir):
    assert validated_dataset(f"{VALID_DATASET}/") == VALID_DATASET


def test_validated_dataset_symlink(mock_dataset_dir, tmp_path):
    # Create a symlink to a valid dataset
    valid_symlink = tmp_path / "symlink_to_dataset"
    valid_symlink.symlink_to(VALID_DATASET)

    # Should pass if the symlink resolves to a valid dataset
    assert validated_dataset(str(valid_symlink)) == VALID_DATASET


# --- test replace validation ---


def test_validated_redcap_replace_valid():
    # Valid replacement column map
    valid_input = "col1"
    assert validated_redcap_replace(valid_input) == valid_input


def test_validated_redcap_replace_invalid():
    # Invalid replacement column map
    invalid_input = "col1 col2"
    with pytest.raises(argparse.ArgumentTypeError):
        validated_redcap_replace(invalid_input)


def test_validated_redcap_replace_empty():
    with pytest.raises(argparse.ArgumentTypeError):
        validated_redcap_replace("")


def test_validated_redcap_replace_multiple():
    # Test valid input with multiple columns
    valid_input = ["col1", "col2", "col3"]
    assert [validated_redcap_replace(col) for col in valid_input] == valid_input


def test_get_args_replace(mock_dataset_dir):
    test_args = [VALID_DATASET, "--replace", "col1", "col2"]
    with mock.patch("sys.argv", ["program_name"] + test_args):
        args = get_args()
        assert args.dataset == VALID_DATASET
        assert args.replace == ["col1", "col2"]
        assert not args.map


# --- test mapping validation ---


def test_validated_redcap_map_valid():
    # Valid map
    valid_input = "old:new"
    assert validated_redcap_map(valid_input) == ("old", "new")


def test_validated_redcap_map_invalid():
    # Invalid map
    invalid_input = "oldnew"
    with pytest.raises(argparse.ArgumentTypeError):
        validated_redcap_map(invalid_input)


def test_validated_redcap_map_empty():
    with pytest.raises(argparse.ArgumentTypeError):
        validated_redcap_map("")


def test_validated_redcap_map_multiple_colons():
    invalid_input = "old:new:extra"
    with pytest.raises(argparse.ArgumentTypeError):
        validated_redcap_map(invalid_input)


def test_get_args_map(mock_dataset_dir):
    test_args = [VALID_DATASET, "--map", "old:new", "old2:new2"]
    with mock.patch("sys.argv", ["program_name"] + test_args):
        args = get_args()
        assert args.dataset == VALID_DATASET
        assert args.map == [("old", "new"), ("old2", "new2")]
        assert not args.replace


# --- test assorted functionality ---


def test_get_args_none(mock_dataset_dir):
    test_args = [VALID_DATASET]
    with mock.patch("sys.argv", ["program_name"] + test_args):
        args = get_args()
        assert args.dataset == VALID_DATASET
        assert not args.replace
        assert not args.map
        assert not args.verbose
        assert not args.quiet


def test_get_args_replace_and_map_mutually_exclusive(mock_dataset_dir):
    test_args = [VALID_DATASET, "--replace", "col1", "--map", "old:new"]
    with mock.patch("sys.argv", ["program_name"] + test_args):
        with pytest.raises(SystemExit):  # argparse throws SystemExit on parsing failure
            get_args()


# Test get_args with verbosity flags
def test_get_args_verbose(mock_dataset_dir):
    test_args = [VALID_DATASET, "--verbose"]
    with mock.patch("sys.argv", ["program_name"] + test_args):
        args = get_args()
        assert args.verbose
        assert not args.quiet


def test_get_args_quiet(mock_dataset_dir):
    test_args = [VALID_DATASET, "--quiet"]
    with mock.patch("sys.argv", ["program_name"] + test_args):
        args = get_args()
        assert args.quiet
        assert not args.verbose


def test_get_args_ignore_before(mock_dataset_dir):
    test_args = [VALID_DATASET, "--ignore-before", "2022-01-01"]
    with mock.patch("sys.argv", ["program_name"] + test_args):
        args = get_args()
        assert args.ignore_before == datetime.date(2022, 1, 1)


def test_get_args_ignore_before_bad_date(mock_dataset_dir):
    base_args = [VALID_DATASET, "--ignore-before"]
    test_dates = ["2022-01-32", "2022-13-01", "2022-01-01-01", "2022-301-01", "2022-04"]
    for date in test_dates:
        with (
            mock.patch("sys.argv", ["program_name"] + base_args + [date]),
            pytest.raises(SystemExit),
        ):
            get_args()
