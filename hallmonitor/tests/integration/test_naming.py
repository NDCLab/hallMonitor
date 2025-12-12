import os
import re

from hallmonitor.tests.integration.base_cases import ExpectedError, ValidationTestCase


class NamingTestCase(ValidationTestCase):
    pass


class InvalidVariableNameTestCase(NamingTestCase):
    """
    Test case for incorrect variable names in file names.
    """

    case_name = "InvalidVariableNameTestCase"
    description = "Introduces an incorrect variable name in the file name."
    conditions = ["Variable name is invalid"]
    expected_output = "Error is raised for incorrect variable name in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1.csv"
        new_name = f"sub-{self.sub_id}_bad-taskname_s1_r1_e1.csv"

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_PATTERN_s1_r1_e1.csv"
        old_var = "arrow-alert-v1-1_psychopy"
        new_var = "bad-taskname"
        old_basename = basename.replace("PATTERN", old_var)
        new_basename = basename.replace("PATTERN", new_var)

        naming_info = re.escape(f"Invalid variable name {new_var}")
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_invalid_variable_name(request):
    InvalidVariableNameTestCase.run_test_case(request)


class MissingVariableNameTestCase(NamingTestCase):
    """
    Test case for missing variable names in file names.
    """

    case_name = "MissingVariableNameTestCase"
    description = "Removes the variable name from the file name, making it missing."
    conditions = ["Variable name is missing"]
    expected_output = "Error is raised for missing variable name in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        variable = "arrow-alert-v1-1_psychopy"
        old_name = f"sub-{self.sub_id}_{variable}_s1_r1_e1.csv"
        new_name = old_name.replace(variable, "")

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_PATTERN_s1_r1_e1.csv"
        old_var = "arrow-alert-v1-1_psychopy"
        new_var = ""
        old_basename = basename.replace("PATTERN", old_var)
        new_basename = basename.replace("PATTERN", new_var)

        new_filepath = os.path.join(
            self.case_dir,
            self.build_path("s1_r1", "psychopy", new_basename, self.is_raw),
        )

        naming_info = re.escape(
            f"File {new_filepath} does not match expected identifier format"
        )
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_missing_variable_name(request):
    MissingVariableNameTestCase.run_test_case(request)


class MissingSubjectNumberTestCase(NamingTestCase):
    """
    Test case for missing subject number in file names.
    """

    case_name = "MissingSubjectNumberTestCase"
    description = "Removes the subject number from the file name, leaving an incomplete subject identifier."
    conditions = ["Subject number is missing"]
    expected_output = "Error is raised for missing subject number in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        sub = f"sub-{self.sub_id}"
        old_name = f"{sub}_all_eeg_s1_r1_e1.eeg"
        new_name = old_name.replace(sub, "sub-")

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = "sub-PATTERN_all_eeg_s1_r1_e1.eeg"
        old_sub = str(self.sub_id)
        new_sub = ""
        old_basename = basename.replace("PATTERN", old_sub)
        new_basename = basename.replace("PATTERN", new_sub)

        new_path = os.path.join(
            self.case_dir, self.build_path("s1_r1", "eeg", new_basename, self.is_raw)
        )

        naming_info = re.escape(
            f"File {new_path} does not match expected identifier format"
        )
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_missing_subject_number(request):
    MissingSubjectNumberTestCase.run_test_case(request)


class InvalidSubjectNumberTestCase(NamingTestCase):
    """
    Test case for invalid subject numbers in file names.
    """

    case_name = "InvalidSubjectNumberTestCase"
    description = "Replaces the valid subject number in the file name with an invalid subject number."
    conditions = ["Subject number is invalid"]
    expected_output = "Error is raised for invalid subject number in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        sub = f"sub-{self.sub_id}"
        old_name = f"{sub}_all_eeg_s1_r1_e1.eeg"
        new_name = old_name.replace(sub, "sub-303")

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = "sub-PATTERN_all_eeg_s1_r1_e1.eeg"
        old_sub = str(self.sub_id)
        new_sub = "303"
        old_basename = basename.replace("PATTERN", old_sub)
        new_basename = basename.replace("PATTERN", new_sub)

        new_path = os.path.join(
            self.case_dir, self.build_path("s1_r1", "eeg", new_basename, self.is_raw)
        )

        naming_info = f"Subject number {new_sub} not an allowed subject value" + r".*"
        misplaced_info = (
            re.escape(f"Found file in wrong directory: {new_basename} found in ")
            + r"(?:.*/)+"
        )
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Misplaced file", misplaced_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_invalid_subject_number(request):
    InvalidSubjectNumberTestCase.run_test_case(request)


