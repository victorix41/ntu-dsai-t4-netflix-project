"""
Block 1/2: Extract Kaggle Netflix CSV and upload it to Google Cloud Storage.

Official project flow:

Kaggle API
→ local CSV checkpoint at data/raw/netflix_titles.csv
→ GCS object at raw/netflix_titles.csv

Important project rule:
This script is part of the RAW ingestion layer.

That means:
- We download the original Kaggle CSV.
- We save it locally for inspection.
- We upload the same raw CSV to GCS.
- We DO NOT clean, rename, split, or model the data here.

Cleaning and modelling happen later in dbt.

Why this script is heavily commented:
The team is still learning data engineering, so the code is written to be readable and explainable,
not short and clever. Clever code is fun until it becomes tomorrow's group project crime scene.
"""

# pathlib gives us a clean way to work with file and folder paths.
from pathlib import Path

# os lets us read environment variables and check local system settings.
import os

# load_dotenv reads key-value pairs from our local .env file.
from dotenv import load_dotenv

# KaggleApi lets Python talk to Kaggle using the Kaggle API.
# It uses your local Kaggle credentials, usually stored at:
# ~/.kaggle/kaggle.json
from kaggle.api.kaggle_api_extended import KaggleApi

# pandas is used here only for a lightweight local CSV verification:
# row count and column list.
# We are NOT doing cleaning or analysis in this script.
import pandas as pd

# zipfile lets Python open and extract .zip files.
# Kaggle may download a single CSV as netflix_titles.csv.zip,
# so we need to unzip it before checking for netflix_titles.csv.
import zipfile

# google-cloud-storage lets Python upload files into Google Cloud Storage.
# In this script, we use it to upload the raw Netflix CSV to our GCS bucket.
from google.cloud import storage


def load_project_config():
    """
    Load project configuration from the local .env file.

    Why use .env?
    We do not want to hardcode project settings all over the script.
    If bucket names, dataset names, or file paths change later,
    we update .env instead of hunting through the code like sad data archaeologists.

    This function returns a dictionary containing all settings needed by the script.
    """

    # Load variables from .env into the current Python process.
    # opens your local .env file and loads the values into Python.
    load_dotenv()

    # Read settings from .env. stores them in a dictionary called config.
    # os.getenv("GCP_PROJECT_ID") asks Python: “Do you know a setting called GCP_PROJECT_ID?”
    config = {
        "gcp_project_id": os.getenv("GCP_PROJECT_ID"),
        "gcp_location": os.getenv("GCP_LOCATION"),
        "gcs_bucket_name": os.getenv("GCS_BUCKET_NAME"),
        "gcs_raw_object_path": os.getenv("GCS_RAW_OBJECT_PATH"),
        "kaggle_dataset_slug": os.getenv("KAGGLE_DATASET_SLUG"),
        "local_raw_file": os.getenv("LOCAL_RAW_FILE"),
    }

    # Check whether any required config value is missing.
    missing_keys = []

    # loops through every config setting and checks missing and blank values
    for key, value in config.items():
        if value is None or value.strip() == "":
            missing_keys.append(key)

    # if there are mssing/blank values, display error message
    if missing_keys:
        raise ValueError(
            "Missing required config values in .env: "
            + ", ".join(missing_keys)
        )

    return config

def print_config_summary(config):
    """
    Print a simple summary of the loaded configuration.
    This helps us confirm that the script is reading the correct project,
    bucket, Kaggle dataset, and local file path before we do anything dangerous.
    """

    print("\nProject configuration loaded successfully.")
    print(f"GCP project ID      : {config['gcp_project_id']}")
    print(f"GCP location        : {config['gcp_location']}")
    print(f"GCS bucket name     : {config['gcs_bucket_name']}")
    print(f"GCS object path     : {config['gcs_raw_object_path']}")
    print(f"Kaggle dataset slug : {config['kaggle_dataset_slug']}")
    print(f"Local raw file path : {config['local_raw_file']}")

