import os
from unittest import mock

import pytest

from hallmonitor.hmutils import get_eeg_errors


@pytest.fixture
def mock_file_re(monkeypatch):
    # mock valid filename regex
    mock_re = r"(?P<id>\D+)"  # anything but digits
    monkeypatch.setattr("hallmonitor.hmutils.FILE_RE", mock_re)
    return mock_re


# Mocking a helper function for creating error records
def mock_new_error_record(logger, dataset, id, error_type, message):
    return {
        "error_type": error_type,
        "message": message,
    }


@pytest.fixture
def logger():
    # Mock logger object
    return mock.Mock()


@pytest.fixture
def dataset(tmp_path):
    # Temporary dataset directory
    return str(tmp_path)


@pytest.fixture
def mock_new_error(monkeypatch):
    # Patch the new_error_record function
    monkeypatch.setattr("hallmonitor.hmutils.new_error_record", mock_new_error_record)


# Test: Valid EEG files with consistent .vhdr, .vmrk, and .eeg content
def test_get_eeg_errors_valid_files(logger, dataset, mock_new_error, mock_file_re):
    # Simulate file contents for valid cases
    vhdr_content = "MarkerFile=correct.vmrk\nDataFile=correct.eeg"
    vmrk_content = "DataFile=correct.eeg"

    # Create a function to simulate different file contents based on the file name
    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vhdr"):
            return mock.mock_open(read_data=vhdr_content).return_value
        elif filepath.endswith(".vmrk"):
            return mock.mock_open(read_data=vmrk_content).return_value
        else:
            # Default to a regular file handler for other files
            return mock.mock_open().return_value

    # Use mock.patch to mock the open function and provide side_effect to vary behavior
    with mock.patch("builtins.open", new=mock_file_open):
        files = [
            os.path.join(dataset, "correct.vhdr"),
            os.path.join(dataset, "correct.vmrk"),
            os.path.join(dataset, "correct.eeg"),
        ]
        errors = get_eeg_errors(logger, dataset, files)
        assert errors == []  # No errors expected


# Test: Invalid marker file specified in the .vhdr file
def test_get_eeg_errors_invalid_marker(logger, dataset, mock_new_error, mock_file_re):
    vhdr_content = "MarkerFile=wrong.vmrk\nDataFile=correct.eeg"
    vmrk_content = "DataFile=correct.eeg"

    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vhdr"):
            return mock.mock_open(read_data=vhdr_content).return_value
        elif filepath.endswith(".vmrk"):
            return mock.mock_open(read_data=vmrk_content).return_value
        else:
            return mock.mock_open().return_value

    # Mock open function for reading files
    with mock.patch("builtins.open", new=mock_file_open):
        files = [
            os.path.join(dataset, "correct.vhdr"),
            os.path.join(dataset, "correct.vmrk"),
            os.path.join(dataset, "correct.eeg"),
        ]
        errors = get_eeg_errors(logger, dataset, files)

        # Check that the error is for the incorrect marker file
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == "Incorrect MarkerFile wrong.vmrk in .vhdr file, expected correct.vmrk"
        )


# Test: Missing DataFile entry in .vmrk file
def test_get_eeg_errors_missing_datafile_in_vmrk(
    logger, dataset, mock_new_error, mock_file_re
):
    vhdr_content = "MarkerFile=correct.vmrk\nDataFile=correct.eeg"
    vmrk_content = ""  # No DataFile entry

    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vhdr"):
            return mock.mock_open(read_data=vhdr_content).return_value
        elif filepath.endswith(".vmrk"):
            return mock.mock_open(read_data=vmrk_content).return_value
        else:
            return mock.mock_open().return_value

    # Mock open function for reading files
    with mock.patch("builtins.open", new=mock_file_open):
        files = [
            os.path.join(dataset, "correct.vhdr"),
            os.path.join(dataset, "correct.vmrk"),
            os.path.join(dataset, "correct.eeg"),
        ]
        errors = get_eeg_errors(logger, dataset, files)

        # Verify that an error is recorded for missing DataFile in .vmrk
        assert len(errors) == 1
        assert errors[0]["message"] == "No DataFile found in .vmrk file"