class InvalidSessionSuffixTestCase(NamingTestCase):
    """
    Test case for invalid session numbers in file names.
    """

    case_name = "InvalidSessionSuffixTestCase"
    description = "Replaces the valid session number in the file name with an invalid session suffix."
    conditions = ["Session number in suffix is invalid"]
    expected_output = "Error is raised for invalid session suffix in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        old_suffix = "s1_r1_e1"
        new_suffix = "s11_r1_e1"
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_{old_suffix}.csv"
        new_name = old_name.replace(old_suffix, new_suffix)

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_PATTERN.csv"
        old_suffix = "s1_r1_e1"
        new_suffix = "s11_r1_e1"
        old_basename = basename.replace("PATTERN", old_suffix)
        new_basename = basename.replace("PATTERN", new_suffix)

        naming_info = f"Suffix {new_suffix} not in allowed suffixes" + r".*"
        misplaced_info = re.escape(
            f"Found file in wrong directory: {new_basename} found in "
        )
        misplaced_info += r"(?:.*/)+"
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Misplaced file", misplaced_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_invalid_session_suffix(request):
    InvalidSessionSuffixTestCase.run_test_case(request)


class InvalidRunSuffixTestCase(NamingTestCase):
    """
    Test case for invalid run numbers in file names.
    """

    case_name = "InvalidRunSuffixTestCase"
    description = (
        "Replaces the valid run number in the file name with an invalid run suffix."
    )
    conditions = ["Run number in suffix is invalid"]
    expected_output = "Error is raised for invalid run suffix in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        old_suffix = "s1_r1_e1"
        new_suffix = "s1_r3_e1"
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_{old_suffix}.csv"
        new_name = old_name.replace(old_suffix, new_suffix)

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_PATTERN.csv"
        old_suffix = "s1_r1_e1"
        new_suffix = "s1_r3_e1"
        old_basename = basename.replace("PATTERN", old_suffix)
        new_basename = basename.replace("PATTERN", new_suffix)

        naming_info = f"Suffix {new_suffix} not in allowed suffixes" + r".*"
        misplaced_info = re.escape(
            f"Found file in wrong directory: {new_basename} found in "
        )
        misplaced_info += r"(?:.*/)+"
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Misplaced file", misplaced_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_invalid_run_suffix(request):
    InvalidRunSuffixTestCase.run_test_case(request)


class InvalidEventSuffixTestCase(NamingTestCase):
    """
    Test case for invalid event numbers in file names.
    """

    case_name = "InvalidEventSuffixTestCase"
    description = (
        "Replaces the valid event number in the file name with an invalid event suffix."
    )
    conditions = ["Event number in suffix is invalid"]
    expected_output = "Error is raised for invalid event suffix in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        old_suffix = "s1_r1_e1"
        new_suffix = "s1_r1_e3"
        old_name = f"sub-{self.sub_id}_all_eeg_{old_suffix}.eeg"
        new_name = old_name.replace(old_suffix, new_suffix)

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        identifier = f"sub-{self.sub_id}_all_eeg_PATTERN"
        old_suffix = "s1_r1_e1"
        new_suffix = "s1_r1_e3"

        naming_info = f"Suffix {new_suffix} not in allowed suffixes" + r".*"
        missing_info = re.escape(
            f"Expected file {identifier.replace('PATTERN', old_suffix)}.eeg not found"
        )
        extra_info = re.escape(
            f"Unexpected file {identifier.replace('PATTERN', new_suffix)}.eeg found"
        )

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_invalid_event_suffix(request):
    InvalidEventSuffixTestCase.run_test_case(request)


class MissingSessionSuffixTestCase(NamingTestCase):
    """
    Test case for missing session numbers in file names.
    """

    case_name = "MissingSessionSuffixTestCase"
    description = "Removes the session number from the file name, making it incomplete."
    conditions = ["Session number in suffix is missing"]
    expected_output = "Error is raised for missing session number in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        old_suffix = "s1_r1_e1"
        new_suffix = "s_r1_e1"
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_{old_suffix}.csv"
        new_name = old_name.replace(old_suffix, new_suffix)

        if not self.replace_file_name(modified_files, old_name, new_name):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_PATTERN.csv"
        old_suffix = "s1_r1_e1"
        new_suffix = "s_r1_e1"
        old_basename = basename.replace("PATTERN", old_suffix)
        new_basename = basename.replace("PATTERN", new_suffix)

        new_path = os.path.join(
            self.case_dir,
            self.build_path("s1_r1", "psychopy", new_basename, self.is_raw),
        )

        naming_info = re.escape(
            f"File {new_path} does not match expected identifier format"
        )
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_missing_session_suffix(request):
    MissingSessionSuffixTestCase.run_test_case(request)


