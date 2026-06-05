SELECT
    show_id,
    type,
    duration,
    SAFE_CAST(release_year AS INT64)                    AS release_year,
    SAFE.PARSE_DATE('%B %d, %Y', TRIM(date_added))      AS date_added
FROM {{ source('raw', 'netflix_titles') }}