# Test: Missing .eeg file entry in .vhdr
def test_get_eeg_errors_missing_datafile_in_vhdr(
    logger, dataset, mock_new_error, mock_file_re
):
    vhdr_content = "MarkerFile=correct.vmrk\n"  # Missing DataFile
    vmrk_content = "DataFile=correct.eeg"

    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vhdr"):
            return mock.mock_open(read_data=vhdr_content).return_value
        elif filepath.endswith(".vmrk"):
            return mock.mock_open(read_data=vmrk_content).return_value
        else:
            return mock.mock_open().return_value

    with mock.patch("builtins.open", new=mock_file_open):
        files = [
            os.path.join(dataset, "correct.vhdr"),
            os.path.join(dataset, "correct.vmrk"),
            os.path.join(dataset, "correct.eeg"),
        ]
        errors = get_eeg_errors(logger, dataset, files)

        # Verify that an error is recorded for missing DataFile in .vhdr
        assert len(errors) == 1
        assert errors[0]["message"] == "No DataFile found in .vhdr file"


# Test: Invalid identifier in EEG filename
def test_get_eeg_errors_invalid_identifier(logger, dataset):
    files = [os.path.join(dataset, "invalidname.vhdr")]

    with pytest.raises(ValueError, match="Invalid EEG file name"):
        get_eeg_errors(logger, dataset, files)


# Test: Incorrect DataFile entry in marker file
def test_get_eeg_errors_incorrect_datafile_in_marker(
    logger, dataset, mock_new_error, mock_file_re
):
    vhdr_content = "MarkerFile=correct.vmrk\nDataFile=correct.eeg"
    vmrk_content = "DataFile=wrong.eeg"

    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vhdr"):
            return mock.mock_open(read_data=vhdr_content).return_value
        elif filepath.endswith(".vmrk"):
            return mock.mock_open(read_data=vmrk_content).return_value
        else:
            return mock.mock_open().return_value

    # Mock open function for reading files
    with mock.patch("builtins.open", new=mock_file_open):
        files = [
            os.path.join(dataset, "correct.vhdr"),
            os.path.join(dataset, "correct.vmrk"),
            os.path.join(dataset, "correct.eeg"),
        ]
        errors = get_eeg_errors(logger, dataset, files)

        # Verify that an error is recorded for incorrect DataFile in marker
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == "Incorrect DataFile wrong.eeg in .vmrk file, expected correct.eeg"
        )


# Test: Missing .eeg file
def test_get_eeg_errors_missing_datafile(logger, dataset, mock_new_error, mock_file_re):
    vhdr_content = "MarkerFile=correct.vmrk\nDataFile=correct.eeg"
    vmrk_content = "DataFile=correct.eeg"

    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vhdr"):
            return mock.mock_open(read_data=vhdr_content).return_value
        elif filepath.endswith(".vmrk"):
            return mock.mock_open(read_data=vmrk_content).return_value
        return mock.mock_open().return_value

    with mock.patch("builtins.open", new=mock_file_open):
        files = [
            os.path.join(dataset, "correct.vhdr"),
            os.path.join(dataset, "correct.vmrk"),
        ]
        errors = get_eeg_errors(logger, dataset, files)
        assert len(errors) == 0


# Test: missing .vmrk file
def test_get_eeg_errors_missing_markerfile(
    logger, dataset, mock_new_error, mock_file_re
):
    vhdr_content = "DataFile=correct.eeg\nMarkerFile=correct.vmrk"

    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vhdr"):
            return mock.mock_open(read_data=vhdr_content).return_value
        return mock.mock_open().return_value

    with mock.patch("builtins.open", new=mock_file_open):
        files = [
            os.path.join(dataset, "correct.vhdr"),
            os.path.join(dataset, "correct.eeg"),
        ]
        errors = get_eeg_errors(logger, dataset, files)
        assert len(errors) == 0


