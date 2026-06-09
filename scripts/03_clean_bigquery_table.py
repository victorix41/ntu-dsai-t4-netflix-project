"""
Block 3.5: Clean the raw Netflix table in BigQuery and write to a cleaned table.

Official project flow for Block 3.5:

BigQuery raw table:
    ntu-dsai-t4-netflix.raw.netflix_titles

→ BigQuery cleaned table:
    ntu-dsai-t4-netflix.analytics.stg_netflix_titles

Cleaning rules applied in this script:
- 'director', 'cast', 'rating', 'duration':
      Empty/NULL values are filled with the word 'Unknown'.
- 'country':
      Empty/NULL values are filled with the word 'International'.
- 'date_added':
      Empty/NULL values are filled with 'January 01 <release_year>',
      then parsed into a proper DATE in MM-DD-YYYY format.

Important project rule:
This script belongs to the CLEANING layer between raw ingestion (Blocks 1-3)
and dbt modelling (Blocks 4-6).

That means:
- We read from raw.netflix_titles.
- We apply null-filling and date parsing.
- We write the result to analytics.stg_netflix_titles.
- We do NOT split genre/country, rename columns beyond cleaning, or model
  into fact/dimension tables here. That happens in dbt Blocks 4-6.

Why this script is heavily commented:
The team is still learning data engineering, so the code is written to be readable
and explainable, not short and clever.
"""

# os lets us read environment variables from the current Python process.
import os

# load_dotenv reads key-value pairs from our local .env file.
from dotenv import load_dotenv

# bigquery lets Python talk to Google BigQuery.
# We use it here to:
# 1. Run a cleaning SQL query that reads from raw.netflix_titles.
# 2. Write the cleaned result to analytics.stg_netflix_titles.
# 3. Verify the cleaned table after writing.
from google.cloud import bigquery


def load_project_config():
    """
    Load project configuration from the local .env file.

    Why use .env?
    We do not want to hardcode project IDs, dataset names, and table names
    all over the script. If a setting changes, we update .env, not the code.
    """

    # Load variables from .env into the Python process.
    load_dotenv()

    # Read required settings from .env.
    # Key names match the .env.example file exactly:
    #   GCP_PROJECT_ID, GCP_LOCATION, BQ_RAW_DATASET,
    #   BQ_RAW_TABLE, BQ_ANALYTICS_DATASET
    config = {
        "gcp_project_id": os.getenv("GCP_PROJECT_ID"),
        "gcp_location": os.getenv("GCP_LOCATION"),
        "bigquery_raw_dataset": os.getenv("BQ_RAW_DATASET"),
        "bigquery_raw_table": os.getenv("BQ_RAW_TABLE"),
        "bigquery_analytics_dataset": os.getenv("BQ_ANALYTICS_DATASET"),
        "bigquery_cleaned_table": os.getenv(
            "BQ_CLEANED_TABLE", "stg_netflix_titles"
        ),
    }

    # Find missing values early.
    # We skip bigquery_cleaned_table because it has a default above.
    required_keys = [
        "gcp_project_id",
        "gcp_location",
        "bigquery_raw_dataset",
        "bigquery_raw_table",
        "bigquery_analytics_dataset",
    ]

    missing_keys = []

    for key in required_keys:
        value = config.get(key)
        if value is None or value.strip() == "":
            missing_keys.append(key)

    if missing_keys:
        raise ValueError(
            "Missing required config values in .env: "
            + ", ".join(missing_keys)
            + "\n\nPlease check your .env file before running this script."
        )

    return config


def build_table_ids(config):
    """
    Build fully-qualified BigQuery table IDs for the source and destination tables.

    BigQuery table ID format:
        project_id.dataset_name.table_name

    Source (raw table):
        ntu-dsai-t4-netflix.raw.netflix_titles

    Destination (cleaned staging table):
        ntu-dsai-t4-netflix.analytics.stg_netflix_titles
    """

    raw_table_id = (
        f"{config['gcp_project_id']}."
        f"{config['bigquery_raw_dataset']}."
        f"{config['bigquery_raw_table']}"
    )

    cleaned_table_id = (
        f"{config['gcp_project_id']}."
        f"{config['bigquery_analytics_dataset']}."
        f"{config['bigquery_cleaned_table']}"
    )

    return raw_table_id, cleaned_table_id


