import os
import re

import pandas as pd

from hallmonitor.tests.integration.base_cases import QATestCase


class PendingQAFileTestCase(QATestCase):
    """
    Test case for verifying that valid raw identifier files are copied to the pending-qa directory,
    and that no other files are copied.
    """

    case_name = "PendingQAFileTestCase"
    description = "Moves files for valid raw identifiers to the pending-qa directory and verifies that only those files are moved."
    conditions = ["Files for valid raw identifiers are copied to pending-qa"]
    expected_output = (
        "Files are copied correctly, and no extraneous files are present in pending-qa."
    )

    original_paths = set()

    def modify(self, base_files):
        modified_files = base_files.copy()
        self.original_paths = set(modified_files.keys())

        pending_dir = os.path.join("data-monitoring", "pending")

        # remove old pending-files CSV, keep pending-errors
        modified_files = {
            path: contents
            for path, contents in modified_files.items()
            if "pending-errors" in path or not path.startswith(pending_dir)
        }

        # add in our own pending-files CSV
        identifier = f"sub-{self.sub_id}_all_eeg_s1_r1_e1"
        pending_files_path = os.path.join(
            pending_dir, "pending-files-2024-01-01_12-30.csv"
        )
        pending_df = pd.DataFrame(
            [
                {
                    "datetime": "2024-01-01_12-30",
                    "user": "dummy",
                    "passRaw": 1,
                    "identifier": identifier,
                    "subject": self.sub_id,
                    "dataType": "eeg",
                    "encrypted": False,
                    "suffix": "s1_r1_e1",
                    "errorType": "",
                    "errorDetails": "",
                }
            ]
        )

        pending_files_contents = pending_df.to_csv(index=False)
        modified_files[pending_files_path] = pending_files_contents

        return modified_files

    def validate(self):
        error = self.run_qa_validation()
        if error:
            raise AssertionError(f"Unexpected error occurred: {error}")

        # mock out copied files in sourcedata/pending-qa/
        data_folder = os.path.join(
            "sourcedata",
            "pending-qa",
            "s1_r1",
            "eeg",
            f"sub-{self.sub_id}",
        )
        identifier = f"sub-{self.sub_id}_all_eeg_s1_r1_e1"
        exts = {".eeg", ".vmrk", ".vhdr"}
        additional_files = {os.path.join(data_folder, identifier + ext) for ext in exts}

        expected_files = self.original_paths
        expected_files.update(additional_files)

        actual_files = set(self.get_paths(self.case_dir))

        missing_files = expected_files - actual_files
        extra_files = actual_files - expected_files

        # raise error on mismatch
        if missing_files or extra_files:
            fail_reason = ""
            if missing_files:
                fail_reason += "Missing files:\n" + "\n".join(missing_files) + "\n"
            if extra_files:
                fail_reason += "Extra files:\n" + "\n".join(extra_files) + "\n"
            raise AssertionError(f"File layout validation failed:\n{fail_reason}")


def test_pending_qa_file(request):
    PendingQAFileTestCase.run_test_case(request)


class QAChecklistEntryTestCase(PendingQAFileTestCase):
    """
    Test case for verifying that only valid raw identifiers are given an entry in the QA checklist.
    """

    case_name = "QAChecklistEntryTestCase"
    description = "Sets up a valid raw identifier in the pending-files CSV and checks that an entry is given in the QA checklist."
    conditions = ["Valid raw identifiers have an entry in the QA checklist."]
    expected_output = "QA checklist details are given correctly for the specified identifier, and no other identifiers are present."

    def validate(self):
        error = self.run_qa_validation()
        if error:
            raise AssertionError(f"Unexpected error occurred: {error}")

        identifier = f"sub-{self.sub_id}_all_eeg_s1_r1_e1"

        qa_df = pd.read_csv(
            os.path.join(self.case_dir, "sourcedata", "pending-qa", "qa-checklist.csv")
        )
        assert len(qa_df.index) == 1  # should be only one entry

        qa_rows = qa_df[qa_df["identifier"] == identifier]
        assert len(qa_rows.index) == 1  # the only entry should match our identifier

        info = qa_rows.iloc[0].to_dict()

        assert info["subject"] == self.sub_id
        assert info["dataType"] == "eeg"
        assert info["suffix"] == "s1_r1"
        assert not info["qa"]
        assert not info["localMove"]

        assert info["user"]
        assert re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}", info["datetime"]) is not None


