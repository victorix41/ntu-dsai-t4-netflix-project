WITH base AS (SELECT
    show_id,
    TRIM(country_item)      AS country
FROM {{ source('raw', 'netflix_titles') }},
UNNEST(SPLIT(
    CASE 
        WHEN TRIM(country) IS NULL  THEN 'International'
        WHEN TRIM(country) = ''     THEN 'International'
        ELSE TRIM(country)
    END
, ',')) AS country_item
)
SELECT *
FROM base
WHERE TRIM(country) IS NOT NULL AND TRIM(country) != ''