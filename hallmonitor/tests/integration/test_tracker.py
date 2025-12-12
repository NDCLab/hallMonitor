import logging
import os
import re
from io import StringIO
from unittest import mock

import pandas as pd
import pytest

from hallmonitor.tests.integration.base_cases import TrackerTestCase


class BaseUpdateTrackerTestCase(TrackerTestCase):
    """
    Validates the state of the base central tracker, with no modifications
    made to subject data.
    """

    case_name = "BaseUpdateTrackerTestCase"
    description = "Ensures that update_tracker runs correctly with no modifications."
    conditions = ["No modifications made to base subject files"]
    expected_output = "update_tracker runs without issues."

    def modify(self, base_files):
        return base_files.copy()

    def validate(self):
        try:
            self.run_update_tracker(child=True, session="s1")
            self.run_update_tracker(child=True, session="s2")
            self.run_update_tracker(child=True, session="s3")
        except Exception as err:
            raise AssertionError from err

        tracker_path = os.path.join(
            self.case_dir,
            "data-monitoring",
            f"central-tracker_{self.case_name}.csv",
        )
        assert os.path.exists(tracker_path)

        tracker_df = pd.read_csv(tracker_path)
        assert not tracker_df.empty

        # only our subject should be present
        assert len(tracker_df.index) == 1
        assert tracker_df["id"].astype(int).iloc[0] == self.sub_id

        # helpful to break out our subject's row as a separate variable
        sub_row = tracker_df[tracker_df["id"].astype(int) == self.sub_id].iloc[0]

        # check consent and assent separately, since they don't follow
        # the same pattern as the other columns
        assert sub_row["consent"] == 1
        assert sub_row["assent"] == 1

        # extract only the columns that follow the `variable_s_r_e` pattern
        exclude_cols = {"id", "consent", "assent"}
        cols = tracker_df.columns
        cols = cols[~cols.isin(exclude_cols)].tolist()

        expected_sre = ["s1_r1_e1", "s2_r1_e1", "s3_r1_e1"]
        expected_vars = [
            # ordinary variables
            "arrow-alert-v1-1_psychopy",
            "arrow-alert-v1-2_psychopy",
            "all_audacity",
            "all_zoom",
            "all_eeg",
            "all_digi",
            # combination variables
            "arrow-alert_psychopy",
            # status variables
            "iqs_status",
            "bbs_status",
            # data variables
            "iqs_data",
            "bbs_data",
            # REDCap variables
            "abq",
            "psb",
        ]

        expected_cols = set()
        for var in expected_vars:
            for sre in expected_sre:
                expected_cols.add(f"{var}_{sre}")

        # no extra or missing columns
        assert set(cols) == expected_cols

        # all values should be 1 for the base case

        failed_cols = {col for col in cols if sub_row[col] != 1}
        assert len(failed_cols) == 0, f"Failed column(s): {', '.join(failed_cols)}"


def test_base_update_tracker(request):
    BaseUpdateTrackerTestCase.run_test_case(request)


class DeviationCheckedUpdateTrackerTestCase(BaseUpdateTrackerTestCase):
    """
    Validates that addition of a deviation.txt file for a file that has been
    moved to sourcedata/checked/ does not affect tracker generation.
    """

    case_name = "DeviationCheckedUpdateTrackerTestCase"
    description = (
        "Ensures that presence of deviation.txt file doesn't disturb tracker creation."
    )
    conditions = [
        "File name modified to be incorrect",
        "Deviation.txt file added",
        "File moved to sourcedata/checked",
    ]
    expected_output = "update_tracker runs without issues."

    def modify(self, base_files):
        modified_files = base_files.copy()

        identifier = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1"

        # rename file incorrectly
        old_name = f"{identifier}.csv"
        new_name = old_name.replace(".csv", "_deviation.csv")
        # do once for raw and once for checked
        if not self.replace_file_name(modified_files, old_name, new_name, True):
            raise FileNotFoundError(f"Could not find basename {new_name} in raw")
        if not self.replace_file_name(modified_files, old_name, new_name, False):
            raise FileNotFoundError(f"Could not find basename {new_name} in checked")

        # add deviation.txt to raw/ and checked/
        deviation_file = f"{identifier}_deviation.txt"
        deviation_content = "Test case deviation"
        deviation_raw = self.build_path("s1_r1", "psychopy", deviation_file, True)
        deviation_checked = self.build_path("s1_r1", "psychopy", deviation_file, False)
        modified_files[deviation_raw] = deviation_content
        modified_files[deviation_checked] = deviation_content

        return modified_files


