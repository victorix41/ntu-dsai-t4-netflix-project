SELECT
        show_id,
        rating
    FROM {{ source('raw', 'netflix_titles') }}