def test_qa_checklist_entry(request):
    QAChecklistEntryTestCase.run_test_case(request)


class QAPassMovedToCheckedTestCase(QATestCase):
    """
    Test case for verifying that only identifiers marked as both passing QA checks and
    being moved locally are sent to the checked directory.
    """

    case_name = "QAPassMovedToCheckedTestCase"
    description = (
        "Sets up three identifiers in pending-qa: one that passes QA and is moved locally, "
        "one that fails QA, and one that is not moved. Verifies proper directory placement."
    )
    conditions = [
        "Identifier 'A' is in sourcedata/pending-qa/ and passes QA checks and is moved locally.",
        "Identifier 'B' is in sourcedata/pending-qa/ and fails QA checks.",
        "Identifier 'C' is in sourcedata/pending-qa/ and is not moved locally.",
    ]
    expected_output = "sourcedata/checked/ contains 'A', while the 'pending-qa' directory retains 'B' and 'C'."

    def modify(self, base_files):
        modified_files = base_files.copy()

        pending_qa_dir = os.path.join("sourcedata", "pending-qa")

        # mock out presence of data for three identifiers in source/pending-qa
        data_dir = os.path.join(pending_qa_dir, "s1_r1", "eeg")
        ids = {1, 2, 3}
        for sub_id in ids:
            data_path = os.path.join(data_dir, f"sub-{sub_id}", "dummy.txt")
            modified_files[data_path] = f"Dummy data for mock subject {sub_id}"

        # mock out qa-checklist.csv
        qa_checklist_path = os.path.join(pending_qa_dir, "qa-checklist.csv")
        new_qa_checklist = {
            "identifier": [
                "sub-1_all_eeg_s1_r1_e1",
                "sub-2_all_eeg_s1_r1_e1",
                "sub-3_all_eeg_s1_r1_e1",
            ],
            "qa": [1, 0, 1],  # pass, fail, pass
            "localMove": [1, 1, 0],  # pass, pass, fail
            "deviationString": [""] * 3,
            "datetime": ["2024-01-01_12-30"] * 3,
            "user": ["dummyuser"] * 3,
            "subject": [1, 2, 3],
            "dataType": ["eeg"] * 3,
            "encrypted": [False] * 3,
            "suffix": ["s1_r1_e1"] * 3,
        }
        new_qa_df = pd.DataFrame(new_qa_checklist)
        modified_files[qa_checklist_path] = new_qa_df.to_csv(index=False)

        return modified_files

    def validate(self):
        error = self.run_qa_validation()
        if error:
            raise AssertionError(f"Unexpected error occurred: {error}")

        actual_files = self.read_files(self.case_dir)

        checked_dir = os.path.join("sourcedata", "checked")

        sub1_checked_path = os.path.join(
            checked_dir, "sub-1", "s1_r1", "eeg", "dummy.txt"
        )
        assert sub1_checked_path in actual_files
        assert "subject 1" in str(actual_files[sub1_checked_path]).lower()

        checked_subs = {
            os.path.relpath(path, checked_dir).split("/")[0]
            for path in actual_files
            if str(path).startswith(checked_dir) and "redcap" not in path
        }
        assert checked_subs == {"sub-1", f"sub-{self.sub_id}"}

        data_dir = os.path.join("sourcedata", "pending-qa", "s1_r1", "eeg")

        sub1_pending_path = os.path.join(data_dir, "sub-1", "dummy.txt")
        assert sub1_pending_path not in actual_files

        sub2_pending_path = os.path.join(data_dir, "sub-2", "dummy.txt")
        assert sub2_pending_path in actual_files
        assert "subject 2" in str(actual_files[sub2_pending_path]).lower()

        sub3_pending_path = os.path.join(data_dir, "sub-3", "dummy.txt")
        assert sub3_pending_path in actual_files
        assert "subject 3" in str(actual_files[sub3_pending_path]).lower()


