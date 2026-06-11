SELECT
        show_id,
        COALESCE(NULLIF(TRIM(rating), ''), 'Unknown') AS rating
    FROM {{ source('raw', 'netflix_titles') }}