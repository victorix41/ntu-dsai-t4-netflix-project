"""
Block 3.5 + Blocks 4-6: Data cleaning and dbt transformation.
 
This script combines two stages into one run:
 
  Stage 1 — Data Cleaning (Block 3.5)
  ─────────────────────────────────────────────────────────────────────────
  Reads from raw.netflix_titles in BigQuery, applies cleaning rules, and
  writes the result to analytics.stg_netflix_titles.
 
  Cleaning rules:
  - director, cast, rating, duration : NULL / blank → 'Unknown'
  - country                          : NULL / blank → 'International'
  - date_added                       : NULL / blank → 'January 01, <release_year>'
                                       then parsed to a proper DATE value.
  - release_year                     : cast to INT64
 
  Stage 2 — dbt Transformation (Blocks 4-6)
  ─────────────────────────────────────────────────────────────────────────
  Runs dbt programmatically using Python subprocess so the dbt models
  execute inside the same pipeline without the team needing to type
  dbt run / dbt test manually.
 
  dbt staging model (Block 4):
      analytics.stg_netflix_titles   (rebuilt by dbt from raw, same cleaning)
 
  dbt mart models (Blocks 5-6):
      analytics.fact_showlist
      analytics.dim_agerating
      analytics.dim_showcountry
      analytics.dim_showgenre
      analytics.dim_showtitle
 
  dbt tests (Block 6):
      Runs dbt test after dbt run to verify unique/not_null/accepted_values
      constraints defined in schema.yml.
 
Official project flow:
 
  raw.netflix_titles
      → [Stage 1: Python cleaning]
      → analytics.stg_netflix_titles   (verified here)
      → [Stage 2: dbt run]
      → analytics.fact_showlist
      → analytics.dim_agerating
      → analytics.dim_showcountry
      → analytics.dim_showgenre
      → analytics.dim_showtitle
      → [dbt test]
 
Why this script is heavily commented:
The team is still learning data engineering, so the code is written to be
readable and explainable, not short and clever.
"""
 
# os lets us read environment variables from the current Python process.
import os
 
# subprocess lets Python run shell commands such as 'dbt run' and 'dbt test'.
import subprocess
 
# sys lets us exit early with a non-zero code if something fails.
import sys
 
# load_dotenv reads key-value pairs from our local .env file.
from dotenv import load_dotenv
 
# bigquery lets Python talk to Google BigQuery.
from google.cloud import bigquery
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────
 
def load_project_config():
    """
    Load project configuration from the local .env file.
 
    Why use .env?
    We do not want to hardcode project IDs, dataset names, and table names
    all over the script. If a setting changes, we update .env, not the code.
 
    Expected .env keys:
        GCP_PROJECT_ID        e.g. ntu-dsai-t4-netflix
        GCP_LOCATION          e.g. US
        BQ_RAW_DATASET        e.g. raw
        BQ_RAW_TABLE          e.g. netflix_titles
        BQ_ANALYTICS_DATASET  e.g. analytics
        DBT_PROJECT_DIR       e.g. /home/user/ntu-dsai-t4-netflix-project/dbt_netflix
        DBT_PROFILES_DIR      e.g. /home/user/.dbt   (optional, defaults to ~/.dbt)
    """
 
    load_dotenv()
 
    config = {
        "gcp_project_id":             os.getenv("GCP_PROJECT_ID"),
        "gcp_location":               os.getenv("GCP_LOCATION"),
        "bigquery_raw_dataset":       os.getenv("BQ_RAW_DATASET"),
        "bigquery_raw_table":         os.getenv("BQ_RAW_TABLE"),
        "bigquery_analytics_dataset": os.getenv("BQ_ANALYTICS_DATASET"),
        # Default cleaned table name matches the project naming contract.
        "bigquery_cleaned_table":     os.getenv("BQ_CLEANED_TABLE", "stg_netflix_titles"),
        # DBT_PROJECT_DIR must point to the dbt_netflix/ folder in the repo.
        "dbt_project_dir":            os.getenv("DBT_PROJECT_DIR"),
        # DBT_PROFILES_DIR defaults to ~/.dbt if not set.
        "dbt_profiles_dir":           os.getenv(
            "DBT_PROFILES_DIR", os.path.expanduser("~/.dbt")),
    }
 
    required_keys = [
        "gcp_project_id",
        "gcp_location",
        "bigquery_raw_dataset",
        "bigquery_raw_table",
        "bigquery_analytics_dataset",
        "dbt_project_dir",
    ]
 
    missing_keys = [k for k in required_keys if not (config.get(k) or "").strip()]
 
    if missing_keys:
        raise ValueError(
            "Missing required config values in .env: "
            + ", ".join(missing_keys)
            + "\n\nPlease check your .env file before running this script."
            + "\n\nMake sure DBT_PROJECT_DIR is set to the full path of your "
            "dbt_netflix/ folder, e.g.:\n"
            "  DBT_PROJECT_DIR=/home/user/ntu-dsai-t4-netflix-project/dbt_netflix"
        )
 
    # Confirm the dbt project directory actually exists on disk.
    dbt_dir = config["dbt_project_dir"]
    if not os.path.isdir(dbt_dir):
        raise ValueError(
            f"DBT_PROJECT_DIR does not exist on disk: {dbt_dir}\n\n"
            "Please set DBT_PROJECT_DIR in your .env to the full path of the "
            "dbt_netflix/ folder."
        )
 
    return config
 
 
