-- dbt_netflix/models/marts/dim_showtitle.sql
--
-- Block 6 – Dimension table: title metadata
-- Source : analytics.stg_netflix_titles
-- Output : analytics.dim_showtitle
-- Grain  : one row per show_id
--
-- Columns (Section 11.2 of the implementation guide):
-- ──────────────────────────────────────────────────
-- show_id    STRING   PK, unique, NOT NULL
-- title      STRING   NOT NULL
-- director   STRING   (may be 'Unknown' where original was NULL / blank)
-- cast       STRING   (may be 'Unknown' where original was NULL / blank)
-- ──────────────────────────────────────────────────
--
-- director and cast are kept as flat comma-separated strings here,
-- matching the guide spec.  Splitting them into individual people is
-- a stretch item per Section 1.2 of the implementation guide.

SELECT
    show_id,
    title,
    director,
    cast

FROM {{ ref('stg_netflix_titles') }}
