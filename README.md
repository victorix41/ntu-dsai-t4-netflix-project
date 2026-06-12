# NTU DSAI Module 2 Team 4 — Netflix Catalogue Analytics Project

## Project purpose

This project builds a simple data engineering and analytics pipeline using the Kaggle Netflix catalogue dataset.

The project analyses Netflix catalogue metadata such as title type, genre, country, rating, release year, date added, and duration.

Important limitation: this dataset does not contain viewer behaviour, watch time, likes, ratings, subscriber behaviour, or true content demand. Therefore, the project should be framed as catalogue / portfolio analysis, not viewership or popularity analysis.

## Locked project names

| Item | Name |
|---|---|
| GitHub repo | `ntu-dsai-t4-netflix-project` |
| GCP project | `ntu-dsai-t4-netflix` |
| GCS bucket | `ntu-dsai-t4-netflix-raw-001` |
| GCS / BigQuery location | `US` |
| BigQuery raw dataset | `raw` |
| BigQuery analytics dataset | `analytics` |
| Raw BigQuery table | `raw.netflix_titles` |

## Target architecture

```text
Kaggle API
→ local raw CSV checkpoint
→ Google Cloud Storage raw file
→ BigQuery raw.netflix_titles
→ dbt staging model
→ dbt marts / star schema
→ analysis notebook + Streamlit dashboard
## Official ingestion scripts

scripts/01_extract_and_upload_to_gcs.py
scripts/02_load_gcs_to_bigquery.py

Script 01 downloads the Kaggle Netflix CSV and uploads it to GCS.

Script 02 loads the GCS CSV into BigQuery as raw.netflix_titles.

## Source-of-truth rules

- GitHub is the source of truth for code and documentation.
- BigQuery is the source of truth for shared project data.
- WhatsApp is for discussion only, not file storage.
- Personal BigQuery projects can be used for learning, but the official project tables live in the shared GCP project.
- Do not commit secrets, Kaggle tokens, service account files, .env files, raw CSV files, or downloaded datasets.

## Repo structure

docs/
data/raw/
scripts/
dbt_netflix/models/staging/
dbt_netflix/models/marts/
notebooks/
dashboard/

## Block plan

| Block | Purpose |
|---|---|
| 0 | Repo and project setup |
| 1/2 | Kaggle API download + upload raw CSV to GCS |
| 3 | Load GCS CSV into BigQuery raw table |
| 4 | dbt staging model |
| 5 | dbt bridge tables |
| 6 | dbt marts / star schema |
| 7 | Analysis notebook |
| 8 | Streamlit dashboard and demo |

## Local setup

Create a virtual environment:

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Google Cloud authentication will use local gcloud login.

Kaggle credentials must be configured locally and must not be committed to GitHub.

## Python environment rule

Each teammate should create their own local Python environment on their own machine.

The `.venv/` folder is local only and should not be pushed to GitHub.

The shared setup file is:

requirements.txt

This means everyone uses the same package list, but each person installs those packages into their own local environment.

Recommended setup on WSL / Mac / Linux:

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Recommended setup on Windows PowerShell:

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Simple explanation:
GitHub stores the recipe.
requirements.txt stores the ingredient list.
Each person's .venv is their own kitchen.
Do not upload your kitchen to GitHub.

## Project Repository

Public repository URL: https://github.com/kennywong85/ntu-dsai-t4-netflix-project

This repository contains the Module 2 Team 4 Netflix catalogue analytics project, including ingestion scripts, dbt transformation models, Dagster orchestration files, dashboard files, documentation and setup instructions.
