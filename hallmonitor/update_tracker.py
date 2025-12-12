import logging
import math
import os
import re
import sys
import numpy as np
from collections import defaultdict
from getpass import getuser

import pandas as pd

from hallmonitor.hmutils import (
    REMOTE_REDCAP_PREFIX,
    Identifier,
    SharedTimestamp,
    get_allowed_suffixes,
    get_datadict,
    get_expected_combination_rows,
    get_new_redcaps,
    get_timestamp,
    get_variable_datatype,
    write_pending_errors,
)


def log_tracker_error(logger: logging.Logger, dataset: str, suffix: str, error: str):
    error_info = {
        "datetime": get_timestamp(),
        "user": getuser(),
        "identifier": "",
        "subject": "",
        "dataType": "REDCap",
        "encrypted": False,
        "suffix": suffix,
        "errorType": "Tracker update error",
        "errorDetails": error,
    }
    write_pending_errors(dataset, pd.DataFrame([error_info]), SharedTimestamp())
    logger.error(error)


COMPLETED_SUFFIX = "_complete"
ENGLISH_LANGCODE = 1
SPANISH_LANGCODE = 2


def get_redcap_columns(datadict_df: pd.DataFrame, session: str):
    """Obtains column mappings for all Redcap columns from the data dictionary.

    Args:
        datadict_df (pd.DataFrame): Data dictionary dataframe

    Returns:
        dict[dict[str, str]]: A dict of expected redcaps, and dicts of column mappings from column
        names in the redcap (including Sp. language surveys) to column names in the central tracker,
        drawn from the provenance column in the datadict.
    """
    valid_datatypes = {"consent", "assent", "redcap_data"}
    # only look at REDCap data
    df = datadict_df[datadict_df["dataType"].isin(valid_datatypes)]
    # filter for prov
    cols = {}
    key_counter = defaultdict(lambda: 0)
    allowed_duplicate_columns = []
    for _, row in df.iterrows():
        if isinstance(row["allowedSuffix"], float) and math.isnan(row["allowedSuffix"]):
            allowed_suffixes = [""]
        else:
            allowed_suffixes = str(row["allowedSuffix"]).split(", ")
            allowed_suffixes = [
                x for x in allowed_suffixes if x.startswith(session)
            ]  # only from same session
            allowed_suffixes = ["_" + ses for ses in allowed_suffixes]

        prov = str(row["provenance"]).split()
        rc_variables = []
        var_idx = 0
        if "file:" not in prov:
            continue
        #sets rc_variables to list of variables if multiple variables are present
        if "variables:" in prov:
            var_idx = prov.index("variables:")
            rc_vars = str(prov[var_idx + 1]).strip('";,')
            rc_variables = [str(v).strip('";,') for v in rc_vars.split(",")]
            # remove any empty strings from rc_variables
            rc_variables = [v for v in rc_variables if v != ""]
        elif "variable:" in prov:
            var_idx = prov.index("variable:")
            rc_variable = str(prov[var_idx + 1]).strip('";,')
            rc_variables.append(rc_variable)
        else:
            continue
        #iterates through each variable in rc_variables list
        for rc_variable in rc_variables:
            if rc_variable == "":
                rc_variable = str(row["variable"]).lower()


            file_idx = prov.index("file:")
            # gets filename of redcap
            rc_filename = prov[file_idx + 1].strip('";,')
            if rc_filename not in cols:
                cols[rc_filename] = {}

            if "id:" in prov:
                id_idx = prov.index("id:")
                rc_idcol = prov[id_idx + 1].strip('";,')
                cols[rc_filename]["id_column"] = rc_idcol
            # creates the following:
            # cols["thriveconsent"]["consent_complete"] = "consent"
            # cols["iqsclinician"]["iqsclinician_s1_r1_e1_complete"] = "iqsclinician_s1_r1_e1"

            #adds spanish version below
            for ses_tag in allowed_suffixes:
                # gets the column name in the redcap, e.g consent, all_eeg, arrow-alert_psychopy
                var = row["variable"]
                # maps all redcap variables to their respective column names in central tracker for each rc file
                cols[rc_filename][rc_variable + ses_tag + COMPLETED_SUFFIX] = var + ses_tag
                key_counter[rc_variable + ses_tag + COMPLETED_SUFFIX] += 1
                if "assent" in row["dataType"]:
                    continue
                # also map Sp. surveys to same column name in central tracker if completed
                surv_match = re.fullmatch(
                    r"([A-Za-z0-9]+)(_[a-z0-9]{1,2})?(_scrd[a-zA-Z]+)?(_[a-zA-Z]{2,})?", rc_variable
                )
                # breaks it down into base, version, scored string, multiple report tag
                # adds 'es' after base to form Spanish survey name
                # Example cbcl_01_scrdA_p1 -> [cbcl + es +,_01,_scrdA_,p1] -> cbcles_01_scrdA_p1 
                if surv_match is not None:
                    surv_version = surv_match.group(2) or ""
                    scrd_str = surv_match.group(3) or ""
                    multiple_report_tag = surv_match.group(4) or ""
                    surv_esp = (
                        surv_match.group(1)
                        + "es"
                        + surv_version
                        + scrd_str
                        + multiple_report_tag
                        + ses_tag
                    )
                    cols[rc_filename][surv_esp + COMPLETED_SUFFIX] = var + ses_tag
                    # checks for duplicates
                    key_counter[surv_esp + COMPLETED_SUFFIX] += 1
    # the key counter keeps track of how many times each key appears across all redcaps
    for key, value in key_counter.items():
        if value > 1:
            allowed_duplicate_columns.append(key)
    return cols, allowed_duplicate_columns

    
