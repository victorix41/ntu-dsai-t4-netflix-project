"""
Block 1/2: Extract Kaggle Netflix CSV and upload it to Google Cloud Storage.

Official project flow for this script:

Kaggle API
→ local CSV checkpoint at data/raw/netflix_titles.csv
→ GCS object at raw/netflix_titles.csv

Why we keep a local CSV checkpoint:
- It lets us inspect the downloaded file before uploading to GCS.
- It makes the pipeline easier for teammates to understand.
- It helps us debug whether a failure happened during Kaggle download or GCS upload.

Important raw data rule:
This script should NOT clean, rename, split, or model the data.
It only moves the raw Netflix CSV from Kaggle to our cloud staging area.
Cleaning and modelling happen later in dbt.
"""


def main():
    """
    Main function for Block 1/2.

    Later, this function will:
    1. Read project settings from environment variables.
    2. Use the Kaggle API to download the Netflix dataset.
    3. Save netflix_titles.csv into data/raw/.
    4. Upload netflix_titles.csv to Google Cloud Storage.
    5. Print simple checks such as file path, row count, and column list.

    For now, this is only a placeholder so the repo structure is clear.
    """
    print("TODO: Download Kaggle Netflix dataset and upload netflix_titles.csv to GCS.")


if __name__ == "__main__":
    main()
