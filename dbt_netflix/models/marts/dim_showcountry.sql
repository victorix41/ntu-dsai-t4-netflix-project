-- dbt_netflix/models/marts/dim_showcountry.sql
--
-- Block 5/6 – Dimension / bridge table: title ↔ country
-- Source : analytics.stg_netflix_titles
-- Output : analytics.dim_showcountry
-- Grain  : one row per (show_id, country) pair
--
-- Columns (Section 11.2 of the implementation guide):
-- ──────────────────────────────────────────────────────────────────
-- show_id   STRING   PK (composite with country), NOT NULL
-- country   STRING   NOT NULL
-- ──────────────────────────────────────────────────────────────────
--
-- The raw 'country' field may contain multiple comma-separated values,
-- e.g. 'United States, United Kingdom'.
--
-- Steps:
--   1. SPLIT(country, ',') → array of country strings.
--   2. UNNEST (CROSS JOIN) expands each element into its own row.
--   3. TRIM removes leading/trailing spaces.
--   4. WHERE filters out blank strings produced by consecutive commas.
--
-- Rows whose original country was NULL/blank were filled with 'International'
-- in the staging model, so they appear here as ('show_id', 'International').

SELECT
    show_id,
    TRIM(country_part) AS country

FROM {{ ref('stg_netflix_titles') }},
    UNNEST(SPLIT(country, ',')) AS country_part

WHERE TRIM(country_part) != ''