def get_all_subject_ids(dataset):
    """
    Get a list of subject IDs from the dataset's specified ID REDCap column.

    Args:
        dataset (str): The path to the dataset's base directory.

    Raises:
        ValueError: If the dataset's data dictionary contains an invalid provenance for the ID variable.
        FileNotFoundError: If no file matches the specified REDCap stem.
        FileExistsError: If multiple files match the specified REDCap stem.

    Returns:
        list[int]: A list of the dataset's subject IDs.
    """
    dd_df = get_datadict(dataset)
    redcap_dir = os.path.join(dataset, "sourcedata", "checked", "redcap")
    id_row = dd_df[dd_df["variable"] == "id"].iloc[0]
    id_prov = str(id_row["provenance"])

    filename_match = re.search(r"file:\s*\"([^\s]+)\"", id_prov)
    if filename_match is None:
        raise ValueError(f"No ID REDCap given in provenance '{id_prov}'")
    redcap_stem = filename_match.group(1).lower()

    variable_match = re.search(r"variable:\s*\"([^\s]+)\"", id_prov)
    if variable_match is None:
        raise ValueError(f"No ID variable given in provenance '{id_prov}'")
    id_variable = variable_match.group(1)

    newest_redcaps = get_new_redcaps(redcap_dir)
    matching_redcaps = [
        redcap
        for redcap in newest_redcaps
        if redcap_stem in os.path.basename(redcap).lower()
    ]
    if len(matching_redcaps) == 0:
        raise FileNotFoundError(f"Can't find '{redcap_stem}' REDCap to read IDs from")
    elif len(matching_redcaps) > 1:
        raise FileExistsError(
            f"Found multiple REDCaps matching '{redcap_stem}': {', '.join(matching_redcaps)}"
        )

    redcap_df = pd.read_csv(matching_redcaps[0], usecols={id_variable})
    all_sub_ids = redcap_df[id_variable].astype(int).tolist()
    return all_sub_ids


def get_study_num(dataset):
    """
    Get the study's two-digit study number from allowed values for subject ID.

    Args:
        dataset (str): The path to the dataset's base directory.

    Raises:
        ValueError: If the dataset's study number cannot be determined.

    Returns:
        str: The dataset's two-digit study number.
    """
    dd_df = get_datadict(dataset)
    id_row = dd_df[dd_df["variable"] == "id"].iloc[0]
    allowed_vals = str(id_row["allowedValues"])
    allowed_vals = allowed_vals.replace(" ", "")
    intervals = re.split(r"[\[\]]", allowed_vals)

    for interval in intervals:
        interval = str(interval)
        if interval not in {"", ","}:
            return interval[:2]

    raise ValueError("Could not find study number")


def fill_combination_columns(dataset: str, tracker_df: pd.DataFrame):
    """
    Fill in combination columns by checking for the presence of one or more "child variables".

    Args:
        dataset (str): The path to the dataset's base directory.
        tracker_df (pd.DataFrame): The dataset's central tracker.
    Returns:
        pd.DataFrame: The updated central tracker.
    """
    combination_rows = get_expected_combination_rows(dataset)

    for combo in combination_rows:
        combo_suffixes = get_allowed_suffixes(dataset, combo.name)
        for suffix in combo_suffixes:
            combo_col = f"{combo.name}_{suffix}"
            var_cols = pd.Index([f"{var}_{suffix}" for var in combo.variables])
            # some variables may not be valid for this suffix, skip them
            var_cols = var_cols[var_cols.isin(tracker_df.columns)]
            print("[CUSTOM DEBUG] Filling combination column...")
            print("var_cols:", var_cols, type(var_cols))
            print("combo_col:", combo_col, type(combo_col))
            # we treat the combination column as an aggregator that is 1 if
            #   any of its "child variables" are truthy and 0 otherwise
            tracker_df[combo_col] = (tracker_df[var_cols].replace("0", 0).fillna(0) != 0).any(axis="columns").astype(int)

            if (tracker_df[combo_col] == 0).all():
                # if the combination column is all 0, we leave it blank
                tracker_df[combo_col] = ""

    return tracker_df


