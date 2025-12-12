import os
import re

import pandas as pd
import pytest

from hallmonitor.hmutils import (
    Identifier,
    get_expected_files,
    get_expected_identifiers,
)


@pytest.fixture
def mock_Identifier_re(monkeypatch):
    id_pattern = r"(?P<subject>[a-zA-Z0-9]+)_(?P<var>[a-zA-Z0-9]+)_(?P<sre>(?:[a-zA-Z0-9]+_?){3})"
    monkeypatch.setattr(
        "hallmonitor.hmutils.Identifier.PATTERN", re.compile(id_pattern)
    )


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


@pytest.fixture
def mock_dataset(tmp_path, mock_datadict, mock_Identifier_re):
    dataset_path = tmp_path / "mock_dataset"
    os.makedirs(dataset_path)
    return str(dataset_path)


# -- test get_expected_files() --


def test_get_expected_files_valid_string(mock_dataset):
    identifier = "subject1_eeg_s1_r1_e1"

    # The mocked data dictionary specifies that eeg
    # has expected extensions ".eeg, .vmrk, .vhdr"
    expected_files = {
        "subject1_eeg_s1_r1_e1.eeg",
        "subject1_eeg_s1_r1_e1.vmrk",
        "subject1_eeg_s1_r1_e1.vhdr",
    }

    assert set(get_expected_files(mock_dataset, identifier)) == expected_files


def test_get_expected_files_invalid_string(mock_dataset):
    invalid_identifier = "invalid_identifier"

    with pytest.raises(ValueError, match="Could not build Identifier"):
        get_expected_files(mock_dataset, invalid_identifier)


def test_get_expected_files_valid_Identifier(mock_dataset):
    identifier = Identifier("subject1", "eeg", "s1", "r1", "e1")

    expected_files = {
        "subject1_eeg_s1_r1_e1.eeg",
        "subject1_eeg_s1_r1_e1.vmrk",
        "subject1_eeg_s1_r1_e1.vhdr",
    }

    assert set(get_expected_files(mock_dataset, identifier)) == expected_files


def test_get_expected_files_no_extensions(mock_dataset):
    # var3 has no extensions in the mock data dictionary
    identifier = "subject1_var3_s1_r1_e1"
    assert get_expected_files(mock_dataset, identifier) == []


# -- test get_expected_identifiers() --


def test_get_expected_identifiers_valid(mock_dataset):
    present_ids = ["subject1_eeg_s1_r1_e1", "subject2_eeg_s2_r1_e1"]

    # Based on the mock data dictionary, eeg and psychopy are associated with visit data
    # So, we expect combinations of subject1, subject2 with eeg and psychopy for the same sessions
    expected_ids = [
        Identifier("subject1", "eeg", "s1", "r1", "e1"),
        Identifier("subject1", "psychopy", "s1", "r1", "e1"),
        Identifier("subject2", "eeg", "s2", "r1", "e1"),
        Identifier("subject2", "psychopy", "s2", "r1", "e1"),
    ]

    result = get_expected_identifiers(mock_dataset, present_ids)

    assert len(result) == len(expected_ids)

    for id in expected_ids:
        assert id in result


def test_get_expected_identifiers_invalid_present_ids(mock_dataset):
    with pytest.raises(ValueError):
        get_expected_identifiers(mock_dataset, ["invalid_identifier"])


def test_get_expected_identifiers_no_visit_vars(mock_dataset, monkeypatch):
    # Mock data dictionary without any visit variables
    def mock_get_datadict_no_visit_vars(dataset):
        return pd.DataFrame(
            {
                "variable": ["var1", "var2"],  # No "visit_data"
                "expectedFileExt": ['".eeg,.vmrk,.vhdr"', '".txt,.csv"'],
                "dataType": ["other", "other"],  # Not associated with visit_data
                "provenance": ["", ""],
            }
        )

    monkeypatch.setattr(
        "hallmonitor.hmutils.get_datadict", mock_get_datadict_no_visit_vars
    )

    # Present identifiers, but since no variables are associated with visit_data,
    # we expect an empty list of expected identifiers
    present_ids = ["subject1_var1_s1_r1_e1", "subject2_var2_s2_r1_e1"]

    result = get_expected_identifiers(mock_dataset, present_ids)
    assert result == []


def test_get_expected_identifiers_no_present_ids(mock_dataset):
    result = get_expected_identifiers(mock_dataset, [])
    assert result == []
