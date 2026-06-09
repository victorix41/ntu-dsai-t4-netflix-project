-- dbt_netflix/models/marts/dim_showgenre.sql
--
-- Block 5/6 – Dimension / bridge table: title ↔ genre
-- Source : analytics.stg_netflix_titles
-- Output : analytics.dim_showgenre
-- Grain  : one row per (show_id, genre) pair
--
-- Columns (Section 11.2 of the implementation guide):
-- ──────────────────────────────────────────────────────────────────
-- show_id   STRING   PK (composite with genre), NOT NULL
-- genre     STRING   NOT NULL
-- ──────────────────────────────────────────────────────────────────
--
-- The raw 'listed_in' field contains comma-separated genre strings,
-- e.g. 'Documentaries, International Movies'.
--
-- Steps:
--   1. SPLIT(listed_in, ',') → array of genre strings.
--   2. UNNEST (CROSS JOIN) expands each element into its own row.
--   3. TRIM removes leading/trailing spaces.
--   4. WHERE filters out blank strings.
--
-- This table acts as both the bridge (show_id → genre) and as the
-- source for a distinct genre list.  To get distinct genres for
-- analytics queries, simply: SELECT DISTINCT genre FROM dim_showgenre.

SELECT
    show_id,
    TRIM(genre_part) AS genre

FROM {{ ref('stg_netflix_titles') }},
    UNNEST(SPLIT(listed_in, ',')) AS genre_part

WHERE TRIM(genre_part) != ''