def prepare_local_raw_folder(local_raw_file_path):
    """
    Prepare the local folder where the Kaggle CSV will be saved.

    Example:
    If local_raw_file_path is:

        data/raw/netflix_titles.csv

    then local_raw_file_path.parent is:

        data/raw

    This function creates data/raw/ if it does not already exist.
    """

    # .parent gets the folder part of the file path.
    local_raw_folder = local_raw_file_path.parent

    # mkdir creates the folder.
    # parents=True means:
    # "If parent folders do not exist, create them too."
    # # exist_ok=True means:
    # "If the folder already exists, do not panic."
    local_raw_folder.mkdir(parents=True, exist_ok=True)

    print("Local raw folder is ready.")
    print(f"Folder path: {local_raw_folder}\n")

def check_kaggle_authentication(kaggle_dataset_slug):
    """
    Check that Kaggle authentication works before we try to download anything.
    Kaggle authentication can be set up in different ways depending on Kaggle CLI version.

    Common options:
    1. Newer flow:
       kaggle auth login

    2. Token file flow:
       ~/.kaggle/kaggle.json or Kaggle's newer local token file

    We do NOT hardcode credentials in this script.
    Ask the Kaggle API client to authenticate using whatever is valid
    local Kaggle credentials are already configured.
    """

    print("Checking Kaggle authentication...")

    # Create a Kaggle API client object.
    # KaggleApi() creates a Kaggle API object.
    api = KaggleApi()

    try:
        # Authenticate using locally configured Kaggle credentials.
        # If authentication is missing or invalid, Kaggle will raise an error.
        # If there is an error, catch error
        # Go to the next section and ask user to use 'kaggle auth login'
        api.authenticate()

    except Exception as error:
        raise RuntimeError(
            "Kaggle authentication failed.\n\n"
            "Please run this command in your terminal first:\n\n"
            "    kaggle auth login\n\n"
            "Then test access with:\n\n"
            "    kaggle datasets files -d shivamb/netflix-shows\n\n"
            "Original error:\n"
            f"{error}"
        )

    print("Kaggle authentication successful.")

    print("Checking whether the Kaggle dataset is reachable...")

    try:
        # Ask Kaggle to list the files inside the dataset.
        # This is a light check. It does not download the dataset yet.
        # the dataset slug is shivamb/netflix-shows
        dataset_files_response = api.dataset_list_files(kaggle_dataset_slug)

    except Exception as error:
        raise RuntimeError(
            "Kaggle dataset check failed.\n\n"
            f"Dataset slug used: {kaggle_dataset_slug}\n\n"
            "Please confirm the dataset exists and your Kaggle account can access it.\n\n"
            "You can also test manually with:\n\n"
            "    kaggle datasets files -d shivamb/netflix-shows\n\n"
            "Original error:\n"
            f"{error}"
        )

    # Kaggle returns file objects, not plain strings.
    # We extract the file names so we can read them easily.
    dataset_files = dataset_files_response.files

    file_names = []

    # Response from Kaggle is more like a list of file objects, where each object has a .name.
    # loop through the file objects, build a clean list of file names and display them
    for dataset_file in dataset_files:
        file_names.append(dataset_file.name)

    print("Kaggle dataset is reachable.")
    print(f"Dataset slug: {kaggle_dataset_slug}")
    print("Files found in dataset:")

    for file_name in file_names:
        print(f"- {file_name}")

    # For this project, we expect to see this specific netflix_titles.csv file
    expected_file_name = "netflix_titles.csv"

    # If it is missing, we should stop early instead of pretending everything is fine
    if expected_file_name not in file_names:
        raise FileNotFoundError(
            f"Expected file '{expected_file_name}' was not found in Kaggle dataset "
            f"'{kaggle_dataset_slug}'. Files found: {file_names}"
        )

    print(f"\nExpected file found: {expected_file_name}\n")

    # Return the authenticated API object so later functions can reuse it.
    # The function sends the authenticated Kaggle API object back to main().
    return api