def test_qa_pass_moved_to_checked(request):
    QAPassMovedToCheckedTestCase.run_test_case(request)


class QAPassRemovedFromChecklistTestCase(QAPassMovedToCheckedTestCase):
    """
    Test case for verifying that only identifiers marked as both passing QA checks and
    being moved locally are removed from the QA checklist.
    """

    case_name = "QAPassRemovedFromChecklistTestCase"
    description = (
        "Sets up three identifiers in pending-qa: one that passes QA and is moved locally, "
        "one that fails QA, and one that is not moved. Verifies proper QA checklist state."
    )
    conditions = [
        "Identifier 'A' is in sourcedata/pending-qa/ and passes QA checks and is moved locally.",
        "Identifier 'B' is in sourcedata/pending-qa/ and fails QA checks.",
        "Identifier 'C' is in sourcedata/pending-qa/ and is not moved locally.",
    ]
    expected_output = "qa-checklist.csv is missing 'A' and contains entries for identifiers 'B' and 'C'."

    def validate(self):
        error = self.run_qa_validation()
        if error:
            raise AssertionError(f"Unexpected error occurred: {error}")

        qa_df = pd.read_csv(
            os.path.join(self.case_dir, "sourcedata", "pending-qa", "qa-checklist.csv")
        )

        assert len(qa_df.index) == 2

        sub1_qa_entries = qa_df[qa_df["identifier"] == "sub-1_all_eeg_s1_r1_e1"]
        assert len(sub1_qa_entries.index) == 0

        sub2_qa_entries = qa_df[qa_df["identifier"] == "sub-2_all_eeg_s1_r1_e1"]
        assert len(sub2_qa_entries.index) == 1

        sub3_qa_entries = qa_df[qa_df["identifier"] == "sub-3_all_eeg_s1_r1_e1"]
        assert len(sub3_qa_entries.index) == 1


def test_qa_pass_removed_from_checklist(request):
    QAPassRemovedFromChecklistTestCase.run_test_case(request)


class QAPassAddedToValidatedFileRecordTestCase(QAPassMovedToCheckedTestCase):
    """
    Test case for verifying that only identifiers marked as both passing QA checks and
    being moved locally are added to the validated file record.
    """

    case_name = "QAPassAddedToValidatedFileRecordTestCase"
    description = (
        "Sets up three identifiers in pending-qa: one that passes QA and is moved locally, "
        "one that fails QA, and one that is not moved. Verifies proper validated file record state."
    )
    conditions = [
        "Identifier 'A' is in sourcedata/pending-qa/ and passes QA checks and is moved locally.",
        "Identifier 'B' is in sourcedata/pending-qa/ and fails QA checks.",
        "Identifier 'C' is in sourcedata/pending-qa/ and is not moved locally.",
    ]
    expected_output = "validated-file-record.csv contains an entry for 'A' and does not have 'B' or 'C'."

    def validate(self):
        error = self.run_qa_validation()
        if error:
            raise AssertionError(f"Unexpected error occurred: {error}")

        record_df = pd.read_csv(
            os.path.join(self.case_dir, "data-monitoring", "validated-file-record.csv")
        )

        assert len(record_df.index) == 1

        sub1_qa_entries = record_df[record_df["identifier"] == "sub-1_all_eeg_s1_r1_e1"]
        assert len(sub1_qa_entries.index) == 1

        datetime = sub1_qa_entries["datetime"].iloc[0]
        assert re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}", str(datetime)) is not None

        sub2_qa_entries = record_df[record_df["identifier"] == "sub-2_all_eeg_s1_r1_e1"]
        assert len(sub2_qa_entries.index) == 0

        sub3_qa_entries = record_df[record_df["identifier"] == "sub-3_all_eeg_s1_r1_e1"]
        assert len(sub3_qa_entries.index) == 0


def test_qa_pass_added_to_validated_file_record(request):
    QAPassAddedToValidatedFileRecordTestCase.run_test_case(request)


