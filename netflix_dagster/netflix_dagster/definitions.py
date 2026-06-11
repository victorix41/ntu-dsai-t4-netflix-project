import os
from dagster import Definitions
from dagster_dbt import DbtCliResource
from .assets import extract_and_upload_to_gcs, load_gcs_to_bigquery, dbt_netflix_dsp_assets
from .project import dbt_netflix_project

defs = Definitions(
    assets=[
        extract_and_upload_to_gcs,
        load_gcs_to_bigquery,
        dbt_netflix_dsp_assets
    ],
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt_netflix_project,
            env=os.environ # Continues to forward your system profile variables
        ),
    },
)