def download_kaggle_csv(api, kaggle_dataset_slug, local_raw_file_path):
    """
    Download netflix_titles.csv from the Kaggle dataset into our local raw folder.

    Official local output:
        data/raw/netflix_titles.csv

    Important:
    This function only downloads the raw CSV.
    It does NOT clean, rename, split, or transform the data.

    Why download locally first?
    The local CSV acts as a checkpoint.
    If something goes wrong later during GCS upload or BigQuery loading,
    we can still inspect the downloaded source file.

    Important Kaggle behaviour:
    Kaggle may download the CSV as a zipped file:
        netflix_titles.csv.zip

    So this function handles both cases:
    1. If netflix_titles.csv appears directly, use it.
    2. If netflix_titles.csv.zip appears, unzip it.
    """

    print("Downloading Kaggle CSV...")

    # The specific file we expect from the Kaggle dataset.
    kaggle_file_name = "netflix_titles.csv"

    # The folder where the file should be downloaded.
    # which should be data/raw
    local_raw_folder = local_raw_file_path.parent

    # Kaggle sometimes saves the file as netflix_titles.csv.zip.
    # we need to handle if this situation arises
    downloaded_zip_path = local_raw_folder / f"{kaggle_file_name}.zip"
   
    # Remove old local copies before downloading again.
    # Why? If an old CSV already exists, the script might accidentally verify yesterday's file
    # instead of the file we just downloaded.
    # This keeps each run fresh and repeatable.
    stale_local_files = [
        local_raw_file_path,
        downloaded_zip_path,
    ]

    # remove the following if found:
    # data/raw/netflix_titles.csv
    # data/raw/netflix_titles.csv.zip
    for stale_file in stale_local_files:
        if stale_file.exists():
            print(f"Removing old local file before fresh download: {stale_file}")
            stale_file.unlink()

    # the actual download
    # Download one file from the Kaggle dataset.
    # dataset=kaggle_dataset_slug - Which Kaggle dataset to use.
    # file_name=kaggle_file_name - Which file inside that dataset to download.
    # path=str(local_raw_folder) - Where to save it locally.
    # force=True - Overwrite existing download if needed.
    # quiet=False - Show progress messages.
    api.dataset_download_file(
        dataset=kaggle_dataset_slug,
        file_name=kaggle_file_name,
        path=str(local_raw_folder),
        force=True,
        quiet=False,
    )

    # Situation 1:
    # Kaggle downloaded the CSV directly.
    if local_raw_file_path.exists():
        print("Kaggle CSV downloaded directly.")
        print(f"Local file path: {local_raw_file_path}\n")
        return

    # Situation 2:
    # Kaggle downloaded a zip file instead. :(
    if downloaded_zip_path.exists():
        print("Kaggle downloaded a zip file.")
        print(f"Zip file path: {downloaded_zip_path}")
        print("Extracting zip file...")

        # Open the zip file and extract its contents into data/raw/.
        with zipfile.ZipFile(downloaded_zip_path, "r") as zip_ref:
            zip_ref.extractall(local_raw_folder)

        print("Zip extraction complete.")

    # Final check:
    # After direct download or unzip, the official CSV path must exist.
    # Does data/raw/netflix_titles.csv exist now? if yes, skip the filenotfounderror
    if not local_raw_file_path.exists():
        raise FileNotFoundError(
            "Expected downloaded CSV was not found after Kaggle download/unzip.\n"
            f"Expected path: {local_raw_file_path}\n"
            f"Checked zip path: {downloaded_zip_path}"
        )

    print("Kaggle CSV downloaded and prepared successfully.")
    print(f"Local file path: {local_raw_file_path}\n")

