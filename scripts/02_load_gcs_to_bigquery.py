"""
Block 3: Load raw Netflix CSV from Google Cloud Storage into BigQuery.

Official project flow for Block 3:

GCS raw CSV:
    gs://ntu-dsai-t4-netflix-raw-001/raw/netflix_titles.csv

→ BigQuery raw table:
    ntu-dsai-t4-netflix.raw.netflix_titles

Important project rule:
This script belongs to the RAW ingestion layer.

That means:
- We load the CSV from GCS into BigQuery.
- We preserve the raw source columns as much as possible.
- We DO NOT clean, split, rename, or model the data here.

Cleaning and modelling happen later in dbt.

Why this script is heavily commented:
The team is still learning data engineering, so the code is written to be readable and explainable,
not short and clever. Clever code is nice until it becomes tomorrow's "who wrote this ah?" funeral.
"""

# os lets us read environment variables from the current Python process.
import os

# load_dotenv reads key-value pairs from our local .env file.
# Example:
# GCP_PROJECT_ID=ntu-dsai-t4-netflix
#
# Important:
# .env is local only and should NOT be committed to GitHub.
from dotenv import load_dotenv

# bigquery lets Python talk to Google BigQuery.
# We use it here to:
# 1. Load the CSV from GCS into BigQuery.
# 2. Check whether the target table exists.
# 3. Run verification queries after loading.
from google.cloud import bigquery


def load_project_config():
    """
    Load project configuration from the local .env file.

    Why use .env?
    We do not want to hardcode project IDs, bucket names, dataset names,
    and table names all over the script.

    If we need to change a project setting later, we update .env instead of
    hunting through the script like a sad civil servant looking for one missing form.
    """

    # Load variables from .env into the Python process.
    load_dotenv()

    # Read required settings from .env.
    config = {
        "gcp_project_id": os.getenv("GCP_PROJECT_ID"),
        "gcp_location": os.getenv("GCP_LOCATION"),
        "gcs_bucket_name": os.getenv("GCS_BUCKET_NAME"),
        "gcs_raw_object_path": os.getenv("GCS_RAW_OBJECT_PATH"),
        "bigquery_raw_dataset": os.getenv("BIGQUERY_RAW_DATASET"),
        "bigquery_raw_table": os.getenv("BIGQUERY_RAW_TABLE"),
    }

    # Find missing values early.
    #
    # This prevents the script from failing later with a vague Google Cloud error.
    missing_keys = []

    for key, value in config.items():
        if value is None or value.strip() == "":
            missing_keys.append(key)

    if missing_keys:
        raise ValueError(
            "Missing required config values in .env: "
            + ", ".join(missing_keys)
            + "\n\nPlease check your .env file before running this script."
        )

    return config

def build_gcs_uri(config):
    """
    Build the full GCS URI for the raw CSV file.

    GCS URI format:

        gs://bucket-name/path/to/file.csv

    For this project:

        gs://ntu-dsai-t4-netflix-raw-001/raw/netflix_titles.csv
    """

    gcs_uri = (
        f"gs://{config['gcs_bucket_name']}/"
        f"{config['gcs_raw_object_path']}"
    )

    return gcs_uri

def build_bigquery_table_id(config):
    """
    Build the fully-qualified BigQuery table ID.

    BigQuery table ID format:

        project_id.dataset_name.table_name

    For this project:

        ntu-dsai-t4-netflix.raw.netflix_titles
    """

    table_id = (
        f"{config['gcp_project_id']}."
        f"{config['bigquery_raw_dataset']}."
        f"{config['bigquery_raw_table']}"
    )

    return table_id

def print_config_summary(config, gcs_uri, table_id):
    """
    Print the source and target configuration.

    This is a human sanity check before we ask BigQuery to load anything.
    """

    print("\nBlock 3 configuration loaded successfully.")
    print(f"GCP project ID       : {config['gcp_project_id']}")
    print(f"GCP location         : {config['gcp_location']}")
    print(f"GCS source URI       : {gcs_uri}")
    print(f"BigQuery raw dataset : {config['bigquery_raw_dataset']}")
    print(f"BigQuery raw table   : {config['bigquery_raw_table']}")
    print(f"BigQuery table ID    : {table_id}")

def create_bigquery_client(config):
    """
    Create a BigQuery client.

    The BigQuery client is the Python object that lets this script talk to BigQuery.

    It uses your local Google authentication from:

        gcloud auth application-default login

    This means we do not need to store service account JSON files in the repo.
    """

    print("Creating BigQuery client...")

    # Read project ID from config.
    gcp_project_id = config["gcp_project_id"]

    # Create the BigQuery client for the project.
    client = bigquery.Client(project=gcp_project_id)

    print("BigQuery client created successfully.")
    print(f"Client project: {client.project}\n")

    return client