def test_deviation_checked_update_tracker(request):
    DeviationCheckedUpdateTrackerTestCase.run_test_case(request)


class DeviationNoCheckedUpdateTrackerTestCase(BaseUpdateTrackerTestCase):
    """
    Validates that addition of a deviation.txt file for a file that has not been
    moved to sourcedata/checked/ does not affect tracker generation.
    """

    case_name = "DeviationNoCheckedUpdateTrackerTestCase"
    description = (
        "Ensures that presence of deviation.txt file doesn't disturb tracker creation."
    )
    conditions = [
        "File name modified to be incorrect",
        "Deviation.txt file added",
        "File not moved to sourcedata/checked",
    ]
    expected_output = "update_tracker runs without issues."

    def modify(self, base_files):
        modified_files = base_files.copy()

        # rename file only in sourcedata/raw/
        filename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1.csv"
        old_name = os.path.join(
            "sourcedata", "raw", "s1_r1", "psychopy", f"sub-{self.sub_id}", filename
        )
        new_name = old_name.replace(".csv", "_deviation.csv")
        modified_files[new_name] = modified_files.pop(old_name)

        # add deviation.txt to raw/
        deviation_file = f"{filename}_deviation.txt"
        deviation_file = self.build_path("s1_r1", "psychopy", deviation_file, True)
        modified_files[deviation_file] = "Test case deviation"

        return modified_files


def test_deviation_no_checked_update_tracker(request):
    DeviationNoCheckedUpdateTrackerTestCase.run_test_case(request)


class BBSDataZeroMissingDatatypeFolderTestCase(TrackerTestCase):
    """
    Validates that a missing datatype folder results in a 0 in the central tracker.
    """

    case_name = "BBSDataZeroMissingDatatypeFolderTestCase"
    description = (
        "Ensures that a missing datatype folder results in a 0 in the central tracker."
    )
    conditions = ["Missing bbs_data folder for s1_r1_e1"]
    expected_output = "update_tracker runs without issues, and bbs_data_s1_r1_e1 is 0."

    def modify(self, base_files):
        modified_files = base_files.copy()

        psychopy_dir = os.path.dirname(self.build_path("s1_r1", "psychopy", "", True))
        modified_files = {
            path: contents
            for path, contents in modified_files.items()
            if not path.startswith(psychopy_dir)
        }

        return modified_files

    def validate(self):
        from hallmonitor import app

        args = self.get_standard_args()
        args.raw_only = True
        args.no_qa = True

        try:
            app.main(args)
        except Exception as err:
            raise AssertionError from err

        tracker_path = os.path.join(
            self.case_dir,
            "data-monitoring",
            f"central-tracker_{self.case_name}.csv",
        )
        tracker_df = pd.read_csv(tracker_path)

        sub_row = tracker_df[tracker_df["id"].astype(int) == self.sub_id].iloc[0]

        # we deleted the files for this session
        assert sub_row["bbs_data_s1_r1_e1"] == 0

        # these sessions should have no problems
        assert sub_row["bbs_data_s2_r1_e1"] == 1
        assert sub_row["bbs_data_s3_r1_e1"] == 1


def test_bbs_data_zero_missing_datatype_folder(request):
    BBSDataZeroMissingDatatypeFolderTestCase.run_test_case(request)


