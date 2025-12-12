import re

from hallmonitor.tests.integration.base_cases import ExpectedError, ValidationTestCase


class MisplacedFileTestCase(ValidationTestCase):
    pass


class FolderSessionSuffixMismatchTestCase(MisplacedFileTestCase):
    """
    Test case for mismatched session suffix in file name and folder.
    """

    case_name = "FolderSessionSuffixMismatchTestCase"
    description = "Renames a file so its session suffix doesn't match the session folder it's located in."
    conditions = ["File's session suffix does not match session folder"]
    expected_output = "Error is raised for file whose session suffix does not match its session folder."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()

        old_suffix = "s1_r1_e1"
        new_suffix = "s3_r1_e1"
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_{old_suffix}.csv"
        new_name = old_name.replace(old_suffix, new_suffix)

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        old_basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1.csv"
        new_basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s3_r1_e1.csv"
        misplaced_info = re.escape(
            f"Found file in wrong directory: {new_basename} found in "
        )
        misplaced_info += r"(?:.*/)+"

        errors = [
            ExpectedError("Misplaced file", misplaced_info),
            ExpectedError(
                "Missing file", re.escape(f"Expected file {old_basename} not found")
            ),
            ExpectedError(
                "Unexpected file", re.escape(f"Unexpected file {new_basename} found")
            ),
        ]

        return errors


def test_folder_session_suffix_mismatch(request):
    FolderSessionSuffixMismatchTestCase.run_test_case(request)


class FolderRunSuffixMismatchTestCase(MisplacedFileTestCase):
    """
    Test case for mismatched run suffix in file name and session folder.
    """

    case_name = "FolderRunSuffixMismatchTestCase"
    description = "Renames a file so its run suffix doesn't match the session folder it's located in."
    conditions = ["File's run suffix does not match session folder"]
    expected_output = (
        "Error is raised for file whose run suffix does not match its session folder."
    )

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()

        old_suffix = "s1_r1_e1"
        new_suffix = "s3_r1_e1"
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_{old_suffix}.csv"
        new_name = old_name.replace(old_suffix, new_suffix)

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self) -> list[ExpectedError]:
        old_basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1.csv"
        new_basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s3_r1_e1.csv"

        misplaced_info = re.escape(
            f"Found file in wrong directory: {new_basename} found in "
        )
        misplaced_info += r"(?:.*/)+"
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Misplaced file", misplaced_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_folder_run_suffix_mismatch(request):
    FolderRunSuffixMismatchTestCase.run_test_case(request)


class FolderSubjectMismatchTestCase(MisplacedFileTestCase):
    """
    Test case for mismatched subject in file name and subject folder.
    """

    case_name = "FolderSubjectMismatchTestCase"
    description = "Renames a file so its specified subject does not match the subject folder it's located in."
    conditions = ["File's subject does not match subject folder"]
    expected_output = (
        "Error is raised for file whose subject does not match its subject folder."
    )

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()

        old_name = f"sub-{self.sub_id}_all_eeg_s1_r1_e1.eeg"
        new_name = old_name.replace(str(self.sub_id), str(self.sub_id + 1))

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        old_basename = f"sub-{self.sub_id}_all_eeg_s1_r1_e1.eeg"
        new_basename = f"sub-{self.sub_id + 1}_all_eeg_s1_r1_e1.eeg"

        misplaced_info = re.escape(
            f"Found file in wrong directory: {new_basename} found in "
        )
        misplaced_info += r"(?:.*/)+"
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Misplaced file", misplaced_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_folder_subject_mismatch(request):
    FolderSubjectMismatchTestCase.run_test_case(request)


class FolderVariableMismatchTestCase(MisplacedFileTestCase):
    """
    Test case for variable name not matching the enclosing data type folder.
    """

    case_name = "FolderVariableMismatchTestCase"
    description = "Copies a file to a folder with an incorrect data type, causing a mismatch between the variable name and the folder."
    conditions = ["File's variable name does not match enclosing data type folder"]
    expected_output = "Error is raised for file whose variable name does not match the enclosing data type folder."

    is_raw = False

    def modify(self, base_files):
        modified_files = base_files.copy()

        old_folder = "psychopy"
        new_folder = "digi"
        old_path = self.build_path(
            "s1_r1",
            old_folder,
            f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1.csv",
            self.is_raw,
        )
        new_path = old_path.replace(old_folder, new_folder, count=1)

        if old_path not in modified_files:
            raise FileNotFoundError(f"File matching relative path {old_path} not found")

        modified_files[new_path] = modified_files[old_path]  # make copy of file

        return modified_files

    def get_expected_errors(self):
        file_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1.csv"
        misplaced_info = re.escape(
            f"Found file in wrong directory: {file_name} found in "
        )
        misplaced_info += r"(?:.*/)+digi/"
        errors = [
            ExpectedError("Misplaced file", misplaced_info),
            ExpectedError(
                "Unexpected file", re.escape(f"Unexpected file {file_name} found")
            ),
        ]

        return errors


def test_folder_variable_mismatch(request):
    FolderVariableMismatchTestCase.run_test_case(request)
