SELECT
    show_id,
    TRIM(genre)     AS genre
FROM {{ source('raw', 'netflix_titles') }},
UNNEST(SPLIT(listed_in, ',')) AS genre
WHERE listed_in IS NOT NULL