# Test: Missing .vhdr file
def test_get_eeg_errors_missing_headerfile(
    logger, dataset, mock_new_error, mock_file_re
):
    vmrk_content = "DataFile=correct.eeg"

    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vmrk"):
            return mock.mock_open(read_data=vmrk_content).return_value
        return mock.mock_open().return_value

    # Mock the open function to provide contents for .vmrk file only
    with mock.patch("builtins.open", new=mock_file_open):
        files = [
            os.path.join(dataset, "correct.vmrk"),
            os.path.join(dataset, "correct.eeg"),
        ]

        # Since there is no .vhdr file, get_eeg_errors should not perform checks related to .vhdr
        errors = get_eeg_errors(logger, dataset, files)

        # Verify that no errors are produced because there is no header file to validate
        assert errors == []


# Test: File extensions mismatch (.vhdr references .dat instead of .eeg)
def test_get_eeg_errors_wrong_extension(logger, dataset, mock_new_error, mock_file_re):
    vhdr_content = "MarkerFile=correct.vmrk\nDataFile=correct.dat"
    vmrk_content = "DataFile=correct.eeg"

    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vhdr"):
            return mock.mock_open(read_data=vhdr_content).return_value
        elif filepath.endswith(".vmrk"):
            return mock.mock_open(read_data=vmrk_content).return_value
        return mock.mock_open().return_value

    with mock.patch("builtins.open", new=mock_file_open):
        files = [
            os.path.join(dataset, "correct.vhdr"),
            os.path.join(dataset, "correct.vmrk"),
            os.path.join(dataset, "correct.eeg"),
        ]
        errors = get_eeg_errors(logger, dataset, files)
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == "Incorrect DataFile correct.dat in .vhdr file, expected correct.eeg"
        )


# Test: Bad naming convention based on mocked FILE_RE
def test_get_eeg_errors_bad_naming_convention(
    logger, dataset, mock_new_error, mock_file_re
):
    with mock.patch("hallmonitor.hmutils.FILE_RE", mock_file_re):
        files = [
            os.path.join(dataset, "correct.vmrk"),
            os.path.join(dataset, "123subject.vhdr"),  # Does not match the regex
            os.path.join(dataset, "correct.eeg"),
        ]

        with pytest.raises(ValueError, match="Invalid EEG file name"):
            get_eeg_errors(logger, dataset, files)


# Test: Ensure .vhdr and .vmrk files are both opened once
def test_get_eeg_errors_open_calls(logger, dataset, mock_new_error, mock_file_re):
    vhdr_content = "MarkerFile=correct.vmrk\nDataFile=correct.eeg"
    vmrk_content = "DataFile=correct.eeg"

    def mock_file_open(filepath, *args, **kwargs):
        if filepath.endswith(".vhdr"):
            return mock.mock_open(read_data=vhdr_content).return_value
        elif filepath.endswith(".vmrk"):
            return mock.mock_open(read_data=vmrk_content).return_value
        return mock.mock_open().return_value

    with mock.patch("builtins.open", new_callable=mock.Mock()) as mock_open:
        mock_open.side_effect = mock_file_open

        files = [
            os.path.join(dataset, "correct.vhdr"),
            os.path.join(dataset, "correct.vmrk"),
            os.path.join(dataset, "correct.eeg"),
        ]

        # Call the function to check for errors
        get_eeg_errors(logger, dataset, files)

        # Ensure builtins.open is called once for the .vhdr and once for the .vmrk
        vhdr_path = os.path.join(dataset, "correct.vhdr")
        vmrk_path = os.path.join(dataset, "correct.vmrk")

        mock_open.assert_any_call(vhdr_path, "r")
        mock_open.assert_any_call(vmrk_path, "r")

        # Verify that the .vhdr and .vmrk files are each opened exactly once
        assert mock_open.call_count == 2