def fill_status_data_columns(dataset: str, tracker_df: pd.DataFrame):
    """
    Fill in "status" and "data" columns based on their specified values.

    Args:
        dataset (str): The path to the dataset's base directory.
        tracker_df (pd.DataFrame): The dataset's central tracker.
    Returns:
        pd.DataFrame: The updated central tracker.
    """
    dd_df = get_datadict(dataset)
    redcaps = get_new_redcaps(os.path.join(dataset, "sourcedata", "checked", "redcap"))

    status_var_rows = dd_df[dd_df["dataType"] == "visit_status"]
    data_var_rows = dd_df[dd_df["dataType"] == "visit_data"]

    for _, row in status_var_rows.iterrows():
        prov = str(row["provenance"])
        suffixes = get_allowed_suffixes(dataset, row["variable"])
        prov_file = re.search(r'file:\s*"([^"\s]+)"', prov)
        prov_var = re.search(r'variable:\s*"([^"\s]+)"', prov)
        if None not in {prov_file, prov_var}:  # ensure both matches exist
            prov_file = str(prov_file.group(1))
            prov_var = str(prov_var.group(1))

            for suffix in suffixes:
                prov_id_match = re.search(r'id:\s*"([^"\s]+)"', prov)
                if prov_id_match:
                    prov_id = f"{prov_id_match.group(1)}_{suffix}"
                else:
                    prov_id = "record_id"

                # get session from suffix
                ses = suffix.split("_")[0]
                # find matching redcap files
                matching_rc = [
                    rc
                    for rc in redcaps
                    if prov_file.lower() in rc.lower() and ses in rc
                ]
                if len(matching_rc) == 0:
                    continue
                rc_df = pd.read_csv(matching_rc[0])
                # find matching columns in redcap dataframe
                matching_cols = rc_df.columns[
                    (rc_df.columns.str.contains(f"{prov_var}_{suffix}"))
                    & (rc_df.columns.str.endswith(COMPLETED_SUFFIX))
                ]
                if len(matching_cols) == 0:
                    continue
                matching_col = matching_cols[0]
                # set index to the provenance id column
                rc_df = rc_df.set_index(prov_id)
                # deduplicate index
                if rc_df.index.duplicated().any():
                    rc_df = rc_df.groupby(rc_df.index).first()
                # get matching column data and convert to int
                rc_df[matching_col] = (rc_df[matching_col].astype(int) == 2).astype(int)
                # update tracker dataframe with matching column data
                shared_sub_ids = tracker_df.index.intersection(rc_df.index)
                tracker_df.loc[shared_sub_ids, row["variable"] + "_" + suffix] = (
                    rc_df.loc[shared_sub_ids, matching_col].values
                )

    for _, row in data_var_rows.iterrows():
        prov = str(row["provenance"])
        suffixes = get_allowed_suffixes(dataset, row["variable"])
        if "variables:" in prov and "file:" not in prov:
            prov_vars = re.findall(r'"([^"]+)"', prov)
            for suffix in suffixes:
                # create column names by combining each variable with the current suffix
                colnames = [f"{var}_{suffix}" for var in prov_vars]
                # filter out any column names that don't exist in the tracker
                valid_colnames = [col for col in colnames if col in tracker_df.columns]
                if not valid_colnames:
                    continue
                # check if all specified columns are True for each row
                all_true = tracker_df[valid_colnames].all(axis="columns")
                # set the status column to 1 where all components are True
                status_colname = f"{row['variable']}_{suffix}"
                tracker_df[status_colname] = all_true.astype(int)

        elif "file:" in prov:
            prov_files = re.findall(r'"([^\s"]+)"', prov)
            for suffix in suffixes:
                ses = suffix.split("_")[0]
                colname = f"{row['variable']}_{suffix}"
                # set to 1 by default; we set to 0 if any file is missing
                tracker_df[colname] = 1
                for file in prov_files:
                    matching_rc = [
                        rc for rc in redcaps if file.lower() in rc.lower() and ses in rc
                    ]
                    if len(matching_rc) == 0:
                        tracker_df[colname] = 0
                        break
                    rc_df = pd.read_csv(matching_rc[0])
                    common_subjects = tracker_df.index.intersection(rc_df["record_id"])
                    tracker_df.loc[~tracker_df.index.isin(common_subjects), colname] = 0

    return tracker_df


def get_child_id(parent_id: str, study_no: str) -> int | None:
    """
    Given a parent ID, extract and return the corresponding child ID.

    Args:
        parent_id (str): The parent ID string.
        study_no (str): The two-digit study number.

    Returns:
        int | None: The corresponding child ID as an integer, or None if no match is found.
    """
    child_id_match = re.search(study_no + r"([089])(\d{4})", str(parent_id))
    if child_id_match is None:
        return None
    child_id = study_no + "0" + child_id_match.group(2)
    return int(child_id)