class BBSDataZeroMissingDataTestCase(TrackerTestCase):
    """
    Validates that a present datatype folder with no data results in a 0 in the central tracker.
    """

    case_name = "BBSDataZeroMissingDataTestCase"
    description = "Ensures that a present datatype folder with no data results in a 0 in the central tracker."
    conditions = ["Empty psychopy folder for s1_r1_e1"]
    expected_output = "update_tracker runs without issues, and bbs_data_s1_r1_e1 is 0."

    def modify(self, base_files):
        modified_files = base_files.copy()

        psychopy_dir = os.path.dirname(self.build_path("s1_r1", "psychopy", "", True))
        modified_files = {
            path: contents
            for path, contents in modified_files.items()
            if not path.startswith(psychopy_dir)
        }

        # add back the empty psychopy folder
        modified_files[self.build_path("s1_r1", "psychopy", "", True)] = ""

        return modified_files

    def validate(self):
        from hallmonitor import app

        args = self.get_standard_args()
        args.raw_only = True
        args.no_qa = True

        try:
            app.main(args)
        except Exception as err:
            raise AssertionError from err

        tracker_path = os.path.join(
            self.case_dir,
            "data-monitoring",
            f"central-tracker_{self.case_name}.csv",
        )
        tracker_df = pd.read_csv(tracker_path)

        sub_row = tracker_df[tracker_df["id"].astype(int) == self.sub_id].iloc[0]

        # we deleted the files, but not the folder, for this session
        assert sub_row["bbs_data_s1_r1_e1"] == 0

        # these sessions should have no problems
        assert sub_row["bbs_data_s2_r1_e1"] == 1
        assert sub_row["bbs_data_s3_r1_e1"] == 1


def test_bbs_data_zero_missing_data(request):
    BBSDataZeroMissingDataTestCase.run_test_case(request)


class BBSDataZeroNoDataFileTestCase(TrackerTestCase):
    """
    Validates that a present datatype folder with a no-data.txt file (and nothing else) results in a 0 in the central tracker."""

    case_name = "BBSDataZeroNoDataFileTestCase"
    description = "Ensures that a present datatype folder with only a no-data.txt file results in a 0 in the central tracker."
    conditions = [
        "no-data.txt file present in psychopy folder for s1_r1_e1, all other files deleted"
    ]
    expected_output = "update_tracker runs without issues, and bbs_data_s1_r1_e1 is 0."

    def modify(self, base_files):
        modified_files = base_files.copy()

        psychopy_dir = os.path.dirname(self.build_path("s1_r1", "psychopy", "", True))
        modified_files = {
            path: contents
            for path, contents in modified_files.items()
            if not path.startswith(psychopy_dir)
        }

        # add the no-data.txt file
        no_data_file = self.build_path("s1_r1", "psychopy", "no-data.txt", True)
        modified_files[no_data_file] = "Data omitted to test update_tracker."

        return modified_files

    def validate(self):
        from hallmonitor import app

        args = self.get_standard_args()
        args.raw_only = True
        args.no_qa = True
        args.legacy_exceptions = True  # no-data.txt without identifier

        try:
            app.main(args)
        except Exception as err:
            raise AssertionError from err

        tracker_path = os.path.join(
            self.case_dir,
            "data-monitoring",
            f"central-tracker_{self.case_name}.csv",
        )
        tracker_df = pd.read_csv(tracker_path)

        sub_row = tracker_df[tracker_df["id"].astype(int) == self.sub_id].iloc[0]

        # no-data.txt present for this session
        assert sub_row["bbs_data_s1_r1_e1"] == 0

        # these sessions should have no problems
        assert sub_row["bbs_data_s2_r1_e1"] == 1
        assert sub_row["bbs_data_s3_r1_e1"] == 1


def test_bbs_data_zero_no_data_file(request):
    BBSDataZeroNoDataFileTestCase.run_test_case(request)


