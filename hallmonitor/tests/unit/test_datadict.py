import os
from unittest import mock

import pandas as pd
import pytest

from hallmonitor.hmutils import datadict_has_changes, get_datadict


@pytest.fixture
def dataset(tmp_path):
    dataset_path = tmp_path / "mock_dataset"
    os.makedirs(dataset_path)
    return str(dataset_path)


# -- test get_datadict() --


@pytest.fixture()
def datadict():
    df = pd.DataFrame(
        {
            "col1": [1, 5, 7],
            "col2": [2, 3, 5],
            "variable": ["var1", "var3", "var5"],
            "type": ["int", "str", "float"],
            "description": ["Variable 1", "Variable 3", "Variable 5"],
        }
    )
    return df


@pytest.fixture
def mock_read_csv(monkeypatch, datadict):
    monkeypatch.setattr("pandas.read_csv", lambda _: datadict)


@pytest.fixture
def mock_local_datadict(monkeypatch, dataset, datadict):
    datadict_path = "datadict.csv"
    datadict.to_csv(os.path.join(dataset, datadict_path))
    monkeypatch.setattr("hallmonitor.hmutils.DATADICT_SUBPATH", datadict_path)


def test_get_datadict_valid(dataset, mock_read_csv):
    df = get_datadict(dataset, use_cache=False)
    assert list(df.col1) == [1, 5, 7]
    assert list(df.col2) == [2, 3, 5]


def test_get_datadict_DATADICT_SUBPATH(dataset):
    # make sure get_datadict() uses DATADICT_SUBPATH by varying its value
    mock_subpaths = ["mock_subpath", "another_subpath", "ndclab"]
    for subpath in mock_subpaths:
        with (
            mock.patch("hallmonitor.hmutils.DATADICT_SUBPATH", subpath),
            mock.patch("pandas.read_csv") as read_csv,
        ):
            get_datadict(dataset, use_cache=False)
            read_csv.assert_called_once_with(os.path.join(dataset, subpath))


def test_get_datadict_file_does_not_exist(dataset):
    with pytest.raises(FileNotFoundError):
        get_datadict(dataset, use_cache=False)


def test_get_datadict_uses_index_col(dataset, mock_local_datadict):
    df = get_datadict(dataset, "col1", use_cache=False)
    assert list(df.index) == [1, 5, 7]
    assert "col1" not in df.columns

    df = get_datadict(dataset, "col2", use_cache=False)
    assert list(df.index) == [2, 3, 5]
    assert "col2" not in df.columns


def test_get_datadict_index_col_does_not_exist(dataset, mock_local_datadict):
    with pytest.raises(ValueError):
        get_datadict(dataset, "invalid_col", use_cache=False)


def test_get_datadict_no_index_col(dataset, mock_local_datadict):
    # ensure default index if index_col is None
    df = get_datadict(dataset, index_col=None, use_cache=False)
    assert list(df.index) == [0, 1, 2]

    # ensure default index if index_col not passed
    df = get_datadict(dataset, use_cache=False)
    assert list(df.index) == [0, 1, 2]


# -- test datadict_has_changes() --


@pytest.fixture
def latest_datadict():
    df = pd.DataFrame(
        {
            "variable": ["var1", "var2"],
            "type": ["int", "float"],
            "description": ["Variable 1", "Variable 2"],
        }
    ).set_index("variable")
    return df


@pytest.fixture
def matching_datadict():
    # exact copy of latest_datadict
    df = pd.DataFrame(
        {
            "variable": ["var1", "var2"],
            "type": ["int", "float"],
            "description": ["Variable 1", "Variable 2"],
        }
    ).set_index("variable")
    return df


@pytest.fixture
def mock_local_data_dictionaries(
    monkeypatch,
    dataset,
    matching_datadict,
    latest_datadict,
):
    dd_path = "datadict.csv"
    latest_dd_path = "latest_datadict.csv"

    matching_datadict.to_csv(os.path.join(dataset, dd_path))
    latest_datadict.to_csv(os.path.join(dataset, latest_dd_path))

    monkeypatch.setattr("hallmonitor.hmutils.DATADICT_SUBPATH", dd_path)
    monkeypatch.setattr("hallmonitor.hmutils.DATADICT_LATEST_SUBPATH", latest_dd_path)


