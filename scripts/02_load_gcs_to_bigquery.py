"""
Block 3: Load the raw Netflix CSV from Google Cloud Storage into BigQuery.

Official project flow for this script:

GCS object:
gs://ntu-dsai-t4-netflix-raw-001/raw/netflix_titles.csv

→ BigQuery raw table:
raw.netflix_titles

Important raw data rule:
This script should preserve the original Kaggle CSV columns as much as possible.
It should NOT split genre, country, cast, or director fields.
Those transformations happen later in dbt.
"""


def main():
    """
    Main function for Block 3.

    Later, this function will:
    1. Read project settings from environment variables.
    2. Load the CSV from GCS into BigQuery.
    3. Create or replace the raw.netflix_titles table.
    4. Print the BigQuery table name.
    5. Run a simple row-count check.
    6. Confirm that the raw columns are present.

    For now, this is only a placeholder so the repo structure is clear.
    """
    print("TODO: Load GCS CSV into BigQuery raw.netflix_titles.")


if __name__ == "__main__":
    main()
