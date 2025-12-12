import re
from unittest import mock

import pytest

from hallmonitor.hmutils import get_psychopy_errors


@pytest.fixture
def mock_identifier_re(monkeypatch):
    # mock valid Identifier regex
    mock_re = (
        r"(?P<id>(?P<subject>sub-\d+)(?:_(?P<var>[\w-]+))?_(?P<sre>s\d+_r\d+_e\d+))"
    )
    monkeypatch.setattr("hallmonitor.hmutils.Identifier.PATTERN", re.compile(mock_re))
    return mock_re


@pytest.fixture
def mock_file_re(monkeypatch, mock_identifier_re):
    # mock valid filename regex
    mock_re = mock_identifier_re + r"\..*"
    monkeypatch.setattr("hallmonitor.hmutils.FILE_RE", mock_re)
    return mock_re


@pytest.fixture
def mock_logger():
    # Mock logger object
    return mock.Mock()


@pytest.fixture
def mock_new_error_record(monkeypatch):
    def mock_error_record(
        logger, dataset, identifier, error_type, error_details, *args, **kwargs
    ):
        return {
            "error_type": error_type,
            "message": error_details,
        }

    monkeypatch.setattr("hallmonitor.hmutils.new_error_record", mock_error_record)


@pytest.fixture
def dataset(tmp_path):
    # Temporary dataset directory
    return str(tmp_path)


@pytest.fixture
def empty_files_list():
    return []


@pytest.fixture
def valid_files_list(tmp_path):
    id_num = "001"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"

    # Write contents to the files
    csv_file.write_text(f"id\n{id_num}")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()

    return [str(csv_file), str(log_file), str(psydat_file)]


@pytest.fixture
def non_utf8_encoded_files(tmp_path):
    id_num = "001"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"

    csv_file.write_bytes("id\n001".encode("latin1"))
    log_file.write_bytes(
        "saved data to 'sub-001_s1_r1_e1.csv'\nsaved data to 'sub-001_s1_r1_e1.psydat'".encode(
            "latin1"
        )
    )

    return [str(csv_file), str(log_file), str(psydat_file)]


@pytest.fixture
def files_in_nested_directories(tmp_path):
    id_num = "001"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()

    csv_file = nested_dir / f"{base_filename}.csv"
    log_file = nested_dir / f"{base_filename}.log"
    psydat_file = nested_dir / f"{base_filename}.psydat"

    csv_file.write_text(f"id\n{id_num}")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()

    return [str(csv_file), str(log_file), str(psydat_file)]


def test_empty_files_list(mock_logger, dataset, empty_files_list):
    errors = get_psychopy_errors(mock_logger, dataset, empty_files_list)
    assert errors == []


def test_invalid_file_name_format(mock_logger, dataset, tmp_path, mock_file_re):
    invalid_file = tmp_path / "invalid_filename.csv"
    invalid_file.write_text("id\n001")
    files = [str(invalid_file)]
    with pytest.raises(ValueError, match="Invalid Psychopy file name"):
        get_psychopy_errors(mock_logger, dataset, files)


def test_valid_files_with_matching_ids(
    mock_logger, dataset, valid_files_list, mock_file_re
):
    errors = get_psychopy_errors(mock_logger, dataset, valid_files_list)
    assert errors == []


def test_missing_log_file(mock_logger, dataset, valid_files_list, mock_file_re):
    files = [f for f in valid_files_list if not f.endswith(".log")]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert errors == []


def test_missing_csv_file(
    mock_logger, dataset, valid_files_list, mock_new_error_record, mock_file_re
):
    files = [f for f in valid_files_list if not f.endswith(".csv")]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert len(errors) == 0


def test_missing_psydat_file(
    mock_logger, dataset, valid_files_list, mock_new_error_record, mock_file_re
):
    files = [f for f in valid_files_list if not f.endswith(".psydat")]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert len(errors) == 0