def test_datadict_has_changes_no_change(mock_local_data_dictionaries, dataset):
    assert not datadict_has_changes(dataset)


def test_datadict_has_changes_change(mock_local_data_dictionaries, dataset):
    # introduce a change to the datadict
    dd_path = os.path.join(dataset, "datadict.csv")
    dd_df = pd.read_csv(dd_path, index_col="variable")
    dd_df.at["var1", "description"] = "Modified Variable 1"
    dd_df.to_csv(dd_path)

    assert datadict_has_changes(dataset)


def test_datadict_has_changes_dd_missing(mock_local_data_dictionaries, dataset):
    dd_path = os.path.join(dataset, "datadict.csv")
    os.remove(dd_path)

    with pytest.raises(FileNotFoundError, match="Data dictionary not found"):
        datadict_has_changes(dataset)


def test_datadict_has_changes_latest_dd_missing(mock_local_data_dictionaries, dataset):
    latest_dd_path = os.path.join(dataset, "latest_datadict.csv")
    os.remove(latest_dd_path)

    with pytest.raises(FileNotFoundError, match="Latest data dictionary not found"):
        datadict_has_changes(dataset)


def test_datadict_has_changes_latest_dd_empty(mock_local_data_dictionaries, dataset):
    latest_dd_path = os.path.join(dataset, "latest_datadict.csv")
    pd.DataFrame().to_csv(latest_dd_path)
    assert datadict_has_changes(dataset)


def test_datadict_has_changes_dd_empty(mock_local_data_dictionaries, dataset):
    dd_path = os.path.join(dataset, "datadict.csv")
    pd.DataFrame().to_csv(dd_path)
    assert datadict_has_changes(dataset)


def test_datadict_has_changes_both_empty(mock_local_data_dictionaries, dataset):
    dd_path = os.path.join(dataset, "datadict.csv")
    latest_dd_path = os.path.join(dataset, "latest_datadict.csv")
    pd.DataFrame().to_csv(dd_path)
    pd.DataFrame().to_csv(latest_dd_path)
    assert not datadict_has_changes(dataset)


def test_datadict_has_changes_different_columns(mock_local_data_dictionaries, dataset):
    dd_path = os.path.join(dataset, "datadict.csv")
    datadict = pd.DataFrame(
        {
            "variable": ["var1", "var2"],
            "type": ["int", "float"],
            "label": ["Label 1", "Label 2"],  # new column "label"
        }
    ).set_index("variable")
    datadict.to_csv(dd_path)

    assert datadict_has_changes(dataset)


def test_datadict_has_changes_different_variables(
    mock_local_data_dictionaries, dataset
):
    latest_dd_path = os.path.join(dataset, "latest_datadict.csv")
    latest_datadict = pd.DataFrame(
        {
            "variable": ["var1", "var3"],  # different set of variables
            "type": ["int", "str"],
            "description": ["Variable 1", "Variable 3"],
        }
    ).set_index("variable")
    latest_datadict.to_csv(latest_dd_path)

    assert datadict_has_changes(dataset)


def test_datadict_has_changes_partial_match(mock_local_data_dictionaries, dataset):
    latest_dd_path = os.path.join(dataset, "latest_datadict.csv")
    latest_datadict = pd.DataFrame(
        {
            "variable": ["var1", "var2", "var4"],  # Added var4
            "type": ["int", "float", "str"],
            "description": ["Variable 1", "Variable 2", "Variable 4"],
        }
    ).set_index("variable")
    latest_datadict.to_csv(latest_dd_path)

    assert datadict_has_changes(dataset)


def test_datadict_has_changes_dd_has_new_column(mock_local_data_dictionaries, dataset):
    dd_path = os.path.join(dataset, "datadict.csv")
    datadict = pd.read_csv(dd_path, index_col="variable")
    datadict["new_column"] = ["data1", "data2"]
    datadict.to_csv(dd_path)

    assert datadict_has_changes(dataset)