def build_table_ids(config):
    """
    Build fully-qualified BigQuery table IDs for the source and staging tables.
 
    BigQuery table ID format:
        project_id.dataset_name.table_name
    """
 
    proj    = config["gcp_project_id"]
    raw_ds  = config["bigquery_raw_dataset"]
    anal_ds = config["bigquery_analytics_dataset"]
 
    raw_table_id     = f"{proj}.{raw_ds}.{config['bigquery_raw_table']}"
    cleaned_table_id = f"{proj}.{anal_ds}.{config['bigquery_cleaned_table']}"
 
    return raw_table_id, cleaned_table_id
 
 
def print_config_summary(config, raw_table_id, cleaned_table_id):
    """Print a human-readable summary of what this run will read and write."""
 
    print("\nBlock 3.5 + Blocks 4-6 configuration loaded successfully.")
    print(f"GCP project ID      : {config['gcp_project_id']}")
    print(f"GCP location        : {config['gcp_location']}")
    print(f"Source raw table    : {raw_table_id}")
    print(f"Staging table       : {cleaned_table_id}")
    print(f"dbt project dir     : {config['dbt_project_dir']}")
    print(f"dbt profiles dir    : {config['dbt_profiles_dir']}")
    print()
 
 
def create_bigquery_client(config):
    """
    Create a BigQuery client using local Google application-default credentials.
 
    Run once before this script if not already authenticated:
        gcloud auth application-default login
    """
 
    print("Creating BigQuery client...")
    client = bigquery.Client(project=config["gcp_project_id"])
    print("BigQuery client created successfully.")
    print(f"Client project: {client.project}\n")
    return client
 
 
def check_analytics_dataset_exists(client, config):
    """
    Confirm the analytics dataset exists before any write operation.
    Fail early with a clear message if it is missing.
    """
 
    print("Checking analytics dataset exists...")
 
    dataset_id = (
        f"{config['gcp_project_id']}."
        f"{config['bigquery_analytics_dataset']}"
    )
 
    try:
        dataset = client.get_dataset(dataset_id)
    except Exception as error:
        raise RuntimeError(
            "BigQuery analytics dataset check failed.\n\n"
            f"Expected dataset: {dataset_id}\n\n"
            "Please confirm the analytics dataset exists in BigQuery.\n\n"
            f"Original error:\n{error}"
        )
 
    print("Analytics dataset exists.")
    print(f"Dataset ID : {dataset.full_dataset_id}")
    print(f"Location   : {dataset.location}\n")
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Data Cleaning (Block 3.5)
# ─────────────────────────────────────────────────────────────────────────────
 