#TODO Refactor tracker_df into some class or data structure to avoid passing it around so much

def get_parent_columns(
    datadict_df: pd.DataFrame,
    tracker_df: pd.DataFrame,
    study_no,
    session,
    all_redcap_paths,
):
    """
    Populate parent_identity (pidentity) and parent_language (plang) columns in central tracker (8 = primary
    parent, 9 = secondary parent), return a dict of Redcaps with their respective plang and pidentity columns
    """
    parent_info = defaultdict(list)
    for _, row in datadict_df.iterrows():
        if row["dataType"] == "parent_identity":
            prov = str(row["provenance"]).split()
            if "file:" in prov and "variable:" in prov:
                file_idx = prov.index("file:")
                rc_filename = prov[file_idx + 1].strip('";')
                var_idx = prov.index("variable:")
                rc_variable = prov[var_idx + 1].strip('";')
                parent_info[rc_filename].append(row["variable"])
                
            else:
                continue
            rc_df = pd.read_csv(all_redcap_paths[rc_filename])
            parent_ids = []
            for suf in str(row["allowedSuffix"]).split(", "):
                rc_var_suf = rc_variable + "_" + suf
                if rc_var_suf in rc_df.columns:
                    try:
                        parent_ids = rc_df[rc_var_suf].to_list()
                    except Exception:  # FIXME
                        raise ValueError(f"Error processing column {rc_var_suf} in file {all_redcap_paths[rc_filename]} all columns: {rc_df.columns.tolist()}")
            for id in parent_ids:
                child_id_match = re.search(study_no + r"([089])(\d{4})", str(id))
                if child_id_match is None:
                    continue
                child_id = study_no + "0" + child_id_match.group(2)
                child_id = int(child_id)
                parent = study_no + child_id_match.group(1)

                try:
                    for suf in str(row["allowedSuffix"]).split(","):
                        suf = suf.strip()
                        if re.fullmatch(session + r"_e\d$", suf):
                            tracker_df.loc[child_id, row["variable"] + "_" + suf] = int(
                                parent
                            )
                except Exception:  # FIXME
                    raise ValueError(f"Error setting tracker_df at child_id {child_id}, variable {row['variable']}_{suf} for val {parent}")

        elif row["dataType"] == "parent_lang":
            prov = str(row["provenance"]).split()

            if "file:" not in prov or "variable:" not in prov:
                continue

            idx = prov.index("file:")
            rc_filename = prov[idx + 1].strip('";')
            idx = prov.index("variable:")
            rc_variable = prov[idx + 1].strip('";')
            parent_info[rc_filename].append(row["variable"])

            rc_df = pd.read_csv(all_redcap_paths[rc_filename], index_col="record_id")
            for col in rc_df.columns:
                lang_re = re.match(rc_variable + r"_(s\d+_r\d+_e\d+)", col)
                if lang_re is not None:
                    for _, rc_row in rc_df.iterrows():
                        child_id_match = re.search(
                            study_no + r"[089](\d{4})", str(rc_row.name)
                        )
                        if child_id_match is not None:
                            child_id = study_no + "0" + child_id_match.group(1)
                            child_id = int(child_id)
                            # throws error here!
                            if rc_row[col] not in {ENGLISH_LANGCODE, SPANISH_LANGCODE} and not np.isnan(rc_row[col]):
                                raise ValueError(
                                    f"Unknown value {rc_row[col]} seen for parent language "
                                    + f"in REDCap {all_redcap_paths[rc_filename]}, "
                                    + f"should be {ENGLISH_LANGCODE} for English and {SPANISH_LANGCODE} for Spanish."
                                )

                            try:
                                for suf in str(row["allowedSuffix"]).split(", "):
                                    if re.fullmatch(session + r"_e\d+", suf):
                                        tracker_df.loc[
                                            child_id, row["variable"] + "_" + suf
                                        ] = int(rc_row[col])
                            except Exception:  # FIXME
                                continue

    return dict(parent_info)

def check_consent_tracker(
    tracker_df: pd.DataFrame,
    variables: list[str] = ["consent","assent"],
):
    """
    Check that for any rows where any key variables are marked as 0 and has data filled in and throws ValueError if so.

    Args:
        tracker_df (pd.DataFrame): The dataset's central tracker.
        variables (list[str], optional): List of key variables to check. Defaults to ["consent"].
    """
    invalid_rows = []
    # Create a mask for rows where any of the key variables are 0
    key_zero_mask = (tracker_df[variables] == 0).any(axis=1)

    other_data = tracker_df.drop(columns=variables, errors='ignore')
    # Check if any other data is present in those rows that are not 0 or NaN
    other_data_present = ((other_data.notna()) & (other_data == 1)).any(axis=1)


    # returns list of invalid row indices

    invalid_rows = tracker_df.index[key_zero_mask & other_data_present].tolist()
    # if there are invalid rows, raise ValueError
    if invalid_rows:
        raise ValueError(
            f"Invalid data found in rows: {invalid_rows} where key variables are marked as 0 but other data is present."
        )
    

