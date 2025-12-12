
## Commands
To compress the hallMonitor package into a Singularity image, use the following command:

```bash
singularity build hallmonitor.sif Singularity.def
```

To run the hallMonitor package within the Singularity image, use the following command:

```bash
singularity exec hallMonitor.sif python3 -m hallmonitor
```

For faster editing and testing, you can use Apptainer to create a writable sandbox directory instead of a single image file:

```bash
singularity build --sandbox my_container_folder/ your_image.sif
```

However, files will be located in /usr/local/lib/python3.13/site-packages/hallmonitor within the container.
To compress changes, you can re-build the image from the sandbox:

```bash
singularity build your_new_image.sif my_container_folder/
```

## Flags

### Command-Line Flags

- `dataset`  
	**(positional argument)**  
	Path to the dataset's root directory (can be relative).

- `-c`, `--child-data`  
	Dataset includes child data.

- `-i`, `--ignore-before`  
	Automatically pass all identifiers whose files were last modified before this date.  
	**Format:** YYYY-MM-DD

- `-l`, `--legacy-exceptions`  
	Use legacy exception file behavior (deviation.txt and no-data.txt do not include identifier name).

- `-n`, `--no-color`  
	Disable color in output, useful for logging or plain-text environments.

- `--no-qa`  
	Skip the QA (quality assurance) step of the pipeline.

- `-o`, `--output`  
	File path for logger output (defaults to timestamped file in data-monitoring/logs/).

- `--suppress-missing-pending-qa`  
	Skip “missing identifier” errors when an identifier is absent from checked but present in pending-qa. An error is raised only if the identifier is missing from both lists, letting mid-pipeline runs proceed without noise.

#### Data Validation Limiting (mutually exclusive):

- `--checked-only`  
	Only run data validation for data in `sourcedata/checked/`.

- `--raw-only`  
	Only run data validation for data in `sourcedata/raw/`.

#### Verbosity (mutually exclusive):

- `-v`, `--verbose`  
	Print additional debugging information to the console.

- `-q`, `--quiet`  
	Do not print any information to the console.

#### REDCap Column Mapping (mutually exclusive):

- `-r`, `--replace`  
	Replace all REDCap columns with the passed values.  
	**Usage:** `-r col1 col2 ...`

- `-m`, `--map`  
	Remap the names of specified REDCap columns.  
	**Usage:** `-m old1:new1 old2:new2 ...`

---


These flags control the behavior of the data validation and monitoring script, allowing customization of input, output, validation scope, verbosity, and REDCap column handling.

## Key Files

- **hmutils.py**  
	Contains core utility functions and classes for the Hallmonitor pipeline.  
	- Handles file and identifier parsing, data dictionary access, validation logic, and record creation.
	- Provides helper functions for naming conventions, error handling, and QA checklist management.
	- Used throughout the package for consistent data validation and processing.

- **setup.py**  
	Standard Python packaging script for Hallmonitor.  
	- Defines the package name, version, dependencies, and included modules.
	- Used for installation and distribution of the Hallmonitor package.

- **app.py**  
	The main application entry point for the Hallmonitor pipeline.  
	- Orchestrates the data validation workflow, logging, and error handling.
	- Integrates utility functions from `hmutils.py` and calls `update_tracker` for updating central trackers.
	- Can be run as a script to execute the full data validation and monitoring process.

- **update_tracker.py**  
	Handles updating the central tracker files for datasets.  
	- Processes REDCap and data files, updates tracker CSVs, and logs changes or errors.
	- Provides functions for error logging and tracker management.
	- Called at the end of `app.py` as part of the pipeline.