def build_cleaning_query(raw_table_id):
    """
    Build the BigQuery SQL that cleans the raw Netflix table.
 
    Cleaning rules
    ──────────────────────────────────────────────────────────────────────
    Column        Rule
    ──────────────────────────────────────────────────────────────────────
    director      NULL or empty → 'Unknown'
    cast          NULL or empty → 'Unknown'
    rating        NULL or empty → 'Unknown'
    duration      NULL or empty → 'Unknown'
    country       NULL or empty → 'International'
    date_added    NULL or empty → synthetic 'January 01, <release_year>'
                  Then parse into a proper DATE value.
    release_year  cast to INT64
    ──────────────────────────────────────────────────────────────────────
 
    Why NULLIF(TRIM(column), '')?
    The raw CSV sometimes loads blank strings as '' instead of NULL.
    TRIM removes accidental leading/trailing spaces.
    NULLIF converts '' to NULL so COALESCE can then fill it.
 
    Why PARSE_DATE?
    The raw date_added column is a text string like 'September 25, 2021'.
    PARSE_DATE('%B %d, %Y', ...) converts it to a proper DATE value.
    """
 
    query = f"""
    SELECT
        show_id,
        type,
        title,
 
        -- director: fill NULLs and blank strings with 'Unknown'
        COALESCE(NULLIF(TRIM(director), ''), 'Unknown') AS director,
 
        -- cast: fill NULLs and blank strings with 'Unknown'
        COALESCE(NULLIF(TRIM(cast), ''), 'Unknown') AS cast,
 
        -- country: fill NULLs and blank strings with 'International'
        COALESCE(NULLIF(TRIM(country), ''), 'International') AS country,
 
        -- date_added:
        --   Step 1: If NULL or blank, build 'January 01, <release_year>'.
        --   Step 2: Parse the string into a proper DATE value.
        PARSE_DATE(
            '%B %d, %Y',
            COALESCE(
                NULLIF(TRIM(date_added), ''),
                CONCAT('January 01, ', CAST(release_year AS STRING))
            )
        ) AS date_added,
 
        -- release_year: cast to INT64 so fact_showlist can store it as INT64.
        -- The raw table often loads numeric columns as STRING via autodetect.
        SAFE_CAST(release_year AS INT64) AS release_year,
 
        -- rating: fill NULLs and blank strings with 'Unknown'
        COALESCE(NULLIF(TRIM(rating), ''), 'Unknown') AS rating,
 
        -- duration: fill NULLs and blank strings with 'Unknown'
        COALESCE(NULLIF(TRIM(duration), ''), 'Unknown') AS duration,
 
        listed_in,
        description
 
    FROM `{raw_table_id}`
    """
 
    return query
 
 
def run_cleaning_and_write(client, config, raw_table_id, cleaned_table_id):
    """
    Run the cleaning SQL query and write the result to analytics.stg_netflix_titles.
 
    Write mode WRITE_TRUNCATE replaces the table on every run, keeping the
    pipeline fully repeatable.
    """
 
    print("=" * 60)
    print("STAGE 1: Data Cleaning (Block 3.5)")
    print("=" * 60)
    print()
    print("Running cleaning SQL query and writing staging table...")
 
    cleaning_query = build_cleaning_query(raw_table_id)
 
    print("Cleaning SQL query:")
    print(cleaning_query)
    print()
 
    job_config = bigquery.QueryJobConfig(
        destination=cleaned_table_id,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )
 
    print(f"Source raw table    : {raw_table_id}")
    print(f"Destination table   : {cleaned_table_id}")
    print(f"Write mode          : WRITE_TRUNCATE (replace on each run)\n")
 
    query_job = client.query(
        query=cleaning_query,
        job_config=job_config,
        location=config["gcp_location"],
    )
 
    print(f"Started BigQuery query job: {query_job.job_id}")
    print("Waiting for cleaning job to complete...")
    query_job.result()
    print("Cleaning job completed successfully.\n")
 
    table = client.get_table(cleaned_table_id)
    print("Staging table written successfully.")
    print(f"Table ID     : {table.full_table_id}")
    print(f"Row count    : {table.num_rows:,}")
    print(f"Column count : {len(table.schema)}\n")
 
    return table
 
 