class BBSDataZeroIncorrectDataTestCase(TrackerTestCase):
    """
    Validates that the bbs_data column updates with a "0"
    if an expected BBS datatype folder exists but contains incorrect data.
    """

    case_name = "BBSDataZeroIncorrectDataTestCase"
    description = "Ensures that bbs_data_s1_r1_e1 is 0 when incorrect data is present."
    conditions = ["Incorrect data present in psychopy folder for s1_r1_e1"]
    expected_output = "update_tracker runs without issues, and bbs_data_s1_r1_e1 is 0."

    def modify(self, base_files):
        modified_files = base_files.copy()

        old_var = "arrow-alert-v1-1_psychopy"
        old_filename = f"sub-{self.sub_id}_{old_var}_s1_r1_e1.csv"

        new_var = "incorrect_psychopy"
        new_filename = old_filename.replace(old_var, new_var)

        # rename file to be incorrect
        old_path = self.build_path("s1_r1", "psychopy", old_filename, True)
        new_path = self.build_path("s1_r1", "psychopy", new_filename, True)
        modified_files[new_path] = modified_files.pop(old_path)

        return modified_files

    def validate(self):
        from hallmonitor import app

        args = self.get_standard_args()
        args.raw_only = True
        args.no_qa = True

        try:
            app.main(args)
        except Exception as err:
            raise AssertionError from err

        tracker_path = os.path.join(
            self.case_dir,
            "data-monitoring",
            f"central-tracker_{self.case_name}.csv",
        )
        tracker_df = pd.read_csv(tracker_path)

        sub_row = tracker_df[tracker_df["id"].astype(int) == self.sub_id].iloc[0]

        # failing identifier present for this session
        assert sub_row["bbs_data_s1_r1_e1"] == 0

        # these sessions should have no problems
        assert sub_row["bbs_data_s2_r1_e1"] == 1
        assert sub_row["bbs_data_s3_r1_e1"] == 1


def test_bbs_data_zero_incorrect_data(request):
    BBSDataZeroIncorrectDataTestCase.run_test_case(request)


class BBSDataZeroDeviationFileTestCase(TrackerTestCase):
    """"""

    case_name = "BBSDataOneDeviationFileTestCase"
    description = (
        "Ensures that bbs_data_s1_r1_e1 is 0 even when a deviation.txt file is present."
    )
    conditions = [
        "Deviation.txt file present in psychopy folder for s1_r1_e1",
        "Data is in an incorrect state",
    ]
    expected_output = "update_tracker runs without issues, and bbs_data_s1_r1_e1 is 0."

    def modify(self, base_files):
        modified_files = base_files.copy()

        # change the filename to be incorrect
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1.csv"
        old_path = self.build_path("s1_r1", "psychopy", old_name, True)

        new_name = "badfilename.csv"
        new_path = old_path.replace(old_name, new_name)
        modified_files[new_path] = modified_files.pop(old_path)

        # add our deviation.txt file
        deviation_file = self.build_path("s1_r1", "psychopy", "deviation.txt", True)
        modified_files[deviation_file] = "Test case deviation"

        return modified_files

    def validate(self):
        from hallmonitor import app

        args = self.get_standard_args()
        args.raw_only = True
        args.no_qa = True
        args.legacy_exceptions = True  # deviation.txt without identifier

        try:
            app.main(args)
        except Exception as err:
            raise AssertionError from err

        tracker_path = os.path.join(
            self.case_dir,
            "data-monitoring",
            f"central-tracker_{self.case_name}.csv",
        )
        tracker_df = pd.read_csv(tracker_path)

        sub_row = tracker_df[tracker_df["id"].astype(int) == self.sub_id].iloc[0]

        # we should have an error with session 1 despite the deviation.txt file
        assert sub_row["bbs_data_s1_r1_e1"] == 0
        assert sub_row["bbs_data_s2_r1_e1"] == 1
        assert sub_row["bbs_data_s3_r1_e1"] == 1


def test_bbs_data_one_deviation_file(request):
    BBSDataZeroDeviationFileTestCase.run_test_case(request)


