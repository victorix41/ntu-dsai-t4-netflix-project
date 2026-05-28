# Decision Log

This file records important project decisions so the team does not keep reopening settled items.

## 2026-05-28 — Dataset selected

Decision: Use the Kaggle Netflix dataset `shivamb/netflix-shows`.

Reason:
- Simple external CSV source.
- Suitable for demonstrating ingestion into BigQuery.
- Contains useful catalogue metadata for dbt modelling and dashboarding.

Limitation:
- The dataset does not contain viewer demand, watch time, user ratings, subscriber behaviour, or popularity data.
- Analysis should be framed as Netflix catalogue / portfolio analysis.

## 2026-05-28 — Official ingestion path

Decision: Use Python scripts for ingestion.

Official flow:

Kaggle API
→ local CSV checkpoint
→ Google Cloud Storage
→ BigQuery raw.netflix_titles
→ dbt transformations

Reason:
- TA confirmed ingestion tool choice is flexible.
- Python is easier for beginner teammates to read, comment, debug, and reuse.
- Meltano was considered, but is not required for MVP.

## 2026-05-28 — Script structure

Decision: Use two ingestion scripts.

scripts/01_extract_and_upload_to_gcs.py
scripts/02_load_gcs_to_bigquery.py

Reason:
- Keeps the flow simple.
- Separates raw file staging from BigQuery loading.
- Easier to debug than one giant script.

## 2026-05-28 — Official source of truth

Decision:
- GitHub is the official source of truth for code and documentation.
- BigQuery is the official source of truth for shared project data.
- Personal GCP / BigQuery projects may be used for learning only.

Reason:
- Teammates can experiment safely in their own sandbox.
- The official project should still have one shared repo and one shared raw BigQuery table.