class QAEmptyDirectoriesAreDeletedTestCase(QATestCase):
    """
    Test case for verifying that empty directories in the `pending-qa` folder are deleted
    as part of the QA cleanup process.
    """

    case_name = "QAEmptyDirectoriesAreDeletedTestCase"
    description = (
        "Sets up multiple empty directories in sourcedata/pending-qa/ to verify that all "
        "empty directories are removed during QA cleanup."
    )
    conditions = [
        "Directory 'empty1/' is in sourcedata/pending-qa/ and contains no files or subdirectories.",
        "Directory 'empty2/' is in sourcedata/pending-qa/ and contains no files or subdirectories.",
        "Directory 'not_empty/' is in sourcedata/pending-qa/ and contains one or more files.",
    ]
    expected_output = "The directories 'empty1/' and 'empty2/' are deleted, while 'not_empty/' remains intact."

    def modify(self, base_files):
        modified_files = base_files.copy()

        pending_qa_dir = os.path.join("sourcedata", "pending-qa")

        empty_dir_1 = os.path.join(pending_qa_dir, "empty1", "")
        modified_files[empty_dir_1] = ""

        empty_dir_2 = os.path.join(pending_qa_dir, "empty2", "")
        modified_files[empty_dir_2] = ""

        sub_empty_dir = os.path.join(empty_dir_2, "sub_empty", "")
        modified_files[sub_empty_dir] = ""

        non_empty_dir = os.path.join(pending_qa_dir, "not_empty", "")
        dummy_filepath = os.path.join(non_empty_dir, "dummy.txt")
        modified_files[dummy_filepath] = "Dummy content that should not be deleted"

        return modified_files

    def validate(self):
        error = self.run_qa_validation()
        if error:
            raise AssertionError(f"Unexpected error occurred: {error}")

        pending_qa_files = self.read_files(
            os.path.join(self.case_dir, "sourcedata", "pending-qa")
        )

        assert len(pending_qa_files.keys()) == 2
        assert pending_qa_files.keys() == {"not_empty/dummy.txt", "qa-checklist.csv"}


def test_qa_empty_directories_are_deleted(request):
    QAEmptyDirectoriesAreDeletedTestCase.run_test_case(request)


class QAChecklistCreatedTestCase(QATestCase):
    """
    Test case for verifying that a QA checklist is automatically created if one does not
    already exist in the `pending-qa` folder.
    """

    case_name = "QAChecklistCreatedTestCase"
    description = (
        "Simulates a scenario where no QA checklist is present in sourcedata/pending-qa/. "
        "Verifies that hallMonitor creates a new QA checklist during the QA process."
    )
    conditions = [
        "The sourcedata/pending-qa/ directory does not contain a file named 'qa-checklist.csv'.",
        "Identifiers and their data are present in sourcedata/pending-qa/, but no checklist exists.",
    ]
    expected_output = "A new 'qa-checklist.csv' file is created in sourcedata/pending-qa/ with entries for all identifiers."

    def modify(self, base_files):
        modified_files = base_files.copy()

        pending_qa_subdir = os.path.join("sourcedata", "pending-qa", "")
        qa_checklist_path = os.path.join(pending_qa_subdir, "qa-checklist.csv")

        if qa_checklist_path not in modified_files:
            raise FileNotFoundError("Could not find QA checklist at expected location")

        # get rid of qa-checklist.csv
        del modified_files[qa_checklist_path]
        # ensure we still have an empty dir at sourcedata/pending-qa/
        modified_files[pending_qa_subdir] = ""

        return modified_files

    def validate(self):
        error = self.run_qa_validation()
        if error:
            raise AssertionError(f"Unexpected error occurred: {error}")

        pending_qa_dir = os.path.join(self.case_dir, "sourcedata", "pending-qa")
        pending_qa_files = self.read_files(pending_qa_dir)

        assert "qa-checklist.csv" in pending_qa_files

        qa_df = pd.read_csv(os.path.join(pending_qa_dir, "qa-checklist.csv"))

        assert len(qa_df.index) == 0  # no entries by default

        assert set(qa_df.columns) == {
            "datetime",
            "user",
            "identifier",
            "deviationString",
            "subject",
            "dataType",
            "encrypted",
            "suffix",
            "qa",
            "localMove",
        }


