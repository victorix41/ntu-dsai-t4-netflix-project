# Netflix Data Pipeline Orchestration with Dagster & dbt

This repository contains an automated, end-to-end data pipeline managed by **Dagster** that sequentially executes data extraction, Google Cloud Storage staging, BigQuery warehouse loading, and production data transformations via **dbt**.

## Pipeline Execution Sequence

The pipeline enforces a strict sequential dependency graph across 3 core stages:
1. **`01_extract_and_upload_to_gcs`**: Runs a standalone Python script to fetch raw data and push it into a GCS bucket storage layer.
2. **`02_load_gcs_to_bigquery`**: Ingests raw objects from GCS and loads structured tables into your target Google BigQuery project workspace (`ntu-dsai-t4-netflix`).
3. **`03_dbt_build`**: Automatically executes a complete `dbt build` cycle to perform star-schema transformations over your warehouse datasets and run data quality test suites.

---

## Technical Architecture & Layout

The project components are configured dynamically without hardcoded absolute folder paths using the following layout:

```text
ntu-dsai-t4-netflix-project/
├── dbt_netflix/                 # Core dbt project models and tests
│   ├── models/                  # Star-schema dimension and fact models
│   ├── logs/                    # Compiled internal dbt logs (dbt.log)
│   └── dbt_project.yml
├── scripts/                     # Standalone extraction processing scripts
│   ├── 01_extract_and_upload_to_gcs.py
│   └── 02_load_gcs_to_bigquery.py
└── netflix_dagster/             # Centralized Dagster folder workspace root
    ├── netflix_dagster/
    │   ├── __init__.py          # Exposes system definitions object
    │   ├── assets.py            # Custom subprocess, audit logger, & translator logic
    │   └── definitions.py       # Pipelines definitions deployment manifest
    ├── pipeline_logs/           # Storage directory for historical pipeline logs
    │   └── pipeline_status_YYYYMMDDHHMISS.log # Unique execution audit log file
    ├── run_netflix_dagster.sh   # Background CLI pipeline execution script
    └── pyproject.toml
```

---

## 1. Automated Status & Auditing Logs

Every pipeline execution automatically creates a standalone audit file located inside your `netflix_dagster/pipeline_logs/` subfolder using the format `pipeline_status_YYYYMMDDHHMISS.log` [INDEX] (where `YYYYMMDDHHMISS` represents the exact year, month, day, 24-hour, minute, and second the run started). It tracks task execution states, run times, step durations, and error identifiers.

To view your pipeline execution status metrics for a specific run, use this from your project root folder:
```bash
cat netflix_dagster/pipeline_logs/pipeline_status_*.log
```

### Log File Output Format:
```text
[2026-06-10 17:44:32] STEP: 01_extract_and_upload_to_gcs | STATUS: SUCCESS | START: 2026-06-10 17:44:15 | END: 2026-06-10 17:44:32 | DURATION: 17.00s
[2026-06-10 17:44:45] STEP: 02_load_gcs_to_bigquery | STATUS: SUCCESS | START: 2026-06-10 17:44:32 | END: 2026-06-10 17:44:45 | DURATION: 13.00s
[2026-06-10 17:45:49] STEP: 03_dbt_build | STATUS: SUCCESS | START: 2026-06-10 17:44:45 | END: 2026-06-10 17:45:49 | DURATION: 64.00s
```

---

## 2. Standard Execution via Web UI

1. Start the development server from the Dagster project folder:
   ```bash
   cd netflix_dagster
   dagster dev -m netflix_dagster
   ```
2. Open your browser and navigate to **`http://localhost:3000`**.
3. Click on the **Lineage** tab in the left sidebar menu to view your asset flow layout.
4. Click the **Materialize All** button in the top-right corner to run the sequence.

---

## 3. Background Execution via Shell Script (No UI)

When you want to run the pipeline programmatically in the background without launching or opening the Dagster Web UI, use the `run_netflix_dagster.sh` script located inside your `netflix_dagster/` subdirectory [INDEX].

This script automatically captures the name of your currently active Conda environment (defaulting to `dagster`), configures local application path variables, and triggers a headless asset materialization cycle.

### Step 3.1: Initialize Your Application Default Credentials (ADC)
Ensure your active terminal session has authorized local Python library access with project routing parameters by running this command once from the project root [INDEX]:
```bash
gcloud auth application-default login
```
Follow the screen prompts to authorize access via your web browser [INDEX].

### Step 3.2: Make the Script Executable
Ensure the shell script has the correct execution permissions assigned:
```bash
chmod +x netflix_dagster/run_netflix_dagster.sh
```

### Step 3.3: Run the Script in the Background
To kick off your end-to-end pipeline run completely hands-free from the terminal, execute it from the project directory:
```bash
cd netflix_dagster
./run_netflix_dagster.sh
```

This returns control to your terminal shell immediately. You can safely log out of your server session, and the data pipeline will continue running safely in the background.

### Step 3.4: Track Live Background Engine Logs
To stream the live step-by-step orchestrator execution logging output directly inside your terminal, run:
```bash
tail -f headless_execution.log
```
*Note: Because this command continuously monitors the log file, it will not exit on its own when the pipeline finishes. Press **`Ctrl + C`** on your keyboard at any time to disconnect from the log stream and return to your command prompt.*