def verify_cleaned_table(client, cleaned_table_id):
    """
    Verify the staging table after writing.
 
    Checks:
    1. Table exists and has rows.
    2. No NULLs remain in cleaned columns.
    3. Fill-value counts (how many rows received 'Unknown' / 'International').
    4. A sample of 10 cleaned rows.
    5. Sample of rows where date_added fell back to January 01 <release_year>.
    """
 
    print("Verifying cleaned staging table...")
    print()
 
    # Check 1: row count
    table = client.get_table(cleaned_table_id)
    print(f"Table ID     : {table.full_table_id}")
    print(f"Row count    : {table.num_rows:,}\n")
 
    if table.num_rows == 0:
        raise ValueError(
            f"Cleaned table exists but has zero rows: {cleaned_table_id}"
        )
 
    # Check 2: NULL counts in cleaned columns
    null_check_query = f"""
    SELECT
        COUNTIF(director     IS NULL) AS null_director,
        COUNTIF(cast         IS NULL) AS null_cast,
        COUNTIF(country      IS NULL) AS null_country,
        COUNTIF(date_added   IS NULL) AS null_date_added,
        COUNTIF(rating       IS NULL) AS null_rating,
        COUNTIF(duration     IS NULL) AS null_duration,
        COUNTIF(release_year IS NULL) AS null_release_year
    FROM `{cleaned_table_id}`
    """
 
    null_result = client.query(null_check_query).result()
 
    print("NULL check on cleaned columns (all should be 0):")
 
    for row in null_result:
        print(f"  null_director    : {row.null_director}")
        print(f"  null_cast        : {row.null_cast}")
        print(f"  null_country     : {row.null_country}")
        print(f"  null_date_added  : {row.null_date_added}")
        print(f"  null_rating      : {row.null_rating}")
        print(f"  null_duration    : {row.null_duration}")
        print(f"  null_release_year: {row.null_release_year}")
 
        total_nulls = (
            row.null_director + row.null_cast + row.null_country
            + row.null_date_added + row.null_rating + row.null_duration
            + row.null_release_year
        )
 
        if total_nulls > 0:
            print(
                f"\nWARNING: {total_nulls} NULL value(s) remain in cleaned "
                "columns. Please investigate before proceeding to dbt.\n"
            )
        else:
            print("\nAll cleaned columns have zero NULLs. Cleaning verified.\n")
 
    # Check 3: fill-value counts
    fill_count_query = f"""
    SELECT
        COUNTIF(director = 'Unknown')       AS filled_director,
        COUNTIF(cast     = 'Unknown')       AS filled_cast,
        COUNTIF(country  = 'International') AS filled_country,
        COUNTIF(rating   = 'Unknown')       AS filled_rating,
        COUNTIF(duration = 'Unknown')       AS filled_duration
    FROM `{cleaned_table_id}`
    """
 
    fill_result = client.query(fill_count_query).result()
 
    print("Fill-value counts (rows that received fallback fill):")
 
    for row in fill_result:
        print(f"  director filled with 'Unknown'        : {row.filled_director}")
        print(f"  cast filled with 'Unknown'            : {row.filled_cast}")
        print(f"  country filled with 'International'   : {row.filled_country}")
        print(f"  rating filled with 'Unknown'          : {row.filled_rating}")
        print(f"  duration filled with 'Unknown'        : {row.filled_duration}")
 
    print()
 
    # Check 4: 10 sample rows
    sample_query = f"""
    SELECT
        show_id,
        type,
        title,
        director,
        country,
        FORMAT_DATE('%m-%d-%Y', date_added) AS date_added,
        release_year,
        rating,
        duration
    FROM `{cleaned_table_id}`
    ORDER BY show_id
    LIMIT 10
    """
 
    sample_rows = client.query(sample_query).result()
 
    print("Sample rows from cleaned staging table (date_added shown as MM-DD-YYYY):")
    print()
    print(
        f"{'show_id':<8} {'type':<10} {'title':<35} {'director':<25}"
        f" {'country':<20} {'date_added':<15} {'release_year':<13}"
        f" {'rating':<10} {'duration'}"
    )
    print("-" * 160)
 
    for row in sample_rows:
        title_d    = row.title[:33]    if len(row.title)    > 33 else row.title
        director_d = row.director[:23] if len(row.director) > 23 else row.director
        country_d  = row.country[:18]  if len(row.country)  > 18 else row.country
 
        print(
            f"{row.show_id:<8} {row.type:<10} {title_d:<35}"
            f" {director_d:<25} {country_d:<20}"
            f" {row.date_added:<15} {row.release_year:<13}"
            f" {row.rating:<10} {row.duration}"
        )
 
    print()
 
    # Check 5: fallback date rows
    fallback_date_query = f"""
    SELECT
        show_id,
        title,
        release_year,
        FORMAT_DATE('%m-%d-%Y', date_added) AS date_added
    FROM `{cleaned_table_id}`
    WHERE EXTRACT(MONTH FROM date_added) = 1
      AND EXTRACT(DAY   FROM date_added) = 1
    LIMIT 10
    """
 
    fallback_rows = client.query(fallback_date_query).result()
 
    print(
        "Rows where date_added was filled with 'January 01 <release_year>' "
        "(sample, up to 10):"
    )
    print()
    print(f"{'show_id':<10} {'title':<35} {'release_year':<15} {'date_added'}")
    print("-" * 75)
 
    count = 0
    for row in fallback_rows:
        title_d = row.title[:33] if len(row.title) > 33 else row.title
        print(
            f"{row.show_id:<10} {title_d:<35}"
            f" {row.release_year:<15} {row.date_added}"
        )
        count += 1
 
    if count == 0:
        print(
            "  (no rows found with January 01 date — "
            "fallback may not have been needed)"
        )
 
    print()
    print("Cleaned staging table verification complete.\n")
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — dbt Transformation (Blocks 4-6)
# ─────────────────────────────────────────────────────────────────────────────
 