def check_bigquery_dataset_exists(client, config):
    """
    Check that the target BigQuery raw dataset exists.

    For this project, the dataset should be:

        ntu-dsai-t4-netflix.raw

    Why check this before loading?
    If the dataset does not exist, the load job will fail later.
    It is clearer to fail early with a simple message.
    """

    print("Checking BigQuery raw dataset...")

    # Build the full dataset ID.
    #
    # Format:
    # project_id.dataset_name
    #
    # Example:
    # ntu-dsai-t4-netflix.raw
    dataset_id = (
        f"{config['gcp_project_id']}."
        f"{config['bigquery_raw_dataset']}"
    )

    try:
        # Ask BigQuery to fetch dataset metadata.
        # If the dataset does not exist, this will raise an error.
        dataset = client.get_dataset(dataset_id)

    except Exception as error:
        raise RuntimeError(
            "BigQuery raw dataset check failed.\n\n"
            f"Expected dataset: {dataset_id}\n\n"
            "Please confirm the dataset exists in BigQuery before running Block 3.\n\n"
            "You can check manually with:\n\n"
            f"    bq ls {config['gcp_project_id']}:\n\n"
            "Original error:\n"
            f"{error}"
        )

    print("BigQuery raw dataset exists.")
    print(f"Dataset ID : {dataset.full_dataset_id}")
    print(f"Location   : {dataset.location}\n")

    return dataset

def get_raw_netflix_schema():
    """
    Define the explicit BigQuery schema for the raw Netflix table.

    Why explicit schema instead of autodetect?
    BigQuery autodetect is convenient, but it can guess data types differently
    if the source file changes slightly.

    For a team project, we want a stable raw contract.

    Raw table columns should match the Kaggle CSV as closely as possible:

        show_id
        type
        title
        director
        cast
        country
        date_added
        release_year
        rating
        duration
        listed_in
        description

    Important:
    This schema is still for the RAW layer.
    We are not cleaning or splitting anything here.
    """

    schema = [
        bigquery.SchemaField("show_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("title", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("director", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("cast", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("country", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("date_added", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("release_year", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("rating", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("duration", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("listed_in", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("description", "STRING", mode="NULLABLE"),
    ]

    return schema

def load_gcs_csv_to_bigquery(client, config, gcs_uri, table_id):
    """
    Load the raw Netflix CSV from GCS into BigQuery.

    Source:

        gs://ntu-dsai-t4-netflix-raw-001/raw/netflix_titles.csv

    Target:

        ntu-dsai-t4-netflix.raw.netflix_titles

    Important raw-layer rules:
    - Load the CSV as-is.
    - Preserve source columns.
    - Do not clean date_added here.
    - Do not split listed_in here.
    - Do not split country here.
    - Do not model cast/director here.

    This is just the warehouse landing table.
    """

    print("Loading GCS CSV into BigQuery raw table...")

    # Get the explicit raw schema.
    raw_schema = get_raw_netflix_schema()

    # Configure the BigQuery load job.
    #
    # source_format=CSV:
    #   The source file is a CSV.
    #
    # skip_leading_rows=1:
    #   The first row contains column headers, so BigQuery should not treat it as data.
    #
    # schema=raw_schema:
    #   Use our explicit schema instead of letting BigQuery guess.
    #
    # write_disposition=WRITE_TRUNCATE:
    #   Replace the table each time the script runs.
    #   This makes ingestion repeatable and avoids duplicate rows.
    #
    # create_disposition=CREATE_IF_NEEDED:
    #   Create the table if it does not already exist.
    #
    # allow_quoted_newlines=True:
    #   CSV text fields may contain line breaks inside quoted strings.
    #   This setting helps BigQuery read such rows properly.
    load_job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=raw_schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        allow_quoted_newlines=True,
        encoding="UTF-8",
    )

    print(f"Source GCS URI       : {gcs_uri}")
    print(f"Target BigQuery table: {table_id}")
    print("Write mode           : WRITE_TRUNCATE")
    print("Schema mode          : explicit schema")
    print()

    # Start the BigQuery load job.
    #
    # This tells BigQuery:
    # "Take the CSV file from GCS and load it into this table."
    load_job = client.load_table_from_uri(
        source_uris=gcs_uri,
        destination=table_id,
        job_config=load_job_config,
        location=config["gcp_location"],
    )

    print(f"Started BigQuery load job: {load_job.job_id}")
    print("Waiting for BigQuery load job to finish...")

    # .result() waits until the BigQuery job completes.
    # If the job fails, this line will raise an error.
    load_job.result()

    print("BigQuery load job completed successfully.")

    # Fetch the loaded table metadata.
    table = client.get_table(table_id)

    print("Raw table loaded successfully.")
    print(f"Table ID     : {table.full_table_id}")
    print(f"Row count    : {table.num_rows:,}")
    print(f"Column count : {len(table.schema)}")
    print()

    return table

