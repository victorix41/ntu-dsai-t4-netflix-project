import os
from pathlib import Path
from dagster_dbt import DbtProject

# 1. Resolve path to assets.py folder (.../netflix_dagster/netflix_dagster)
CURRENT_DIR = Path(__file__).resolve().parent

# 2. Go up exactly 2 levels to reach the repository root
REPO_ROOT = CURRENT_DIR.parent.parent

# 3. Safely target the target dbt folder node
DBT_PROJECT_DIR = REPO_ROOT / "dbt_netflix"

dbt_netflix_project = DbtProject(
    project_dir=os.fspath(DBT_PROJECT_DIR),
)
dbt_netflix_project.prepare_if_dev()