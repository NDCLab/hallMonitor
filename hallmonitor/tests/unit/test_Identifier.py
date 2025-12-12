import os
import re
from unittest import mock

import pytest

from hallmonitor.hmutils import Identifier

IDENTIFIER_RE = (
    r"(?P<subject>[a-zA-Z0-9]+)_(?P<var>[a-zA-Z0-9]+)_(?P<sre>(?:[a-zA-Z0-9]+_?){3})"
)


@pytest.fixture
def valid_identifier_str():
    return "sub001_eeg_s1_r1_e1"


@pytest.fixture
def identifier():
    return Identifier("sub-001", "all_eeg", "s1", "r1", "e1")


@pytest.fixture
def invalid_identifier_str():
    return "invalid_identifier"


@pytest.fixture
def mock_dataset():
    return "/mock_dataset_path"


def test_identifier_from_str_valid(valid_identifier_str):
    with mock.patch(
        "hallmonitor.hmutils.Identifier.PATTERN", re.compile(IDENTIFIER_RE)
    ):
        identifier = Identifier.from_str(valid_identifier_str)
        assert identifier.subject == "sub001"
        assert identifier.variable == "eeg"
        assert identifier.session == "s1"
        assert identifier.run == "r1"
        assert identifier.event == "e1"


def test_identifier_from_str_invalid(invalid_identifier_str):
    with mock.patch(
        "hallmonitor.hmutils.Identifier.PATTERN", re.compile(IDENTIFIER_RE)
    ):
        with pytest.raises(ValueError):
            Identifier.from_str(invalid_identifier_str)


def test_identifier_str(identifier):
    assert str(identifier) == "sub-001_all_eeg_s1_r1_e1"


def test_identifier_eq(identifier):
    other = Identifier("sub-001", "all_eeg", "s1", "r1", "e1")
    assert identifier == other


def test_identifier_neq(identifier):
    other = Identifier("sub-002", "all_eeg", "s1", "r1", "e1")
    assert identifier != other


def test_identifier_to_dir_raw(identifier, mock_dataset):
    with mock.patch(
        "hallmonitor.hmutils.get_variable_datatype"
    ) as mock_get_variable_datatype:
        datatype = "mockdtype"
        mock_get_variable_datatype.return_value = datatype
        path = identifier.to_dir(mock_dataset, is_raw=True)
        assert path == os.path.join(
            mock_dataset, "sourcedata", "raw", "s1_r1", datatype, "sub-001", ""
        )


def test_identifier_to_dir_checked(identifier, mock_dataset):
    with mock.patch(
        "hallmonitor.hmutils.get_variable_datatype"
    ) as mock_get_variable_datatype:
        datatype = "mockdtype"
        mock_get_variable_datatype.return_value = datatype
        path = identifier.to_dir(mock_dataset, is_raw=False)
        assert path == os.path.join(
            mock_dataset, "sourcedata", "checked", "sub-001", "s1_r1", datatype, ""
        )


def test_identifier_to_detailed_str(identifier, mock_dataset):
    with (
        mock.patch(
            "hallmonitor.hmutils.get_variable_datatype"
        ) as mock_get_variable_datatype,
        mock.patch("hallmonitor.hmutils.is_combination_var") as mock_is_combination_var,
        mock.patch("hallmonitor.hmutils.is_variable_encrypted") as mock_is_encrypted,
    ):
        datatype = "mockdtype"
        mock_get_variable_datatype.return_value = datatype
        mock_is_encrypted.return_value = False

        # test with combination var
        mock_is_combination_var.return_value = True
        detailed_str = identifier.to_detailed_str(mock_dataset)
        assert detailed_str == f"sub-001/all_eeg/s1_r1_e1 ({datatype}) (combination)"

        # test with non-combination var
        mock_is_combination_var.return_value = False
        detailed_str = identifier.to_detailed_str(mock_dataset)
        assert detailed_str == f"sub-001/all_eeg/s1_r1_e1 ({datatype})"