def main(
    dataset: str,
    redcaps: list[str],
    session: str,
    child: bool,
    passed_id_list: list[str],
    failed_id_list: list[str],
) -> bool:
    dataset = os.path.abspath(dataset)
    if not os.path.exists(dataset):
        raise FileNotFoundError(f"{dataset} does not exist")
    elif not os.path.isdir(dataset):
        raise NotADirectoryError(f"{dataset} is not a directory")

    if not redcaps:
        raise ValueError(f"No REDCaps passed for dataset {dataset}")

    if not session:
        raise ValueError(f"No session passed for dataset {dataset}")

    if not passed_id_list and not failed_id_list:
        raise ValueError("No passed or failed identifiers passed")

    logger = logging.getLogger()
    logger = logger.getChild("UpdateTracker")

    # function-level global variable to check whether any errors occurred
    successful_update = True

    # gets all passed and failed ids
    passed_ids = [(Identifier.from_str(s), 1) for s in passed_id_list]
    failed_ids = [(Identifier.from_str(s), 0) for s in failed_id_list]
    all_ids = passed_ids + failed_ids
    id_df = pd.DataFrame(
        [
            {
                "id": int(id.subject.removeprefix("sub-")),
                "colname": f"{id.variable}_{id.session}_{id.run}_{id.event}",
                "variable": id.variable,
                "datatype": get_variable_datatype(dataset, id.variable),
                "passed": pass_val,  # 1 for verified IDs, 0 for failing IDs
            }
            for id, pass_val in all_ids
        ]
    )

    # Log our passed/failed ID info
    logger.debug("Got %d passed identifier(s)", len(passed_ids))
    logger.debug("Got %d failed identifier(s)", len(failed_ids))

    # get redcap columns from datadict
    dd_df = get_datadict(dataset)
    redcheck_columns, allowed_duplicate_columns = get_redcap_columns(dd_df, session)
    
    # "Welcome" survey is needed across multiple projects, so we ignore it (and its Spanish variant)
    allowed_duplicate_columns.append(f"welcome_{session}_e1{COMPLETED_SUFFIX}")
    allowed_duplicate_columns.append(
        f"welcomees_{session}_e1{COMPLETED_SUFFIX}")
    logger.debug(
        "Redcheck columns: %s",
        ", ".join(f"{k} ({v})" for k, v in redcheck_columns.items()),
    )
    logger.debug("Allowed duplicate columns: %s", ", ".join(allowed_duplicate_columns))
    ids = get_all_subject_ids(dataset)
    study_no = get_study_num(dataset)

    tracker_df = get_central_tracker(dataset)
    # tracker_df = tracker_df.replace("0", 0)
    proj_name = os.path.basename(os.path.normpath(dataset)).removesuffix("-dataset")
    # FIXME FIXME FIXME DO NOT INCLUDE THIS IN PRODUCTION CODE
    if "-" in proj_name:
        proj_name = proj_name.split("-")[1]

    logger.debug("Project name: %s", proj_name)
    data_tracker_file = os.path.join(
        dataset, "data-monitoring", f"central-tracker_{proj_name}.csv"
    )

    # add new subjects to the central tracker, if there are any
    tracker_ids = tracker_df["id"].tolist()
    new_subjects = list(set(ids).difference(tracker_ids))
    logger.debug("Found %d new subject(s)", len(new_subjects))
    new_subjects_df = pd.DataFrame({"id": new_subjects})
    tracker_df = pd.concat([tracker_df, new_subjects_df])

    tracker_df = tracker_df.set_index("id").sort_index()

    subjects = tracker_df.index.to_list()

    # all central tracker redcap columns
    all_redcheck_cols = list({v for rc in redcheck_columns.values() for v in rc.values()})
    # make sure it's in the tracker
    all_redcheck_cols = [col for col in all_redcheck_cols if col in tracker_df.columns]
        

    # list of all redcap columns whose names should be mirrored in central tracker
    all_redcap_columns = defaultdict(list)
    all_redcap_paths = dict()

    all_rc_dfs = dict()
    all_rc_subjects = dict()
    for expected_rc in redcheck_columns.keys():
        logger.debug("Processing expected REDCap %s", expected_rc)
        present = False
        remote_rcs = [
            r
            for r in redcaps
            if os.path.basename(r).startswith(REMOTE_REDCAP_PREFIX + proj_name)
        ]
        normal_rcs = [r for r in redcaps if r not in remote_rcs]
        logger.debug(
            "Found %d normal RC(s), %d remote RC(s)", len(normal_rcs), len(remote_rcs)
        )

        matching_rcs = list(
            filter(
                lambda rc: expected_rc.lower() in os.path.basename(rc).lower(),
                normal_rcs,
            )
        )
        logger.debug("Found %d matching RC(s)", len(matching_rcs))
        if len(matching_rcs) == 0:
            log_tracker_error(
                logger,
                dataset,
                session,
                f"Could not find a file matching {expected_rc}",
            )
            successful_update = False
            continue
        elif len(matching_rcs) > 1:
            log_tracker_error(
                logger,
                dataset,
                session,
                f'Multiple REDCaps found with name "{expected_rc}" specified in datadict: {", ".join(matching_rcs)}',
            )
            successful_update = False
            continue
        else:  # desired case with N=1 match
            redcap_path = matching_rcs[0]
            all_redcap_paths[expected_rc] = redcap_path
            present = True
            logger.debug("Found match %s", redcap_path)

        remote_rc = ""
        for redcap in remote_rcs:
            logger.debug("Processing remote RC %s", redcap)
            rc_basename = os.path.basename(redcap.lower())
            if expected_rc not in rc_basename:
                continue

            present = True
            if expected_rc in all_redcap_paths:
                # save remote redcap for later
                remote_rc = redcap
                logger.debug("Saving remote RC for later")
            else:
                # treat remote redcap as the only redcap
                redcap_path = redcap
                all_redcap_paths[expected_rc] = redcap
                logger.debug("Treating remote RC as only REDCap")

            break

        if not present:
            log_tracker_error(
                logger,
                dataset,
                session,
                f'Can\'t find redcap "{expected_rc}" specified in datadict',
            )
            successful_update = False
            continue

        # re-index redcap and save to redcheck_columns

        if "id_column" in redcheck_columns[expected_rc].keys():
            # ID column has been specified
            id_col = str(redcheck_columns[expected_rc]["id_column"])
            logger.debug("ID column specified: %s", id_col)
        else:  # no ID column specified, use default
            id_col = "record_id"
            logger.debug("ID column unspecified, using %s", id_col)

        rc_df = pd.read_csv(redcap_path)

        # get matching ID column
        # needs matching ID column to map to tracker
        rc_cols = rc_df.columns
        col_matches = rc_cols[rc_cols.str.startswith(id_col)]
        if col_matches.empty:  # column match not found, raise an error
            log_tracker_error(
                logger,
                dataset,
                session,
                f"Column {id_col} not found for RedCAP {redcap_path}",
            )
            successful_update = False
            continue
        logger.debug("Found column matches %s", ", ".join(col_matches))
        rc_id_col = col_matches[0]

        if remote_rc:  # if there is both a remote and in-person redcap...
            remote_df = pd.read_csv(remote_rc)

            # ...ensure that each subject is only in one redcap or the other, then...
            duped_subs = set(remote_df[rc_id_col]) & set(rc_df[rc_id_col])
            if duped_subs:
                log_tracker_error(
                    logger,
                    dataset,
                    session,
                    f"The following subjects are in the remote-only and in-person REDCaps for {expected_rc}: "
                    + ", ".join(str(sub) for sub in duped_subs),
                )
                successful_update = False
                continue

            # ...append remote RC to in-person RC, since variables are the same
            rc_df = pd.concat([rc_df, remote_df])

        # re-index rc_df on the selected column
        all_rc_dfs[expected_rc] = rc_df.set_index(rc_id_col)

        # If hallMonitor passes "redcap" arg, data exists and passed checks
        vals = pd.read_csv(redcap_path, header=None, nrows=1).iloc[0, :].value_counts()
        # Exit if duplicate column names in redcap
        if any(vals.values != 1):
            dupes = []
            for rc_col in vals.keys():
                if vals[rc_col] > 1:
                    dupes.append(rc_col)
            log_tracker_error(
                logger,
                dataset,
                session,
                f"Duplicate columns found in redcap {redcap_path}: " + ", ".join(dupes),
            )
            return False

    logger.debug("Finished initial REDCap matching, proceeding to update tracker")

    for expected_rc in redcheck_columns.keys():
        if expected_rc not in all_rc_dfs.keys():
            log_tracker_error(
                logger,
                dataset,
                session,
                f"Could not find {expected_rc} in all_rc_dfs, skipping",
            )
            continue

        logger.debug("Updating tracker for %s", expected_rc)
        rc_df = all_rc_dfs[expected_rc]
        rc_subjects = []
        rc_ids = rc_df.index.tolist()
        if child:
            for id in rc_ids:
                # FIXME magic numbers, repeated code
                child_id_match = re.search(study_no + r"[089](\d{4})", str(id))
                if child_id_match is not None:
                    child_id = int(study_no + "0" + child_id_match.group(1))
                    rc_subjects.append(child_id)
                    logger.debug(
                        "Child ID %s found for parent ID %s", str(child_id), str(id)
                    )
        else:
            rc_subjects = rc_ids
        rc_subjects.sort()

        all_rc_subjects[expected_rc] = rc_subjects

        all_keys = dict()
        for key, value in redcheck_columns[expected_rc].items():
            all_keys[key] = value
            if str(key).startswith(("consent", "assent", "id_column")):
                continue
            if (
                not re.match(
                    r"^.*es(?:_[a-zA-Z])?_s\d+_r\d+_e\d+" + COMPLETED_SUFFIX, key
                )
                and key not in all_rc_dfs[expected_rc].columns
            ):
                other_rcs = []
                other_rc_dfs = {
                    rc: all_rc_dfs[rc] for rc in all_rc_dfs if rc != expected_rc
                }
                for redcap, other_rc_df in other_rc_dfs.items():
                    if key in other_rc_df.columns:
                        other_rcs.append(redcap)
                if len(other_rcs) >= 1:
                    log_tracker_error(
                        logger,
                        dataset,
                        session,
                        f'Can\'t find "{key}" in {expected_rc} redcap, but found in '
                        + ", ".join(other_rcs)
                        + " redcaps",
                    )
                    successful_update = False
                    continue
                else:
                    log_tracker_error(
                        logger,
                        dataset,
                        session,
                        f'Can\'t find "{key}" in {expected_rc} redcap',
                    )
                    successful_update = False
                    continue
        # fill in redcap data into central tracker
        for index, row in rc_df.iterrows():
            if pd.isna(index):
                logger.info(
                    "Skipping NaN value in %s", str(all_redcap_paths[expected_rc])
                )
                continue

            id = int(row.name)

            if child:
                # FIXME magic numbers
                #checks for child ID from parent ID
                child_id_match = re.search(study_no + r"[089](\d{4})", str(id))
                if child_id_match is not None:
                    child_id = study_no + "0" + child_id_match.group(1)
                    child_id = int(child_id)
                else:
                    logger.info(
                        '%s doesn\'t match expected child or parent id format of "%s{0,8, or 9}XXXX", skipping',
                        str(id),
                        study_no,
                    )
                    continue
            else:
                child_id = id

            if child_id not in tracker_df.index:
                logger.info("%s missing in tracker file, skipping", str(child_id))
                continue
            # These are the key variables that must be checked for data integrity
            # Reset these as needed to ensure data consistency with redcap
            required_cols = {"consent", "assent"}
            isReset = False
            # check if all keys contains any of the required columns
            required_cols = {v for k, v in all_keys.items() if v in required_cols}
            required_cols = list(required_cols)
            if required_cols:
                try:
                    # reset key variables to 0 before filling in from redcap so past data doesn't persist
                    if tracker_df.loc[child_id, required_cols].any() == 1:
                        # all columns except required_cols must now be set to 0
                        isReset = True

                    tracker_df.loc[child_id, required_cols] = 0
                except Exception:  # FIXME
                    pass
            
            # fill in redcap data into central tracker
            keys_in_redcap = dict()           
            for key, value in all_keys.items():
                # {key: consent_v2_complete value: consent}
                try:
                    val = rc_df.loc[id, key]
                    keys_in_redcap[key] = value
                    try:
                        if tracker_df.loc[child_id, value] == 1:
                            # if value already set continue
                            continue
                        else:
                            # FIXME magic number
                            tracker_df.loc[child_id, value] = 1 if val == 2 else 0
                    except Exception:  # FIXME
                        # FIXME magic number
                        tracker_df.loc[child_id, value] = 1 if val == 2 else 0
                except Exception:  # FIXME
                    continue
            if isReset:
                # check if the value remains 0 for required columns after filling in from redcap
                if tracker_df.loc[child_id, required_cols].any() == 0:
                    logger.debug(
                        "Reset required columns %s for subject %s before filling in from redcap",
                        ", ".join(required_cols),
                        str(child_id),
                    )
                    # set all other columns  that are check by redcheck to 0
                    for col in tracker_df.columns:
                        if col not in required_cols:
                            try:
                                tracker_df.loc[child_id, col] = None
                            except Exception:  # FIXME
                                logger.info(
                                    "Could not reset column %s for subject %s",
                                    col,
                                    str(child_id),
                                )
                                continue

        # for subject IDs missing from redcap, fill in "0" in redcap columns
        for subj in set(subjects).difference(rc_subjects):
            for key, value in keys_in_redcap.items():
                if re.fullmatch(r".*" + session + r"_e\d+", value):
                    try:
                        tracker_df.loc[subj, value] = 0
                    except Exception:  # FIXME
                        continue

        duplicate_cols = []
        # drop any duplicate columns ending in ".NUMBER"
        for col in tracker_df.columns:
            if re.fullmatch(r".*\.\d+", col):
                duplicate_cols.append(col)
        tracker_df.drop(columns=duplicate_cols, inplace=True)
        tracker_df.to_csv(data_tracker_file)

        for col in rc_df.columns:
            if str(col).endswith(COMPLETED_SUFFIX):
                all_redcap_columns[col].append(all_redcap_paths[expected_rc])

    parent_info = get_parent_columns(
        dd_df, tracker_df, study_no, session, all_redcap_paths
    )

    # Fill in "NA"s in parent cols for all subjects not present in redcap
    # FIXME deep nesting with minimal comments
    for expected_rc in redcheck_columns.keys():
        if expected_rc in parent_info.keys():
            for subj in set(subjects).difference(all_rc_subjects[expected_rc]):
                for col in tracker_df.columns:
                    for var in parent_info[expected_rc]:
                        if re.fullmatch(f"{var}_{session}" + r"_e\d+", col):
                            try:
                                tracker_df.loc[subj, col] = None
                            except Exception:  # FIXME
                                continue

    all_duplicate_cols = []
    redcaps_of_duplicates = []
    for col, rcs in all_redcap_columns.items():
        if len(all_redcap_columns[col]) > 1 and col not in allowed_duplicate_columns:
            all_duplicate_cols.append(col)
            redcaps_of_duplicates.append(", ".join(rcs))

    if len(all_duplicate_cols) > 0:
        errmsg = "Duplicate columns were found across Redcaps: "
        for i in range(0, len(all_duplicate_cols)):
            errmsg = (
                errmsg
                + all_duplicate_cols[i]
                + " in "
                + redcaps_of_duplicates[i]
                + "; Exiting."
            )
        log_tracker_error(logger, dataset, session, errmsg)
        successful_update = False

    # update central tracker with a 1 for each fully-verified identifier

    # ...but first, make sure all column names are valid
    invalid_cols = id_df[~id_df["colname"].isin(tracker_df.columns)]["colname"]
    if not invalid_cols.empty:
        print(f"Invalid column(s) found: {', '.join(invalid_cols.unique())}, skipping")
        id_df = id_df[~id_df["colname"].isin(invalid_cols)]

    # ...and do the same for subject IDs

    invalid_ids = id_df[~id_df["id"].isin(tracker_df.index)]["id"]
    if not invalid_ids.empty:
        log_tracker_error(
            logger,
            dataset,
            session,
            "Invalid ID(s) found: "
            + ", ".join(map(str, invalid_ids.unique()))
            + ", skipping",
        )
        id_df = id_df[~id_df["id"].isin(invalid_ids)]

    # we're all set, update the tracker with an appropriate pass/fail value
    for _, row in id_df.iterrows():
        tracker_df.loc[int(row["id"]), row["colname"]] = row["passed"]

    # fill in combination columns based on the values of their "child variables"
    tracker_df = fill_combination_columns(dataset, tracker_df)

    # fill in "status"/"data" columns based on their specified values
    tracker_df = fill_status_data_columns(dataset, tracker_df)

    # Last Check: Ensure no data exists for subjects who did not consent
    # check_consent_tracker(tracker_df, variables=["consent","assent"])

    # save the updated tracker as our final step
    tracker_df.to_csv(data_tracker_file)


    # Create more readable csv with no blank columns
    tracker_df = pd.read_csv(data_tracker_file, index_col="id")
    data_tracker_filename = os.path.splitext(data_tracker_file)[0]
    tracker_df_no_blank_columns = tracker_df.loc[:, tracker_df.notnull().any(axis=0)]
    tracker_df_no_blank_columns = tracker_df_no_blank_columns.fillna("NA")
    tracker_df_no_blank_columns.to_csv(data_tracker_filename + "_viewable.csv")

    updated_datatypes = ", ".join(id_df["variable"].unique())
    if updated_datatypes:
        logger.info("Success: %s data tracker updated.", updated_datatypes)
    else:
        logger.info("Success: No datatypes updated.")

    return successful_update


def get_central_tracker(dataset):
    """
    Returns the given dataset's central tracker as a DataFrame.

    Args:
        dataset (str): The path to the dataset's base directory.

    Returns:
        pandas.DataFrame: The dataset's central tracker.
    """
    proj_name = os.path.basename(os.path.normpath(dataset))
    data_tracker_file = os.path.join(
        dataset, "data-monitoring", f"central-tracker_{proj_name}.csv"
    )
    tracker_df = pd.read_csv(data_tracker_file)
    return tracker_df


if __name__ == "__main__":
    dataset = sys.argv[1]
    redcaps = sys.argv[2]
    session = sys.argv[3]
    child = sys.argv[4]
    passed_ids = sys.argv[5]
    failed_ids = sys.argv[6]

    main(
        dataset,
        redcaps.split(","),
        session,
        bool(child == "true"),
        passed_ids.split(","),
        failed_ids.split(","),
    )
    exit(0)