class DuplicateREDCapColumnsTestCase(TrackerTestCase):
    """
    Validates that duplicate columns in REDCap files are caught.
    """

    case_name = "DuplicateREDCapColumnsTestCase"
    description = "Ensures that duplicate columns in REDCap files are caught."
    conditions = ["Duplicate columns in REDCap files"]
    expected_output = "update_tracker raises a RuntimeError due to duplicate columns."

    duped_col = "consent_complete"

    def modify(self, base_files):
        modified_files = base_files.copy()

        rc_cols = [
            "record_id",
            "bbsratrk_acid_s1_r1_e1",
            self.duped_col,
            self.duped_col,
        ]
        rc_data = [[1, self.sub_id, 2, 2]]
        redcap_df = pd.DataFrame(columns=rc_cols, data=rc_data)

        redcap_subpath = os.path.join(
            "sourcedata", "checked", "redcap", self.build_rc_name("consent")
        )
        modified_files[redcap_subpath] = redcap_df.to_csv(index=False)

        return modified_files

    def validate(self):
        from hallmonitor import app

        args = self.get_standard_args()
        args.raw_only = True
        args.no_qa = True

        with (
            mock.patch.object(logging.Logger, "error") as mock_error,
            pytest.raises(RuntimeError, match=r"Could not update tracker.*"),
        ):
            app.main(args)

        assert mock_error.call_count == 3, mock_error._calls_repr()

        error_re = re.compile(r".*[Dd]uplicate column.*")

        for call in mock_error.call_args_list:
            args = list(map(str, call.args))
            error_matches = any(error_re.match(arg) for arg in args)
            col_matches = any(self.duped_col in arg for arg in args)

            assert error_matches and col_matches, f"Unexpected error: {call.args}"


def test_duplicate_redcap_columns(request):
    DuplicateREDCapColumnsTestCase.run_test_case(request)


class MissingREDCapColumnTestCase(TrackerTestCase):
    """
    Validates that missing columns in REDCap files are caught.
    """

    case_name = "MissingREDCapColumnTestCase"
    description = "Ensures that missing columns in REDCap files are caught."
    conditions = ["Missing columns in REDCap files"]
    expected_output = "update_tracker raises a RuntimeError due to missing columns."

    removed_col = "abq_s1_r1_e1_complete"

    def modify(self, base_files):
        modified_files = base_files.copy()

        redcap_subpath = os.path.join(
            "sourcedata",
            "checked",
            "redcap",
            self.build_rc_name("bbschild", "s1", "r1"),
        )
        # pandas.read_csv() expects a file-like object, so we create a StringIO object
        #   because modify() is called before the test case's files are written to disk
        redcap_df = pd.read_csv(StringIO(modified_files[redcap_subpath]))
        redcap_df.drop(columns=[self.removed_col], inplace=True)
        modified_files[redcap_subpath] = redcap_df.to_csv(index=False)

        return modified_files

    def validate(self):
        from hallmonitor import app

        args = self.get_standard_args()
        args.raw_only = True
        args.no_qa = True

        with (
            mock.patch.object(logging.Logger, "error") as mock_error,
            pytest.raises(RuntimeError, match=r"Could not update tracker.*"),
        ):
            app.main(args)

        assert mock_error.call_count >= 1, mock_error._calls_repr()

        for call in mock_error.call_args_list:
            args = list(map(str, call.args))
            removed_matches = any(self.removed_col in arg for arg in args)
            col_matches = any("bbschild" in arg for arg in args)

            assert removed_matches and col_matches, f"Unexpected error: {call.args}"


def test_missing_redcap_column(request):
    MissingREDCapColumnTestCase.run_test_case(request)


