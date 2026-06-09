WITH base AS (SELECT
    show_id,
    TRIM(cast_name)      AS cast_name
FROM {{ source('raw', 'netflix_titles') }},
UNNEST(SPLIT(TRIM(`cast`), ',')) AS cast_name
WHERE TRIM(`cast`) IS NOT NULL AND TRIM(`cast`) != ''
)

SELECT *
FROM base
WHERE TRIM(cast_name) IS NOT NULL AND TRIM(cast_name) != ''