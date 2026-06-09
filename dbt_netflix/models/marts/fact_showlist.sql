-- dbt_netflix/models/marts/fact_showlist.sql
--
-- Block 6 – Fact table
-- Source : analytics.stg_netflix_titles
-- Output : analytics.fact_showlist
-- Grain  : one row per show_id (one row per Netflix title)
--
-- Columns (Section 11.1 of the implementation guide):
-- ──────────────────────────────────────────────────
-- show_id       STRING   PK, unique
-- type          STRING   NOT NULL
-- duration      STRING   NOT NULL
-- release_year  INT64    NOT NULL
-- date_added    DATE     NOT NULL
-- ──────────────────────────────────────────────────
--
-- All values are already clean in the staging model.
-- This model simply selects the five columns that belong in the fact table.

SELECT
    show_id,
    type,
    duration,
    release_year,
    date_added

FROM {{ ref('stg_netflix_titles') }}
