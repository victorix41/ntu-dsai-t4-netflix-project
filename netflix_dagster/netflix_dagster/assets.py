import subprocess
import os
from datetime import datetime
from dagster import asset, AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets, DagsterDbtTranslator
from .project import dbt_netflix_project

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
SCRIPT_DIR = os.path.join(REPO_ROOT, "scripts")
LOG_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../pipeline_logs"))

def write_audit_log_pure(step_name: str, start_time: datetime, status: str, details: str = ""):
    """Appends execution metrics directly into a daily log file using pure Python."""
    os.makedirs(LOG_DIR, exist_ok=True)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Creates a unique log file name based on the exact start time of this step run
    date_str = start_time.strftime("%Y%m%d%H%M%S")
    log_file_path = os.path.join(LOG_DIR, f"pipeline_status_{date_str}.log")
    
    log_line = (
        f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] STEP: {step_name} | STATUS: {status} | "
        f"START: {start_time.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"END: {end_time.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"DURATION: {duration:.2f}s"
    )
    if details:
        log_line += f" | {details}"
    log_line += "\n"
    
    with open(log_file_path, "a") as f:
        f.write(log_line)

@asset(compute_kind="python")
def extract_and_upload_to_gcs():
    """Step 1: Execute extraction and upload script with explicit user credentials mapping."""
    script_path = os.path.join(SCRIPT_DIR, "01_extract_and_upload_to_gcs.py")
    start_time = datetime.now()
    
    # Clone the environment and explicitly point to your local user login file
    env_context = os.environ.copy()
    env_context["GOOGLE_APPLICATION_CREDENTIALS"] = "$HOME/.config/ntu-dsai/ntu-dsai-netflix-runner-key.json"
    
    result = subprocess.run(["python", script_path], env=env_context, capture_output=True, text=True, cwd=REPO_ROOT)
    
    if result.returncode == 0:
        write_audit_log_pure("01_extract_and_upload_to_gcs", start_time, "SUCCESS")
    else:
        cleaned_err = result.stderr.replace('\n', ' ').strip()
        write_audit_log_pure(
            "01_extract_and_upload_to_gcs", 
            start_time, 
            "FAILED", 
            f"ERROR: {cleaned_err[:300]}"
        )
        raise Exception(f"Script failed with exit code {result.returncode}")

@asset(compute_kind="python")
def load_gcs_to_bigquery(extract_and_upload_to_gcs):
    """Step 2: Execute BigQuery load script with explicit user credentials mapping."""
    script_path = os.path.join(SCRIPT_DIR, "02_load_gcs_to_bigquery.py")
    start_time = datetime.now()
    
    env_context = os.environ.copy()
    env_context["GOOGLE_APPLICATION_CREDENTIALS"] = "$HOME/.config/ntu-dsai/ntu-dsai-netflix-runner-key.json"
    
    result = subprocess.run(["python", script_path], env=env_context, capture_output=True, text=True, cwd=REPO_ROOT)
    
    if result.returncode == 0:
        write_audit_log_pure("02_load_gcs_to_bigquery", start_time, "SUCCESS")
    else:
        cleaned_err = result.stderr.replace('\n', ' ').strip()
        write_audit_log_pure(
            "02_load_gcs_to_bigquery", 
            start_time, 
            "FAILED", 
            f"ERROR: {cleaned_err[:300]}"
        )
        raise Exception(f"Script failed with exit code {result.returncode}")

class CustomDagsterDbtTranslator(DagsterDbtTranslator):
    def get_asset_key(self, dbt_resource_props):
        from dagster import AssetKey
        resource_type = dbt_resource_props["resource_type"]
        if resource_type == "source" and dbt_resource_props["source_name"] == "raw":
            return AssetKey("load_gcs_to_bigquery")
        return super().get_asset_key(dbt_resource_props)

@dbt_assets(
    manifest=dbt_netflix_project.manifest_path,
    dagster_dbt_translator=CustomDagsterDbtTranslator()
)
def dbt_netflix_dsp_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """Step 3: Execute dbt transformations sequentially."""
    start_time = datetime.now()
    dbt_log_path = os.path.join(dbt.project_dir, "logs", "dbt.log")
    
    try:
        yield from dbt.cli(["build"], context=context).stream()
        write_audit_log_pure("03_dbt_build", start_time, "SUCCESS")
    except Exception as e:
        write_audit_log_pure(
            "03_dbt_build", 
            start_time, 
            "FAILED", 
            f"TROUBLESHOOT PATH: Check compiled dbt execution logs at {dbt_log_path}"
        )
        raise e