def run_dbt_command(command_args, config, label):
    """
    Run a dbt command as a subprocess and stream its output to the terminal.
 
    Why subprocess?
    dbt is a command-line tool. The cleanest way to run it from Python is
    to call it as a subprocess, the same way you would type it in the terminal.
    This keeps the dbt project self-contained and avoids importing dbt internals.
 
    Parameters
    ──────────────────────────────────────────────────────────────────────
    command_args  list of strings, e.g. ['dbt', 'run'] or ['dbt', 'test']
    config        project config dict (used for dbt project/profiles dirs)
    label         human-readable label printed in the output
    ──────────────────────────────────────────────────────────────────────
 
    The function raises RuntimeError if the dbt command exits with a
    non-zero return code, which stops the pipeline early with a clear message.
    """
 
    dbt_project_dir  = config["dbt_project_dir"]
    dbt_profiles_dir = config["dbt_profiles_dir"]
 
    # Build the full command with project and profiles directories.
    # --project-dir  tells dbt where dbt_project.yml lives.
    # --profiles-dir tells dbt where profiles.yml lives (BigQuery credentials).
    full_command = command_args + [
        "--project-dir",  dbt_project_dir,
        "--profiles-dir", dbt_profiles_dir,
    ]
 
    print(f"Running: {' '.join(full_command)}")
    print()
 
    # subprocess.run executes the command and streams output in real time.
    # check=False lets us handle the return code ourselves for a cleaner message.
    result = subprocess.run(
        full_command,
        cwd=dbt_project_dir,
        text=True,
    )
 
    if result.returncode != 0:
        raise RuntimeError(
            f"\n{label} failed with exit code {result.returncode}.\n\n"
            "Please review the dbt output above for error details.\n"
            "Common causes:\n"
            "  - profiles.yml not configured correctly for BigQuery\n"
            "  - dbt model SQL contains an error\n"
            "  - BigQuery table or dataset does not exist\n"
            "  - dbt test found a data quality failure\n"
        )
 
    print(f"\n{label} completed successfully.\n")
 
 
