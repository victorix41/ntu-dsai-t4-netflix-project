-- dbt_netflix/models/staging/stg_netflix_titles.sql
--
-- Block 4 – Staging model
-- Source : raw.netflix_titles
-- Output : analytics.stg_netflix_titles
-- Grain  : one cleaned row per show_id
--
-- Cleaning rules
-- ──────────────────────────────────────────────────────────────
-- director, cast, rating, duration  NULL / blank → 'Unknown'
-- country                           NULL / blank → 'International'
-- date_added                        NULL / blank → 'January 01, <release_year>'
--                                   then parsed to DATE
-- release_year                      cast to INT64
-- ──────────────────────────────────────────────────────────────

WITH raw AS (
    SELECT *
    FROM {{ source('raw', 'netflix_titles') }}
)

SELECT
    show_id,
    type,
    TRIM(title)                                                       AS title,

    -- director: fill NULLs and blank strings with 'Unknown'
    COALESCE(NULLIF(TRIM(director), ''), 'Unknown')                   AS director,

    -- cast: fill NULLs and blank strings with 'Unknown'
    COALESCE(NULLIF(TRIM(cast), ''), 'Unknown')                       AS cast,

    -- country: fill NULLs and blank strings with 'International'
    COALESCE(NULLIF(TRIM(country), ''), 'International')              AS country,

    -- date_added:
    --   If NULL or blank, build a synthetic 'January 01, <release_year>'
    --   string, then parse to a proper DATE value.
    PARSE_DATE(
        '%B %d, %Y',
        COALESCE(
            NULLIF(TRIM(date_added), ''),
            CONCAT('January 01, ', CAST(release_year AS STRING))
        )
    )                                                                 AS date_added,

    -- release_year: cast to INT64
    SAFE_CAST(release_year AS INT64)                                  AS release_year,

    -- rating: fill NULLs and blank strings with 'Unknown'
    COALESCE(NULLIF(TRIM(rating), ''), 'Unknown')                     AS rating,

    -- duration: fill NULLs and blank strings with 'Unknown'
    COALESCE(NULLIF(TRIM(duration), ''), 'Unknown')                   AS duration,

    TRIM(listed_in)                                                   AS listed_in,
    TRIM(description)                                                 AS description

FROM raw