class MissingRunSuffixTestCase(NamingTestCase):
    """
    Test case for missing run numbers in file names.
    """

    case_name = "MissingRunSuffixTestCase"
    description = "Removes the run number from the file name, making it incomplete."
    conditions = ["Run number in suffix is missing"]
    expected_output = "Error is raised for missing run number in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        old_suffix = "s1_r1_e1"
        new_suffix = "s1_r_e1"
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_{old_suffix}.csv"
        new_name = old_name.replace(old_suffix, new_suffix)

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_PATTERN.csv"
        old_suffix = "s1_r1_e1"
        new_suffix = "s1_r_e1"
        old_basename = basename.replace("PATTERN", old_suffix)
        new_basename = basename.replace("PATTERN", new_suffix)

        new_path = os.path.join(
            self.case_dir,
            self.build_path("s1_r1", "psychopy", new_basename, self.is_raw),
        )

        naming_info = re.escape(
            f"File {new_path} does not match expected identifier format"
        )
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_missing_run_suffix(request):
    MissingRunSuffixTestCase.run_test_case(request)


class MissingEventSuffixTestCase(NamingTestCase):
    """
    Test case for missing event numbers in file names.
    """

    case_name = "MissingEventSuffixTestCase"
    description = "Removes the event number from the file name, making it incomplete."
    conditions = ["Event number in suffix is missing"]
    expected_output = "Error is raised for missing event number in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        old_suffix = "s1_r1_e1"
        new_suffix = "s1_r1_e"
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_{old_suffix}.csv"
        new_name = old_name.replace(old_suffix, new_suffix)

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_PATTERN.csv"
        old_suffix = "s1_r1_e1"
        new_suffix = "s1_r1_e"
        old_basename = basename.replace("PATTERN", old_suffix)
        new_basename = basename.replace("PATTERN", new_suffix)

        new_path = os.path.join(
            self.case_dir,
            self.build_path("s1_r1", "psychopy", new_basename, self.is_raw),
        )

        naming_info = re.escape(
            f"File {new_path} does not match expected identifier format"
        )
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_missing_event_suffix(request):
    MissingEventSuffixTestCase.run_test_case(request)


class InvalidExtensionTestCase(NamingTestCase):
    """
    Test case for invalid file extensions in file names.
    """

    case_name = "InvalidExtensionTestCase"
    description = "Replaces the valid file extension with an invalid extension."
    conditions = ["File extension is invalid"]
    expected_output = "Error is raised for invalid file extension in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        old_ext = ".csv"
        new_ext = ".badext"
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1{old_ext}"
        new_name = old_name.replace(old_ext, new_ext)

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1.PATTERN"
        old_ext = "csv"
        new_ext = "badext"

        naming_info = (
            re.escape(f"File extension .{new_ext} doesn't match expected extensions")
            + r".*"
        )
        missing_info = re.escape(
            f"Expected file {basename.replace('PATTERN', old_ext)} not found"
        )
        extra_info = re.escape(
            f"Unexpected file {basename.replace('PATTERN', new_ext)} found"
        )

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_invalid_extension(request):
    InvalidExtensionTestCase.run_test_case(request)


class MissingExtensionTestCase(NamingTestCase):
    """
    Test case for missing file extensions in file names.
    """

    case_name = "MissingExtensionTestCase"
    description = "Removes the file extension from the file name, leaving it missing."
    conditions = ["File extension is missing"]
    expected_output = "Error is raised for missing file extension in file name."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()
        old_ext = ".csv"
        old_name = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1{old_ext}"
        new_name = old_name.replace(old_ext, "")

        if not self.replace_file_name(modified_files, old_name, new_name, self.is_raw):
            raise FileNotFoundError(f"File matching basename {old_name} not found")

        return modified_files

    def get_expected_errors(self):
        old_basename = f"sub-{self.sub_id}_arrow-alert-v1-1_psychopy_s1_r1_e1.csv"
        new_basename = old_basename.replace(".csv", "")

        new_path = os.path.join(
            self.case_dir,
            self.build_path("s1_r1", "psychopy", new_basename, self.is_raw),
        )

        naming_info = re.escape(
            f"File {new_path} does not match expected identifier format"
        )
        missing_info = re.escape(f"Expected file {old_basename} not found")
        extra_info = re.escape(f"Unexpected file {new_basename} found")

        errors = [
            ExpectedError("Naming error", naming_info),
            ExpectedError("Missing file", missing_info),
            ExpectedError("Unexpected file", extra_info),
        ]

        return errors


def test_missing_extension(request):
    MissingExtensionTestCase.run_test_case(request)