def verify_bigquery_raw_table(client, table_id):
    """
    Verify the loaded BigQuery raw table.

    We check:
    1. The table exists.
    2. The table has rows.
    3. The table has the expected schema.
    4. A small sample query works.

    Why do this?
    A load job can complete, but we still want to prove that:
    - the table is queryable,
    - the row count is sensible,
    - the columns look correct,
    - the raw data is actually there.

    This is not analysis yet.
    This is just post-load verification.
    """

    print("Verifying BigQuery raw table...")

    # Ask BigQuery for table metadata.
    # This confirms the table exists and gives us schema/row count info.
    table = client.get_table(table_id)

    print("BigQuery table exists.")
    print(f"Table ID     : {table.full_table_id}")
    print(f"Row count    : {table.num_rows:,}")
    print(f"Column count : {len(table.schema)}")
    print()

    # Safety check:
    # If the table has zero rows, something went wrong.
    if table.num_rows == 0:
        raise ValueError(
            f"BigQuery table exists but has zero rows: {table_id}"
        )

    print("Schema found in BigQuery:")
    for field in table.schema:
        print(f"- {field.name}: {field.field_type}")

    print()

    # Expected raw columns from the Kaggle CSV.
    expected_columns = [
        "show_id",
        "type",
        "title",
        "director",
        "cast",
        "country",
        "date_added",
        "release_year",
        "rating",
        "duration",
        "listed_in",
        "description",
    ]

    # Extract the actual column names from the BigQuery table schema.
    actual_columns = []

    for field in table.schema:
        actual_columns.append(field.name)

    # Check whether any expected columns are missing.
    missing_columns = []

    for column in expected_columns:
        if column not in actual_columns:
            missing_columns.append(column)

    if missing_columns:
        raise ValueError(
            "BigQuery raw table is missing expected columns: "
            + ", ".join(missing_columns)
        )

    print("Expected raw columns are present.")
    print()

    # Run a simple row-count query.
    #
    # Yes, table.num_rows already gives us row count metadata.
    # But this query proves that the table can also be queried normally.
    row_count_query = f"""
    SELECT COUNT(*) AS row_count
    FROM `{table_id}`
    """

    row_count_result = client.query(row_count_query).result()

    # The query returns rows. In this case, exactly one row.
    for row in row_count_result:
        print(f"Query row count: {row.row_count:,}")

    print()

    # Run a small sample query.
    # We only select a few readable columns so the terminal output does not become
    # a cursed wall of Netflix descriptions.
    sample_query = f"""
    SELECT
        show_id,
        type,
        title,
        release_year,
        rating,
        duration
    FROM `{table_id}`
    LIMIT 10
    """

    sample_rows = client.query(sample_query).result()

    print("Sample rows from BigQuery raw table:")
    for row in sample_rows:
        print(
            f"- {row.show_id} | "
            f"{row.type} | "
            f"{row.title} | "
            f"{row.release_year} | "
            f"{row.rating} | "
            f"{row.duration}"
        )

    print()
    print("BigQuery raw table verification successful.")
    print()

def main():
    """
    Main function for Block 3.

    Current sections implemented:
    1. Load project config from .env.
    2. Build GCS source URI.
    3. Build BigQuery target table ID.
    4. Print source/target summary.
    5. Create BigQuery client.
    6. Check BigQuery raw dataset exists.
    7. Define explicit raw schema.
    8. Load GCS CSV into BigQuery.
    9. Verify row count, schema, and sample rows.
    """

    # Section 1: Load config from .env.
    # Reads your .env file and loads settings like GCP project, bucket name, 
    # GCS object path, BigQuery dataset, and BigQuery table.
    config = load_project_config()

    # Section 2: Build the full GCS source URI.
    gcs_uri = build_gcs_uri(config)

    # Section 3: Build the full BigQuery target table ID.
    table_id = build_bigquery_table_id(config)

    # Section 4: Print config summary for sanity checking
    print_config_summary(
        config=config,
        gcs_uri=gcs_uri,
        table_id=table_id,
    )

    # Section 5: Create BigQuery client.
    # Creates the Python connection to BigQuery.
    client = create_bigquery_client(config)

    # Section 6: Check that the raw dataset exists.
    # Checks that the raw dataset exists before trying to load into it.
    check_bigquery_dataset_exists(
        client=client,
        config=config,
    )

    # Section 7: Load the GCS CSV into BigQuery raw table.
    # Loads the CSV from GCS into BigQuery using the explicit schema.
    load_gcs_csv_to_bigquery(
        client=client,
        config=config,
        gcs_uri=gcs_uri,
        table_id=table_id,
    )

    # Section 8: Verify the loaded BigQuery raw table.
    # Loads the CSV from GCS into BigQuery using the explicit schema.
    verify_bigquery_raw_table(
        client=client,
        table_id=table_id,
    )

    print("Block 3 complete. GCS CSV has been loaded into BigQuery raw table and verified.")

# Only run main() when this file is executed directly.
if __name__ == "__main__":
    main()
