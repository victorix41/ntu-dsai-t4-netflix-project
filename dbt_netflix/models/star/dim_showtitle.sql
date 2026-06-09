SELECT
        show_id,
        TRIM(title)      AS title,
        COALESCE(NULLIF(TRIM(director), ''), 'Unknown')      AS director,
        TRIM(description) AS description
    FROM {{ source('raw', 'netflix_titles') }}
    WHERE TRIM(title) IS NOT NULL and TRIM(title) != ''