def test_csv_file_missing_id_column(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"
    csv_file.write_text("other_column\nvalue")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    with pytest.raises(ValueError, match="No ID column found in .csv file"):
        get_psychopy_errors(mock_logger, dataset, files)


def test_nan_values_in_id_column(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"
    csv_file.write_text("id\nNaN\nNaN")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert len(errors) == 1
    assert "NaN value seen under ID in .csv file" in errors[0]["message"]


def test_mismatched_id_in_csv_file(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    mismatched_id = "999"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"
    csv_file.write_text(f"id\n{mismatched_id}")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert len(errors) == 1
    assert (
        f"ID value(s) [{mismatched_id}] in csvfile different from ID in filename ({id_num})"
        in errors[0]["message"]
    )


def test_extra_files_in_files_list(
    mock_logger,
    dataset,
    valid_files_list,
    tmp_path,
    mock_new_error_record,
    mock_file_re,
):
    extra_file = tmp_path / "extra_file.txt"
    extra_file.write_text("Extra content")
    files = valid_files_list + [str(extra_file)]
    with pytest.raises(
        ValueError, match=re.escape(f"Invalid Psychopy file name(s) {extra_file}")
    ):
        get_psychopy_errors(mock_logger, dataset, files)


def test_whitespace_in_filenames_in_log_references(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_filename = f" {base_filename}.csv "
    psydat_filename = f" '{base_filename}.psydat' "
    csv_file = tmp_path / csv_filename.strip()
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / psydat_filename.strip().strip("'")
    csv_file.write_text(f"id\n{id_num}")
    log_file.write_text(
        f"saved data to '{csv_filename}'\nsaved data to {psydat_filename}"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert errors == []


def test_case_sensitivity_in_file_extensions(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.CSV"
    log_file = tmp_path / f"{base_filename}.LOG"
    psydat_file = tmp_path / f"{base_filename}.PSYDAT"
    csv_file.write_text(f"id\n{id_num}")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert errors == []


def test_case_variations_in_id_column_name(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"
    csv_file.write_text(f"ID\n{id_num}")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    with pytest.raises(ValueError, match="No ID column found in .csv file"):
        get_psychopy_errors(mock_logger, dataset, files)


def test_special_characters_in_filenames(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    base_filename = f"sub {id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"
    csv_file.write_text(f"id\n{id_num}")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    with pytest.raises(ValueError, match="Invalid Psychopy file name"):
        get_psychopy_errors(mock_logger, dataset, files)


def test_non_utf8_encoded_files(
    mock_logger, dataset, mock_new_error_record, mock_file_re, non_utf8_encoded_files
):
    errors = get_psychopy_errors(mock_logger, dataset, non_utf8_encoded_files)
    assert errors == []


def test_files_in_nested_directories(
    mock_logger,
    dataset,
    mock_new_error_record,
    mock_file_re,
    files_in_nested_directories,
):
    errors = get_psychopy_errors(mock_logger, dataset, files_in_nested_directories)
    assert errors == []


def test_csv_file_with_extra_columns(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"
    csv_file.write_text(f"id,extra_col\n{id_num},value")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert errors == []


def test_mismatched_sub_id_filename_participant(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    mismatched_id = "999"
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"
    csv_file.write_text(f"participant\n{mismatched_id}")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert len(errors) == 1
    assert (
        f"ID value(s) [{mismatched_id}] in csvfile different from ID in filename ({id_num})"
        in errors[0]["message"]
    )


def test_multiple_filename_participant_mismatches(
    mock_logger, dataset, tmp_path, mock_new_error_record, mock_file_re
):
    id_num = "001"
    mismatched_ids = ["999", "002"]
    base_filename = f"sub-{id_num}_s1_r1_e1"
    csv_file = tmp_path / f"{base_filename}.csv"
    log_file = tmp_path / f"{base_filename}.log"
    psydat_file = tmp_path / f"{base_filename}.psydat"
    newline = "\n"  # no backslashes in f-strings
    csv_file.write_text(f"participant{newline}{newline.join(mismatched_ids)}")
    log_file.write_text(
        f"saved data to '{csv_file.name}'\nsaved data to '{psydat_file.name}'"
    )
    psydat_file.touch()
    files = [str(csv_file), str(log_file), str(psydat_file)]
    errors = get_psychopy_errors(mock_logger, dataset, files)
    assert len(errors) == 1
    assert (
        f"ID value(s) [{', '.join(mismatched_ids)}] in csvfile different from ID in filename ({id_num})"
        in errors[0]["message"]
    )