def test_qa_checklist_created(request):
    QAChecklistCreatedTestCase.run_test_case(request)


class QAChecklistOneRowPerDeviationStringTestCase(QATestCase):
    case_name = "QAChecklistOneRowPerDeviationStringTestCase"
    description = (
        "Sets up multiple deviation strings for a single identifier in the raw data "
        "and verifies that each deviation string gets a separate entry in the QA checklist."
    )
    conditions = [
        "Identifier 'A' is in sourcedata/raw/ and has multiple deviation strings.",
        "The QA checklist should have one row per deviation string for identifier 'A'.",
    ]
    expected_output = (
        "The QA checklist contains one row per deviation string for identifier 'A'."
    )

    deviation_strings = ["test1", "test2", "test3"]

    def modify(self, base_files):
        modified_files = base_files.copy()

        raw_dir = os.path.join(
            "sourcedata", "raw", "s1_r1", "eeg", f"sub-{self.sub_id}"
        )
        identifier = f"sub-{self.sub_id}_all_eeg_s1_r1_e1"
        eeg_exts = [".vmrk", ".vhdr", ".eeg"]

        # add file copies with additional deviation strings
        for ext in eeg_exts:
            old_filename = os.path.join(raw_dir, identifier + ext)
            for dev_str in self.deviation_strings:
                new_filename = old_filename.replace(ext, f"_{dev_str}{ext}")
                modified_files[new_filename] = modified_files[old_filename]

            # we want to remove the original files, leaving just deviation variants
            self.remove_file(modified_files, os.path.basename(old_filename))

        # add deviation.txt file
        deviation_file = os.path.join(raw_dir, identifier + "_deviation.txt")
        modified_files[deviation_file] = "Files to process: NA"

        # indicate that our identifier has passed in pending-files CSV

        pending_dir = os.path.join("data-monitoring", "pending")

        # remove old pending-files CSV, keep pending-errors
        modified_files = {
            path: contents
            for path, contents in modified_files.items()
            if "pending-errors" in path or not path.startswith(pending_dir)
        }

        # add in our own pending-files CSV
        identifier = f"sub-{self.sub_id}_all_eeg_s1_r1_e1"
        pending_files_path = os.path.join(
            pending_dir, "pending-files-2024-01-01_12-30.csv"
        )
        pending_df = pd.DataFrame(
            [
                {
                    "datetime": "2024-01-01_12-30",
                    "user": "dummy",
                    "passRaw": 1,
                    "identifier": identifier,
                    "subject": self.sub_id,
                    "dataType": "eeg",
                    "encrypted": False,
                    "suffix": "s1_r1_e1",
                    "errorType": "",
                    "errorDetails": "",
                }
            ]
        )

        modified_files[pending_files_path] = pending_df.to_csv(index=False)

        return modified_files

    def validate(self):
        error = self.run_qa_validation()
        if error:
            raise AssertionError(f"Unexpected error occurred: {error}")

        qa_df = pd.read_csv(
            os.path.join(
                self.case_dir,
                "sourcedata",
                "pending-qa",
                "qa-checklist.csv",
            )
        )

        assert len(qa_df.index) == len(self.deviation_strings)
        assert (qa_df["identifier"] == f"sub-{self.sub_id}_all_eeg_s1_r1_e1").all()

        for dev_str in self.deviation_strings:
            assert len(qa_df[qa_df["deviationString"] == dev_str].index) == 1


def test_qa_checklist_one_row_per_deviation_string(request):
    QAChecklistOneRowPerDeviationStringTestCase.run_test_case(request)


