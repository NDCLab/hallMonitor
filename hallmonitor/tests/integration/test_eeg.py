import re

from hallmonitor.tests.integration.base_cases import ExpectedError, ValidationTestCase


class EEGTestCase(ValidationTestCase):
    pass


class EEGDataFileVHDRMismatchTestCase(EEGTestCase):
    """
    Test case for mismatched DataFile line in an EEG .vhdr file.
    """

    case_name = "EEGDataFileVHDRMismatchTestCase"
    description = "Edits the DataFile line in a .vhdr file so it does not match the name of the .vhdr file itself."
    conditions = [
        "DataFile line in .vhdr file does not match the .vhdr file name",
    ]
    expected_output = "Error is raised for mismatched DataFile line in the .vhdr file."

    is_raw = True

    def modify(self, base_files):
        modified_files = base_files.copy()

        # define the .vhdr file and the incorrect DataFile line
        vhdr_file = f"sub-{self.sub_id}_all_eeg_s1_r1_e1.vhdr"
        vhdr_file = self.build_path("s1_r1", "eeg", vhdr_file)
        if vhdr_file not in modified_files:
            raise FileNotFoundError(f"File matching basename {vhdr_file} not found")

        # modify the DataFile line in the .vhdr file to introduce the mismatch
        original_content = modified_files[vhdr_file]
        updated_content = original_content.replace(
            f"DataFile=sub-{self.sub_id}_all_eeg_s1_r1_e1.eeg",
            f"DataFile=sub-{self.sub_id}_wrongname_s1_r1_e1.eeg",
        )
        modified_files[vhdr_file] = updated_content

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_PATTERN_s1_r1_e1.eeg"
        correct = basename.replace("PATTERN", "all_eeg")
        incorrect = basename.replace("PATTERN", "wrongname")

        eeg_info = f"Incorrect DataFile {incorrect} in .vhdr file, expected {correct}"
        errors = [ExpectedError("EEG error", re.escape(eeg_info))]

        return errors


def test_eeg_data_file_vhdr_mismatch(request):
    EEGDataFileVHDRMismatchTestCase.run_test_case(request)


class EEGMarkerFileVHDRMismatchTestCase(EEGTestCase):
    """
    Test case for mismatched MarkerFile line in an EEG .vhdr file.
    """

    case_name = "EEGMarkerFileVHDRMismatchTestCase"
    description = "Edits the MarkerFile line in a .vhdr file so it does not match the name of the .vhdr file itself."
    conditions = [
        "MarkerFile line in .vhdr file does not match the .vhdr file name",
    ]
    expected_output = (
        "Error is raised for mismatched MarkerFile line in the .vhdr file."
    )

    is_raw = False

    def modify(self, base_files):
        modified_files = base_files.copy()

        # define the .vhdr file and the incorrect MarkerFile line
        vhdr_file = f"sub-{self.sub_id}_all_eeg_s1_r1_e1.vhdr"
        vhdr_file = self.build_path("s1_r1", "eeg", vhdr_file, self.is_raw)
        if vhdr_file not in modified_files:
            raise FileNotFoundError(f"File matching basename {vhdr_file} not found")

        # modify the MarkerFile line in the .vhdr file to introduce the mismatch
        original_content = modified_files[vhdr_file]
        updated_content = original_content.replace(
            f"MarkerFile=sub-{self.sub_id}_all_eeg_s1_r1_e1.vmrk",
            f"MarkerFile=sub-{self.sub_id}_wrongname_s1_r1_e1.vmrk",
        )
        modified_files[vhdr_file] = updated_content

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_PATTERN_s1_r1_e1.vmrk"
        correct = basename.replace("PATTERN", "all_eeg")
        incorrect = basename.replace("PATTERN", "wrongname")

        eeg_info = f"Incorrect MarkerFile {incorrect} in .vhdr file, expected {correct}"
        errors = [ExpectedError("EEG error", re.escape(eeg_info))]

        return errors


def test_eeg_marker_file_vhdr_mismatch(request):
    EEGMarkerFileVHDRMismatchTestCase.run_test_case(request)


class EEGDataFileVMRKMismatchTestCase(EEGTestCase):
    """
    Test case for mismatched DataFile line in an EEG .vmrk file.
    """

    case_name = "EEGDataFileVMRKMismatchTestCase"
    description = "Edits the DataFile line in a .vmrk file so it does not match the name of the .vmrk file itself."
    conditions = [
        "DataFile line in .vmrk file does not match the .vmrk file name",
    ]
    expected_output = "Error is raised for mismatched DataFile line in the .vmrk file."

    is_raw = False

    def modify(self, base_files):
        modified_files = base_files.copy()

        # define the .vmrk file and the incorrect DataFile line
        vmrk_file = f"sub-{self.sub_id}_all_eeg_s1_r1_e1.vmrk"
        vmrk_file = self.build_path("s1_r1", "eeg", vmrk_file, self.is_raw)
        if vmrk_file not in modified_files:
            raise FileNotFoundError(f"File matching basename {vmrk_file} not found")

        # modify the DataFile line in the .vmrk file to introduce the mismatch
        original_content = modified_files[vmrk_file]
        updated_content = original_content.replace(
            f"DataFile=sub-{self.sub_id}_all_eeg_s1_r1_e1.eeg",
            f"DataFile=sub-{self.sub_id}_wrongname_s1_r1_e1.eeg",
        )
        modified_files[vmrk_file] = updated_content

        return modified_files

    def get_expected_errors(self):
        basename = f"sub-{self.sub_id}_PATTERN_s1_r1_e1.eeg"
        correct = basename.replace("PATTERN", "all_eeg")
        incorrect = basename.replace("PATTERN", "wrongname")

        eeg_info = f"Incorrect DataFile {incorrect} in .vmrk file, expected {correct}"
        errors = [ExpectedError("EEG error", re.escape(eeg_info))]

        return errors


def test_eeg_data_file_vmrk_mismatch(request):
    EEGDataFileVMRKMismatchTestCase.run_test_case(request)
