-- dbt_netflix/models/marts/dim_agerating.sql
--
-- Block 6 – Dimension table: age/maturity rating
-- Source : analytics.stg_netflix_titles
-- Output : analytics.dim_agerating
-- Grain  : one row per show_id
--
-- Columns (Section 11.2 of the implementation guide):
-- ──────────────────────────────────────────────────
-- show_id   STRING   PK, unique, NOT NULL
-- rating    STRING   NOT NULL
-- ──────────────────────────────────────────────────
--
-- 'rating' was already cleaned in the staging model:
--   NULL / blank values were replaced with 'Unknown'.

SELECT
    show_id,
    rating

FROM {{ ref('stg_netflix_titles') }}
