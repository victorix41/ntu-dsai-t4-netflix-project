import os
from google.cloud import bigquery
from google.oauth2 import service_account

def setup_netflix_view():
    print("🚀 Initializing BigQuery Client...")
    
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "ntu-dsai-netflix-runner-key.json")
    
    try:
        credentials = service_account.Credentials.from_service_account_file(key_path)
        # Lock client onto your exact team project workspace
        client = bigquery.Client(credentials=credentials, project="ntu-dsai-t4-netflix")
    except Exception as e:
        print(f"❌ Auth Failed: Ensure your service account JSON file exists. Error: {e}")
        return
  
    view_id = "ntu-dsai-t4-netflix.analytics.netflix_dash"
    
    sql_query = f"""
    CREATE OR REPLACE VIEW `{view_id}` AS
    SELECT 
        f.show_id,
        f.type AS show_type,  -- Aliased to avoid reserved keyword collision
        t.title,
        t.director,
        f.release_year,
        f.date_added,
        r.rating,
        f.duration,
        c.countries,
        g.genres,
        ast.cast_members
    FROM 
        `ntu-dsai-t4-netflix.analytics.fact_showlist` f
    LEFT JOIN 
        `ntu-dsai-t4-netflix.analytics.dim_showtitle` t ON f.show_id = t.show_id
    LEFT JOIN 
        `ntu-dsai-t4-netflix.analytics.dim_agerating` r ON f.show_id = r.show_id
    
    -- Pre-aggregate dimensions to preserve a perfect grain of 1 row per show_id
    LEFT JOIN (
        SELECT show_id, STRING_AGG(DISTINCT country, ', ') AS countries
        FROM `ntu-dsai-t4-netflix.analytics.dim_showcountry`
        GROUP BY show_id
    ) c ON f.show_id = c.show_id
    
    LEFT JOIN (
        SELECT show_id, STRING_AGG(DISTINCT genre, ', ') AS genres
        FROM `ntu-dsai-t4-netflix.analytics.dim_showgenre`
        GROUP BY show_id
    ) g ON f.show_id = g.show_id
    
    LEFT JOIN (
        SELECT show_id, STRING_AGG(DISTINCT cast_name, ', ') AS cast_members
        FROM `ntu-dsai-t4-netflix.analytics.dim_showcast`
        GROUP BY show_id
    ) ast ON f.show_id = ast.show_id;
    """
    
    print(f"🔄 Deploying flattened view to BigQuery: {view_id}...")
    
    try:
        query_job = client.query(sql_query)
        query_job.result()  # Wait for deployment to complete
        print(f"✅ Success! Flattened view is live. Your team can now query `{view_id}`.")
    except Exception as e:
        print(f"❌ SQL Execution Error: {e}")

if __name__ == "__main__":
    setup_netflix_view()