def verify_local_csv(local_raw_file_path):
    """
    Verify the local raw CSV after download.
    This is a light sanity check only.

    We check:
    1. File exists.
    2. File size is greater than 0.
    3. Row count can be read.
    4. Column list matches what we expect.

    We are not cleaning the data here.
    We are just confirming the raw file is usable.
    """

    print("Verifying local CSV...")

    # Check that the file exists.
    # local_raw_file_path = data/raw/netflix_titles.csv
    # not a plain string, earlier in main(), we converted it into a Path object
    # do a check if the file exists
    if not local_raw_file_path.exists():
        raise FileNotFoundError(
            f"Local raw CSV does not exist: {local_raw_file_path}"
        )

    # Check the file size, get file size in bytes. we may get a file but is empty
    file_size_bytes = local_raw_file_path.stat().st_size
    if file_size_bytes == 0:
        raise ValueError(
            f"Local raw CSV exists but is empty: {local_raw_file_path}"
        )

    # Read the CSV using pandas.
    # This dataset is small, so using pandas is fine here.
    # We are only reading it to check row count and columns.
    df = pd.read_csv(local_raw_file_path)
    row_count = len(df)
    column_names = list(df.columns)

    # based on the metadata, we know that we expect these columns in the data
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

    # we do amissing column check, if there is a missing column, we add it to missing_columns
    missing_columns = []
    for column in expected_columns:
        if column not in column_names:
            missing_columns.append(column)

    # raise an error if there are missing columns
    if missing_columns:
        raise ValueError(
            "Local CSV is missing expected columns: "
            + ", ".join(missing_columns)
        )

    print("Local CSV verification successful.")
    print(f"File path : {local_raw_file_path}")
    print(f"File size : {file_size_bytes:,} bytes")
    print(f"Row count : {row_count:,}")
    print("Columns   :")

    for column in column_names:
        print(f"- {column}")

    print()

def upload_csv_to_gcs(config, local_raw_file_path):
    """
    Upload the verified local raw CSV to Google Cloud Storage.
    Official upload target:
        gs://ntu-dsai-t4-netflix-raw-001/raw/netflix_titles.csv

    Important:
    This uploads the raw CSV exactly as downloaded.
    It does NOT clean, rename, split, or transform the data.

    Why upload to GCS before BigQuery?
    GCS acts as the cloud landing zone.
    It gives us a clear raw file checkpoint before loading into BigQuery.
    """

    print("Uploading local CSV to Google Cloud Storage...")

    # First, make sure the local file exists.
    # We should never try to upload a file that is missing.
    if not local_raw_file_path.exists():
        raise FileNotFoundError(
            f"Cannot upload because local raw CSV does not exist: {local_raw_file_path}"
        )

    # Read GCP/GCS settings from config file input
    gcp_project_id = config["gcp_project_id"]
    gcs_bucket_name = config["gcs_bucket_name"]
    gcs_raw_object_path = config["gcs_raw_object_path"]

    # Build the final GCS URI for display.
    # Example:
    # gs://ntu-dsai-t4-netflix-raw-001/raw/netflix_titles.csv
    gcs_uri = f"gs://{gcs_bucket_name}/{gcs_raw_object_path}"

    print(f"Source local file : {local_raw_file_path}")
    print(f"Target GCS URI    : {gcs_uri}")

    # Create a Google Cloud Storage client, Python client that can talk to Google Cloud Storage.
    # This uses your local Google authentication from:
    # gcloud auth application-default login
    storage_client = storage.Client(project=gcp_project_id)

    # Get the bucket object.
    # This does not download or upload anything yet.
    # It simply points Python at the bucket name.
    bucket = storage_client.bucket(gcs_bucket_name)

    # Create a blob object.
    # In GCS language, a "blob" is a file/object inside a bucket.
    # Bucket:
    #   ntu-dsai-t4-netflix-raw-001
    # Blob/object path:
    #   raw/netflix_titles.csv
    blob = bucket.blob(gcs_raw_object_path)

    # Upload the local CSV file into the GCS blob path.
    # content_type="text/csv" tells GCS that this object is a CSV file.
    blob.upload_from_filename(
        filename=str(local_raw_file_path),
        content_type="text/csv",
    )

    print("Upload to GCS completed.")
    print(f"Uploaded file: {gcs_uri}\n")

    return gcs_uri