def run_dbt_pipeline(config):
    """
    Run the full dbt pipeline: dbt run followed by dbt test.
 
    dbt run  — compiles and executes all models in dbt_netflix/models/:
               staging/stg_netflix_titles.sql  (Block 4)
               marts/fact_showlist.sql          (Block 6)
               marts/dim_agerating.sql          (Block 6)
               marts/dim_showcountry.sql        (Block 5)
               marts/dim_showgenre.sql          (Block 5)
               marts/dim_showtitle.sql          (Block 6)
 
    dbt test — runs all tests defined in schema.yml:
               unique, not_null, accepted_values checks on all models.
 
    dbt handles model dependency order automatically:
    stg_netflix_titles runs first because the mart models reference it
    via {{ ref('stg_netflix_titles') }}.
    """
 
    print("=" * 60)
    print("STAGE 2: dbt Transformation (Blocks 4-6)")
    print("=" * 60)
    print()
 
    # ── dbt run ──────────────────────────────────────────────────────────────
    print("Step 2a: Running dbt models (dbt run)...")
    print()
    print("Models that will be built:")
    print("  staging/stg_netflix_titles   (Block 4 — clean base model)")
    print("  marts/fact_showlist          (Block 6 — fact table)")
    print("  marts/dim_agerating          (Block 6 — age rating dimension)")
    print("  marts/dim_showcountry        (Block 5 — country bridge/dimension)")
    print("  marts/dim_showgenre          (Block 5 — genre bridge/dimension)")
    print("  marts/dim_showtitle          (Block 6 — title dimension)")
    print()
 
    run_dbt_command(
        command_args=["dbt", "run"],
        config=config,
        label="dbt run",
    )
 
    # ── dbt test ─────────────────────────────────────────────────────────────
    print("Step 2b: Running dbt tests (dbt test)...")
    print()
    print("Tests that will run (defined in schema.yml):")
    print("  unique + not_null on primary key columns")
    print("  not_null on required columns")
    print("  accepted_values on type (Movie / TV Show)")
    print()
 
    run_dbt_command(
        command_args=["dbt", "test"],
        config=config,
        label="dbt test",
    )
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────────────────────
 
def print_final_summary(config, raw_table_id, cleaned_table_id):
    """
    Print a final summary of all tables written by this pipeline run.
    """
 
    proj    = config["gcp_project_id"]
    anal_ds = config["bigquery_analytics_dataset"]
 
    print("=" * 60)
    print("Pipeline complete. Tables available in BigQuery:")
    print("=" * 60)
    print()
    print("  Stage 1 — Cleaned staging table:")
    print(f"    {cleaned_table_id}")
    print()
    print("  Stage 2 — dbt mart tables:")
    print(f"    {proj}.{anal_ds}.fact_showlist")
    print(f"    {proj}.{anal_ds}.dim_agerating")
    print(f"    {proj}.{anal_ds}.dim_showcountry")
    print(f"    {proj}.{anal_ds}.dim_showgenre")
    print(f"    {proj}.{anal_ds}.dim_showtitle")
    print()
    print("Next steps:")
    print("  Block 7 — Query the mart tables in your analysis notebook.")
    print("  Block 8 — Build the Streamlit dashboard using the mart tables.")
    print()
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
 
def main():
    """
    Main function: runs Stage 1 (cleaning) then Stage 2 (dbt).
 
    Sections:
    1.  Load project config from .env.
    2.  Build raw and staging table IDs.
    3.  Print configuration summary.
    4.  Create BigQuery client.
    5.  Check analytics dataset exists.
    6.  Stage 1: Run cleaning SQL → write analytics.stg_netflix_titles.
    7.  Stage 1: Verify cleaned staging table.
    8.  Stage 2: Run dbt run → build all mart models.
    9.  Stage 2: Run dbt test → verify data quality.
    10. Print final summary.
    """
 
    # ── Section 1: Config ────────────────────────────────────────────────────
    config = load_project_config()
 
    # ── Section 2: Table IDs ─────────────────────────────────────────────────
    raw_table_id, cleaned_table_id = build_table_ids(config)
 
    # ── Section 3: Config summary ────────────────────────────────────────────
    print_config_summary(config, raw_table_id, cleaned_table_id)
 
    # ── Section 4: BigQuery client ───────────────────────────────────────────
    client = create_bigquery_client(config)
 
    # ── Section 5: Dataset check ─────────────────────────────────────────────
    check_analytics_dataset_exists(client=client, config=config)
 
    # ── Section 6: Stage 1 — cleaning ───────────────────────────────────────
    run_cleaning_and_write(
        client=client,
        config=config,
        raw_table_id=raw_table_id,
        cleaned_table_id=cleaned_table_id,
    )
 
    # ── Section 7: Stage 1 — verify staging table ────────────────────────────
    verify_cleaned_table(client=client, cleaned_table_id=cleaned_table_id)
 
    # ── Section 8-9: Stage 2 — dbt run + dbt test ───────────────────────────
    run_dbt_pipeline(config=config)
 
    # ── Section 10: Final summary ────────────────────────────────────────────
    print_final_summary(
        config=config,
        raw_table_id=raw_table_id,
        cleaned_table_id=cleaned_table_id,
    )
 
 
# Only run main() when this file is executed directly.
if __name__ == "__main__":
    main()