class RelocatedREDCapColumnTestCase(TrackerTestCase):
    """
    Validates that relocated columns in REDCap files are detected.
    """

    case_name = "RelocatedREDCapColumnTestCase"
    description = (
        "Ensures that when a column is removed from one REDCap file "
        "and added to another, the error is detected and logged, "
        "preventing the tracker from being updated."
    )
    conditions = [
        "A column is removed from its original REDCap file.",
        "The same column is added to a different REDCap file.",
    ]
    expected_output = (
        "An error is logged indicating the relocation of the column, "
        "and the tracker update fails with a RuntimeError."
    )

    moved_col = "abq_s1_r1_e1_complete"

    def modify(self, base_files):
        modified_files = base_files.copy()

        rc_dir = os.path.join("sourcedata", "checked", "redcap")

        # delete the column from its original REDCap
        original_rc = os.path.join(rc_dir, self.build_rc_name("bbschild", "s1", "r1"))
        # need to read in data via file-like object
        og_df = pd.read_csv(StringIO(modified_files[original_rc]))
        og_df.drop(columns=[self.moved_col], inplace=True)
        modified_files[original_rc] = og_df.to_csv(index=False)

        # add the column back in a different REDCap
        new_rc = os.path.join(rc_dir, self.build_rc_name("iqschild", "s1", "r1"))
        new_df = pd.read_csv(StringIO(modified_files[new_rc]))
        new_df[self.moved_col] = 2
        modified_files[new_rc] = new_df.to_csv(index=False)

        return modified_files

    def validate(self):
        from hallmonitor import app

        args = self.get_standard_args()
        args.raw_only = True
        args.no_qa = True

        with (
            mock.patch.object(logging.Logger, "error") as mock_error,
            pytest.raises(RuntimeError, match=r"Could not update tracker.*"),
        ):
            app.main(args)

        assert mock_error.call_count >= 1, mock_error._calls_repr()

        keywords = [self.moved_col, "bbschild", "iqschild"]
        keyword_pats = [re.compile(re.escape(kw)) for kw in keywords]
        # We're only interested in the first call to Logger.error()
        args = list(map(str, mock_error.call_args_list[0].args))

        for pat in keyword_pats:
            assert any(pat.search(arg.lower()) for arg in args), (
                f"Did not find keyword: {pat.pattern}"
            )


def test_relocated_redcap_column(request):
    RelocatedREDCapColumnTestCase.run_test_case(request)


class RemoteAndInPersonREDCapTestCase(TrackerTestCase):
    """
    Validates that REDCap files with conflicting in-person and remote-only data
    are detected, ensuring errors are logged and the tracker cannot be updated.
    """

    case_name = "RemoteAndInPersonREDCapTestCase"
    description = (
        "Ensures that when duplicate REDCap data exists for the same subject, "
        "with one labeled as remote-only and the other as in-person, the error "
        "is detected and logged, preventing the tracker from being updated."
    )
    conditions = [
        "A duplicate REDCap file is created with remote-only data for the same subject.",
        "The original REDCap file contains in-person data for the same subject.",
    ]
    expected_output = (
        "An error is logged indicating the presence of conflicting remote-only and "
        "in-person data for the same subject, and the tracker update fails with a RuntimeError."
    )

    def modify(self, base_files):
        modified_files = base_files.copy()

        rc_dir = os.path.join("sourcedata", "checked", "redcap")
        rc_stem = "bbschild"
        original_rc = os.path.join(rc_dir, self.build_rc_name(rc_stem, "s1", "r1"))
        new_rc = os.path.join(rc_dir, self.build_rc_name(rc_stem, "s1", "r1", True))
        # copy original content to new remote-only REDCap
        modified_files[new_rc] = modified_files[original_rc]

        return modified_files

    def validate(self):
        from hallmonitor import app

        args = self.get_standard_args()
        args.raw_only = True
        args.no_qa = True

        with (
            mock.patch.object(logging.Logger, "error") as mock_error,
            pytest.raises(RuntimeError, match=r"Could not update tracker.*"),
        ):
            app.main(args)

        assert mock_error.call_count >= 1, mock_error._calls_repr()

        keywords = ["remote-only", "in-person", str(self.sub_id)]
        keyword_pats = [re.compile(re.escape(kw)) for kw in keywords]
        # We're only interested in the first call to Logger.error()
        args = list(map(str, mock_error.call_args_list[0].args))

        for pat in keyword_pats:
            assert any(pat.search(arg.lower()) for arg in args), (
                f"Did not find keyword: {pat.pattern}"
            )


def test_remote_and_in_person_redcap(request):
    RemoteAndInPersonREDCapTestCase.run_test_case(request)