def verify_gcs_upload(config):
    """
    Verify that the raw CSV exists in Google Cloud Storage after upload.
    We check:
    1. The GCS object exists.
    2. GCS metadata can be loaded.
    3. Object size is greater than 0.
    This confirms that the upload worked before we move to BigQuery loading.
    """

    print("Verifying GCS upload...")

    gcp_project_id = config["gcp_project_id"]
    gcs_bucket_name = config["gcs_bucket_name"]
    gcs_raw_object_path = config["gcs_raw_object_path"]

    gcs_uri = f"gs://{gcs_bucket_name}/{gcs_raw_object_path}"

    # Create the GCS client.
    storage_client = storage.Client(project=gcp_project_id)

    # Point to the bucket and blob.
    bucket = storage_client.bucket(gcs_bucket_name)
    blob = bucket.blob(gcs_raw_object_path)

    # Check whether the object exists in GCS.
    if not blob.exists(client=storage_client):
        raise FileNotFoundError(
            f"GCS upload verification failed. Object not found: {gcs_uri}"
        )

    # Load metadata such as file size, content type, and update time.
    blob.reload(client=storage_client)

    # Check object size.
    if blob.size is None or blob.size == 0:
        raise ValueError(
            f"GCS object exists but appears to be empty: {gcs_uri}"
        )

    print("GCS upload verification successful.")
    print(f"GCS URI      : {gcs_uri}")
    print(f"Object size  : {blob.size:,} bytes")
    print(f"Content type : {blob.content_type}")
    print(f"Updated time : {blob.updated}")
    print()

def main():
    """
    Main function for Block 1/2.

   Current sections implemented:
    1. Load project config from .env.
    2. Prepare local raw folder.
    3. Check Kaggle authentication and dataset access.
    4. Download Kaggle dataset.
    5. Verify local CSV.
    6. Upload CSV to GCS.
    7. Verify GCS upload.
    """

    # Section 1: Load and print config.
    # Reads your .env file and stores important settings inside a Python dictionary.
    config = load_project_config()
    print_config_summary(config)

    # Convert the local raw file string into a Path object.
    # Turns the text "data/raw/netflix_titles.csv" into a proper Python path object
    local_raw_file_path = Path(config["local_raw_file"])

    print("Local raw file path as Path object:")
    print(local_raw_file_path)
    print()

    # Section 2A: Prepare local folder.
    # Makes sure the folder data/raw/ exists before downloading anything.
    prepare_local_raw_folder(local_raw_file_path)

    # Section 2B: Check Kaggle authentication.
    # Logs into Kaggle and checks that the dataset is reachable.
    api = check_kaggle_authentication(config["kaggle_dataset_slug"])

    # Section 3A: Download the Kaggle CSV locally.
    # Downloads netflix_titles.csv from Kaggle. If Kaggle gives a zip file, it unzips it.
    download_kaggle_csv(
        api=api,
        kaggle_dataset_slug=config["kaggle_dataset_slug"],
        local_raw_file_path=local_raw_file_path,
    )

    # Section 3B: Verify the downloaded local CSV.
    # Checks that the local CSV exists, is not empty, has 8,807 rows, and has the expected 12 columns.
    verify_local_csv(local_raw_file_path)

    # Section 4: Upload the verified local CSV to GCS.
    # Uploads the local CSV into Google Cloud Storage.
    upload_csv_to_gcs(
        config=config,
        local_raw_file_path=local_raw_file_path,
    )

    # Section 5: Verify the file exists in GCS.
    # Checks that the uploaded file really exists in GCS and is not empty.
    verify_gcs_upload(config)

    print("Blocks 1/2 complete. Kaggle CSV has been downloaded locally and uploaded to GCS.")

# Only run main() when this file is executed directly.
if __name__ == "__main__":
    main()