def print_config_summary(config, raw_table_id, cleaned_table_id):
    """
    Print a summary of the source and destination configuration.

    This is a human sanity check before we run any BigQuery query.
    """

    print("\nBlock 3.5 configuration loaded successfully.")
    print(f"GCP project ID      : {config['gcp_project_id']}")
    print(f"GCP location        : {config['gcp_location']}")
    print(f"Source raw table    : {raw_table_id}")
    print(f"Destination table   : {cleaned_table_id}")
    print()


def create_bigquery_client(config):
    """
    Create a BigQuery client.

    The BigQuery client is the Python object that lets this script talk to BigQuery.
    It uses your local Google authentication from:

        gcloud auth application-default login

    This means we do not need to store service account JSON files in the repo.
    """

    print("Creating BigQuery client...")

    gcp_project_id = config["gcp_project_id"]

    # Create the BigQuery client for the project.
    client = bigquery.Client(project=gcp_project_id)

    print("BigQuery client created successfully.")
    print(f"Client project: {client.project}\n")

    return client


def check_analytics_dataset_exists(client, config):
    """
    Check that the target analytics dataset exists before writing the cleaned table.

    For this project, the analytics dataset should already exist:
        ntu-dsai-t4-netflix.analytics

    If it does not exist, we fail early with a clear message rather than
    letting the write step produce a confusing BigQuery error.
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


def build_cleaning_query(raw_table_id):
    """
    Build the BigQuery SQL query that cleans the raw Netflix table.

    Cleaning rules:
    ─────────────────────────────────────────────────────────────────────────
    Column        | Rule
    ─────────────────────────────────────────────────────────────────────────
    director      | NULL or empty → 'Unknown'
    cast          | NULL or empty → 'Unknown'
    rating        | NULL or empty → 'Unknown'
    duration      | NULL or empty → 'Unknown'
    country       | NULL or empty → 'International'
    date_added    | NULL or empty → 'January 01 <release_year>'
                  | Then parse the string into a DATE (MM-DD-YYYY format)
    ─────────────────────────────────────────────────────────────────────────

    Why NULLIF(TRIM(column), '')?
    The raw CSV sometimes loads blank strings as '' instead of NULL.
    TRIM removes accidental leading/trailing spaces.
    NULLIF converts a blank string '' to NULL so COALESCE can then fill it in.

    Why PARSE_DATE?
    The raw date_added column is a text string like 'September 25, 2021'.
    BigQuery's PARSE_DATE('%B %d, %Y', ...) converts it to a proper DATE value.
    We fill nulls first (creating 'January 01, <year>') before parsing,
    so every row ends up with a valid DATE.

    Why CONCAT for the fallback date?
    When date_added is NULL, we build a synthetic date string in the same
    format: 'January 01, <release_year>' — e.g. 'January 01, 2013'.
    CAST(release_year AS STRING) converts the INTEGER year to text first.
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
        --   Step 1: If date_added is NULL or blank, build a fallback string
        --           in 'Month DD, YYYY' format using January 01 + release_year.
        --   Step 2: Parse the resulting string into a proper DATE.
        --   Output format: DATE (stored as YYYY-MM-DD in BigQuery, displayed
        --           as MM-DD-YYYY in the project's query results).
        PARSE_DATE(
            '%B %d, %Y',
            COALESCE(
                NULLIF(TRIM(date_added), ''),
                CONCAT('January 01, ', CAST(release_year AS STRING))
            )
        ) AS date_added,

        release_year,

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
    Run the cleaning SQL query and write the result to the analytics cleaned table.

    Source:
        ntu-dsai-t4-netflix.raw.netflix_titles

    Destination:
        ntu-dsai-t4-netflix.analytics.stg_netflix_titles

    Write mode: WRITE_TRUNCATE
        This replaces the cleaned table each time the script runs.
        This keeps the pipeline repeatable: running the script again
        always produces the same clean output from the same raw input.
    """

    print("Running cleaning SQL query and writing cleaned table...")

    # Build the cleaning SQL query.
    cleaning_query = build_cleaning_query(raw_table_id)

    print("Cleaning SQL query:")
    print(cleaning_query)
    print()

    # Configure the BigQuery query job.
    #
    # destination:
    #   Where to write the query result.
    #
    # write_disposition=WRITE_TRUNCATE:
    #   Replace the destination table each time this runs.
    #
    # create_disposition=CREATE_IF_NEEDED:
    #   Create the destination table if it does not already exist.
    job_config = bigquery.QueryJobConfig(
        destination=cleaned_table_id,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )

    print(f"Source raw table    : {raw_table_id}")
    print(f"Destination table   : {cleaned_table_id}")
    print(f"Write mode          : WRITE_TRUNCATE (replace on each run)")
    print()

    # Submit the query job to BigQuery.
    query_job = client.query(
        query=cleaning_query,
        job_config=job_config,
        location=config["gcp_location"],
    )

    print(f"Started BigQuery query job: {query_job.job_id}")
    print("Waiting for cleaning job to complete...")

    # .result() waits until the job finishes.
    # If the job fails, this line raises an error.
    query_job.result()

    print("Cleaning job completed successfully.\n")

    # Fetch the destination table metadata to confirm the write succeeded.
    table = client.get_table(cleaned_table_id)

    print("Cleaned table written successfully.")
    print(f"Table ID     : {table.full_table_id}")
    print(f"Row count    : {table.num_rows:,}")
    print(f"Column count : {len(table.schema)}")
    print()

    return table


def verify_cleaned_table(client, cleaned_table_id):
    """
    Verify the cleaned BigQuery table after writing.

    We check:
    1. The table exists and has rows.
    2. No NULL values remain in the cleaned columns.
    3. All date_added values are valid (non-NULL after parsing).
    4. A sample of cleaned rows looks correct.

    This is not analysis. This is a post-cleaning quality check.
    """

    print("Verifying cleaned BigQuery table...")
    print()

    # ─── Check 1: table exists and row count ─────────────────────────────────
    table = client.get_table(cleaned_table_id)

    print(f"Table ID     : {table.full_table_id}")
    print(f"Row count    : {table.num_rows:,}")
    print()

    if table.num_rows == 0:
        raise ValueError(
            f"Cleaned table exists but has zero rows: {cleaned_table_id}"
        )

    # ─── Check 2: NULL counts in cleaned columns ──────────────────────────────
    # After cleaning, these columns should have zero NULLs.
    null_check_query = f"""
    SELECT
        COUNTIF(director    IS NULL) AS null_director,
        COUNTIF(cast        IS NULL) AS null_cast,
        COUNTIF(country     IS NULL) AS null_country,
        COUNTIF(date_added  IS NULL) AS null_date_added,
        COUNTIF(rating      IS NULL) AS null_rating,
        COUNTIF(duration    IS NULL) AS null_duration
    FROM `{cleaned_table_id}`
    """

    null_result = client.query(null_check_query).result()

    print("NULL check on cleaned columns (all should be 0):")

    for row in null_result:
        print(f"  null_director   : {row.null_director}")
        print(f"  null_cast       : {row.null_cast}")
        print(f"  null_country    : {row.null_country}")
        print(f"  null_date_added : {row.null_date_added}")
        print(f"  null_rating     : {row.null_rating}")
        print(f"  null_duration   : {row.null_duration}")

        # If any column still has NULLs, warn the team.
        total_nulls = (
            row.null_director
            + row.null_cast
            + row.null_country
            + row.null_date_added
            + row.null_rating
            + row.null_duration
        )

        if total_nulls > 0:
            print(
                f"\nWARNING: {total_nulls} NULL value(s) remain in cleaned columns."
                " Please investigate before proceeding to dbt modelling.\n"
            )
        else:
            print("\nAll cleaned columns have zero NULLs. Cleaning verified.\n")

    # ─── Check 3: 'Unknown' fill verification ────────────────────────────────
    # Count how many rows received the fallback fill values so the team
    # can see the extent of the original raw nulls.
    fill_count_query = f"""
    SELECT
        COUNTIF(director = 'Unknown')      AS filled_director,
        COUNTIF(cast     = 'Unknown')      AS filled_cast,
        COUNTIF(country  = 'International') AS filled_country,
        COUNTIF(rating   = 'Unknown')      AS filled_rating,
        COUNTIF(duration = 'Unknown')      AS filled_duration
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

    # ─── Check 4: Sample rows ────────────────────────────────────────────────
    # Show 10 sample rows so the team can visually inspect the cleaned data.
    # This is the kind of quick check the guide refers to on pages 23-24:
    # querying stg_netflix_titles to confirm the cleaning looks correct.
    sample_query = f"""
    SELECT
        show_id,
        type,
        title,
        director,
        cast,
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

    print("Sample rows from cleaned table (date_added shown as MM-DD-YYYY):")
    print()

    # Print a header row.
    print(
        f"{'show_id':<8} {'type':<10} {'title':<35} {'director':<25}"
        f" {'country':<20} {'date_added':<15} {'release_year':<13}"
        f" {'rating':<10} {'duration'}"
    )
    print("-" * 160)

    for row in sample_rows:
        # Truncate long fields for readability in the terminal.
        title_display = row.title[:33] if len(row.title) > 33 else row.title
        director_display = (
            row.director[:23] if len(row.director) > 23 else row.director
        )
        country_display = (
            row.country[:18] if len(row.country) > 18 else row.country
        )

        print(
            f"{row.show_id:<8} {row.type:<10} {title_display:<35}"
            f" {director_display:<25} {country_display:<20}"
            f" {row.date_added:<15} {row.release_year:<13}"
            f" {row.rating:<10} {row.duration}"
        )

    print()

    # ─── Check 5: Verify date_added fallback rows ─────────────────────────────
    # Show a few rows where the original date_added was NULL and was filled
    # with 'January 01 <release_year>' to confirm the logic worked correctly.
    fallback_date_query = f"""
    SELECT
        show_id,
        title,
        release_year,
        FORMAT_DATE('%m-%d-%Y', date_added) AS date_added
    FROM `{cleaned_table_id}`
    WHERE
        EXTRACT(MONTH FROM date_added) = 1
        AND EXTRACT(DAY FROM date_added) = 1
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
        title_display = row.title[:33] if len(row.title) > 33 else row.title
        print(
            f"{row.show_id:<10} {title_display:<35}"
            f" {row.release_year:<15} {row.date_added}"
        )
        count += 1

    if count == 0:
        print("  (no rows found with January 01 date — fallback may not have been needed)")

    print()
    print("Cleaned table verification complete.")
    print()


def main():
    """
    Main function for Block 3.5: BigQuery data cleaning.

    Sections:
    1. Load project config from .env.
    2. Build raw and cleaned table IDs.
    3. Print configuration summary.
    4. Create BigQuery client.
    5. Check analytics dataset exists.
    6. Run cleaning SQL and write to analytics.stg_netflix_titles.
    7. Verify cleaned table (null counts, fill counts, sample rows).
    """

    # Section 1: Load config from .env.
    config = load_project_config()

    # Section 2: Build source and destination table IDs.
    raw_table_id, cleaned_table_id = build_table_ids(config)

    # Section 3: Print config summary for sanity checking.
    print_config_summary(
        config=config,
        raw_table_id=raw_table_id,
        cleaned_table_id=cleaned_table_id,
    )

    # Section 4: Create BigQuery client.
    client = create_bigquery_client(config)

    # Section 5: Check the analytics dataset exists.
    check_analytics_dataset_exists(
        client=client,
        config=config,
    )

    # Section 6: Run cleaning SQL and write cleaned table.
    run_cleaning_and_write(
        client=client,
        config=config,
        raw_table_id=raw_table_id,
        cleaned_table_id=cleaned_table_id,
    )

    # Section 7: Verify the cleaned table.
    verify_cleaned_table(
        client=client,
        cleaned_table_id=cleaned_table_id,
    )

    print(
        "Block 3.5 complete. "
        f"Cleaned table is ready at: {cleaned_table_id}"
    )


# Only run main() when this file is executed directly.
if __name__ == "__main__":
    main()
