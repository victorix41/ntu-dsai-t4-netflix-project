#!/bin/bash

# 1. Finds the folder where this script lives (netflix_dagster/)
SCRIPT_DIR_PATH="$( cd "$( dirname "${BASH_SOURCE}" )" && pwd )"

# 2. Dynamically steps up 1 level to find the true repo root directory
REPO_ROOT="$(cd "${SCRIPT_DIR_PATH}/.." && pwd)"

# 3. Automatically capture the name of your currently active Conda environment
ACTIVE_ENV="${CONDA_DEFAULT_ENV:-dagster}"

# 4. Initialize Conda environment settings dynamically
source ~/miniconda3/etc/profile.d/conda.sh
conda activate "${ACTIVE_ENV}"

# 5. Ignore any manually exported service-account key and use ADC from `gcloud auth application-default login`.
unset GOOGLE_APPLICATION_CREDENTIALS

# 6. Step directly into the script's directory folder to launch materialization
cd "${SCRIPT_DIR_PATH}"

# 7. Execute asset sequence specifying the correct definition working directory
dagster asset materialize --select "*" -m netflix_dagster -d "${SCRIPT_DIR_PATH}" > headless_execution.log 2>&1 &

echo "Dagster pipeline sequence triggered successfully in background using environment [${ACTIVE_ENV}]!"
echo "Track live step updates by running: tail -f ${SCRIPT_DIR_PATH}/pipeline_logs/pipeline_status_*.log"
echo "Track raw Dagster engine logs by running: tail -f headless_execution.log"