class QAChecklistUniqueIdentifierDeviationStringTestCase(
    QAChecklistOneRowPerDeviationStringTestCase
):
    case_name = "QAChecklistUniqueIdentifierDeviationStringTestCase"

    def validate(self):
        qa_df_path = os.path.join(
            self.case_dir,
            "sourcedata",
            "pending-qa",
            "qa-checklist.csv",
        )

        # we run QA validation twice to test behavior on persisted identifiers

        error_1 = self.run_qa_validation()
        if error_1:
            raise AssertionError(f"Unexpected error occurred: {error_1}")

        qa_df = pd.read_csv(qa_df_path)

        devstr_iter = iter(self.deviation_strings)

        # modify one of the rows to have qa = 1
        passed_qa_devstr = next(devstr_iter)
        qa_df.loc[qa_df["deviationString"] == passed_qa_devstr, "qa"] = 1

        # modify one of the rows to have localMove = 1
        local_move_devstr = next(devstr_iter)
        qa_df.loc[qa_df["deviationString"] == local_move_devstr, "localMove"] = 1

        # delete the remaining row
        deleted_devstr = next(devstr_iter)
        qa_df = qa_df[qa_df["deviationString"] != deleted_devstr]

        qa_df.to_csv(qa_df_path)

        error_2 = self.run_qa_validation()
        if error_2:
            raise AssertionError(f"Unexpected error occurred: {error_2}")

        qa_df = pd.read_csv(qa_df_path)

        # check that there are the correct number of rows
        assert len(qa_df.index) == len(self.deviation_strings)

        # check that the same row has qa = 1
        assert qa_df[qa_df["deviationString"] == passed_qa_devstr]["qa"].iloc[0] == 1

        # check that the same row has localMove = 1
        assert (
            qa_df[qa_df["deviationString"] == local_move_devstr]["localMove"].iloc[0]
            == 1
        )

        # check that the deleted row was recovered
        assert qa_df["deviationString"].str.contains(deleted_devstr).sum() == 1


def test_qa_checklist_unique_identifier_deviation_string(request):
    QAChecklistUniqueIdentifierDeviationStringTestCase.run_test_case(request)


class QAChecklistRemovesDeletedFilesTestCase(QATestCase):
    case_name = "QAChecklistRemovesDeletedFilesTestCase"
    description = (
        "If all files for an identifier are removed from `pending-qa/`, the QA "
        "checklist must drop the corresponding rows on the next run."
    )
    conditions = [
        "Subject 3000215 session 1 has two EEG triplets with deviation.txt in "
        "`pending-qa/` and fails raw checks.",
        "Data monitor deletes those triplets from `pending-qa/` after marking them "
        "as needing reupload.",
    ]
    expected_output = (
        "No rows for 3000215 session 1 remain in the refreshed QA checklist; "
        "`pending-qa/` is empty for that identifier."
    )

    def modify(self, base_files):
        modified_files = base_files.copy()
        return modified_files

    def validate(self):
        # Import pipeline
        from hallmonitor.app import main as hm_main

        hm_args = self.get_standard_args()
        hm_args.raw_only = True

        # Save some useful variables
        qa_path = self.build_path("s1_r1", "eeg", "", True).replace("raw", "pending-qa")
        identifier = f"sub-{self.sub_id}_all_eeg_s1_r1_e1"

        # Run pipeline for the first time
        hm_main(hm_args)

        # Check that the identifier is in pending-qa/ and the QA checklist to begin with
        assert any(
            str(path).startswith(qa_path) for path in self.get_paths(self.case_dir)
        )
        qa_df_before = self.get_qa_checklist()
        assert qa_df_before is not None
        assert (qa_df_before["identifier"] == identifier).any()

        # Introduce error in sourcedata/raw/ after first run (remove .eeg file)
        target_file = self.build_path("s1_r1", "eeg", identifier + ".eeg", True)
        os.remove(os.path.join(self.case_dir, target_file))

        # Run pipeline for the second time
        hm_main(hm_args)

        qa_df = self.get_qa_checklist()
        assert qa_df is not None
        # Make sure we have removed the identifier from the QA checklist
        assert not (qa_df["identifier"] == identifier).any()

        # Check that we have removed all of the identifier's files from pending-qa
        assert not any(
            str(path).startswith(qa_path) for path in self.get_paths(self.case_dir)
        )


def test_qa_checklist_removes_deleted_files(request):
    QAChecklistRemovesDeletedFilesTestCase.run_test_case(request)
