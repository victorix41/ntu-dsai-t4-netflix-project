import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

# streanlit theme
# primaryColor = "#1E90FF" # Set your desired color
# backgroundColor = "#080808"
# secondaryBackgroundColor = "#F5F5F5"
# textColor = "#FFFFFF"

# 1. Page config
st.set_page_config(
    page_title="Netflix Analytics",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Display a local image and set a custom width
st.image('assets/Netflix_Logo_RGB.png', width=200)
st.title("Analysis of Netflix Content Strategy")
st.markdown('### From a public dataset - <a href="https://www.kaggle.com/datasets/shivamb/netflix-shows/data">Netflix</a>', unsafe_allow_html=True)
st.caption("DSAI- 3F TEAM 4 -- Kenny - Valerie - Hwee Kian - Daniel - Kum Seng - Neville.")
st.markdown("---")
# 2. Secure authentication & client initialization
@st.cache_resource
def get_bigquery_client():
    try:
        # Looks for credentials in .streamlit/secrets.toml locally or environment variables on deployment
        key_dict = st.secrets["gcp_service_account"]
        credentials = service_account.Credentials.from_service_account_info(key_dict)
        return bigquery.Client(credentials=credentials, project=key_dict["project_id"])
    except Exception as e:
        st.error(f"Failed to connect to BigQuery. Check your secrets file. Error: {e}")
        st.stop()

client = get_bigquery_client()

# ==============================================================================
# 3. Cached Data Fetching (Reading cleanly from your updated 11-column view)
# ==============================================================================
@st.cache_data(ttl=600)
def load_netflix_data():
    query = """
    SELECT 
        show_id,
        show_type AS type,  -- 🚀 MUST BE 'show_type AS type' to pull from your view cleanly!
        title,
        director,
        release_year,
        date_added,
        rating,
        duration,
        countries,
        genres,
        cast_members
    FROM 
        `ntu-dsai-t4-netflix.analytics.netflix_dash`
    """
    query_job = client.query(query)
    # 🚀 FORCE the client to use the standard API instead of the Storage API
    return query_job.to_dataframe(create_bqstorage_client=False)


with st.spinner("Fetching unified star-schema view from BigQuery..."):
    df = load_netflix_data()

# 4. Sidebar Dynamic Filtering Layer
st.sidebar.header("Filter Content")

# Content Type Filter (Movie vs TV Show)
available_types = df['type'].dropna().unique().tolist()
selected_types = st.sidebar.multiselect("Content Type", options=available_types, default=available_types)

# Extract unique un-aggregated genres for clean sidebar selection
unique_genres = set()
for genre_list in df['genres'].dropna():
    unique_genres.update([g.strip() for g in genre_list.split(',')])
sorted_genres = sorted(list(unique_genres))

selected_genres = st.sidebar.multiselect("Genres", options=sorted_genres, default=sorted_genres)

# 5. Apply Sidebar Filters to Dataframe
# Filter by Content Type
filtered_df = df[df['type'].isin(selected_types)]

# Filter by Genre list (checks if any selected genre matches items inside the row's string list)
if selected_genres:
    filtered_df = filtered_df[filtered_df['genres'].apply(
        lambda x: any(genre in str(x) for genre in selected_genres) if pd.notnull(x) else False
    )]
# Quick Introduction to Netflix
st.markdown("### Quick Introduction to Netflix")
st.markdown("1. Started as a DVD-by-mail video rental service in 1997 by Hastings and Randolf, but was shutdown in 2023")
st.markdown("2. Is considered the king of streaming, with its primary competitive benchmark, YouTube.")
st.markdown("3.Over 70% of its membership base resides outside the United States and is fast expanding internationally, particularly in the fast growing Asia-Pacific market.")

# 6. Dashboard Layout Elements
# Summary KPI Cards
total_titles = len(filtered_df)
movies_count = len(filtered_df[filtered_df['type'] == 'Movie'])
shows_count = len(filtered_df[filtered_df['type'] == 'TV Show'])

st.markdown("### Movies and TV Shows added annually, up to 2021")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Catalog Titles", f"{total_titles:,}")
with col2:
    st.metric("Total Movies", f"{movies_count:,}")
with col3:
    st.metric("Total TV Shows", f"{shows_count:,}")

# Assuming 'df' is your loaded DataFrame from load_netflix_data()
# 1. Convert to datetime and extract the year as an integer
df['date_added'] = pd.to_datetime(df['date_added'])
df['year_added'] = df['date_added'].dt.year

# Drop rows where date_added was missing/NaT so they don't break the slider
df_clean = df.dropna(subset=['year_added'])
df_clean['year_added'] = df_clean['year_added'].astype(int)



# 2. Setup a Yearly Integer Slider
min_year = int(df_clean['year_added'].min())
max_year = int(df_clean['year_added'].max())

selected_year_range = st.slider(
    "Select Year Range",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),  # Default to full range
    step=1,                      # Move by 1 year increments
    format="%d"                  # Displays numbers cleanly without commas (e.g., 2021)
)

# 3. Filter the DataFrame based on the selected years
start_year, end_year = selected_year_range
filtered_chart_df = df_clean[
    (df_clean['year_added'] >= start_year) & 
    (df_clean['year_added'] <= end_year)
]

# 4. Transform data: Group by the extracted year and type, then count
chart_data = (
    filtered_chart_df.groupby(['year_added', 'type'])
    .size()
    .unstack(fill_value=0)  # Pivots 'type' into columns (Movie, TV Show)
)

# 5. Display the Interactive Yearly Area Chart
if not chart_data.empty:
    # 🚀 Get the exact column order from your pivoted data (e.g., ['Movie', 'TV Show'])
    columns_in_order = chart_data.columns.tolist()
    
    # Map out your colors based on that exact order
    color_palette = []
    for col in columns_in_order:
        if col == "Movie":
            color_palette.append("#916A45")  # Pink hex code
        elif col == "TV Show":
            color_palette.append("#B25929")  # Peach hex code
        else:
            color_palette.append("#7B7964")  # Fallback blue
            
    # Pass the clean list of colors to the chart
    st.area_chart(chart_data, color=color_palette)
else:
    st.warning("No data available for the selected year range.")


st.markdown("Key Observations:")
st.markdown("4. Movie adding trend peaked at 1400 Movies in 2019, but suffered a sharp decline to less than 1000 in 2021.")
st.markdown("5. TV Shows adding trend peaked at less than 600 TV Shows a year between 2019 and 2020, but levels off to just above 500 in 2021")
st.markdown("6. At its peak in 2019, TV Shows were less than a third of Movies. In Two short years, this ratio became more than half of Movies, signifying a shift in content mix.")

# ==============================================================================
# Global Slider & Side-by-Side Top 10 Country Bar Charts
# ==============================================================================

st.write("### Top 10 Countries producing Content")

# 1. Setup a single shared Yearly Integer Slider
min_year = int(df_clean['year_added'].min())
max_year = int(df_clean['year_added'].max())

selected_year_range = st.slider(
    "Select Shared Year Range",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),  # Defaults to the full timeline range
    step=1,
    format="%d"
)

# 2. Filter the primary DataFrame based on the shared slider selection
start_year, end_year = selected_year_range
filtered_chart_df = df_clean[
    (df_clean['year_added'] >= start_year) & 
    (df_clean['year_added'] <= end_year)
]

# 3. Separate the filtered dataset into Movies and TV Shows
movies_df = filtered_chart_df[filtered_chart_df['type'] == 'Movie']
tv_shows_df = filtered_chart_df[filtered_chart_df['type'] == 'TV Show']

# 4. Process Movie Data: Explode, count, and sort descending
if 'countries' in movies_df.columns:
    movies_exploded = movies_df['countries'].dropna().str.split(',').explode().str.strip()
    # .value_counts() naturally sorts from most to least
    top_movie_countries = movies_exploded.value_counts().head(10).to_frame(name='Movies')
else:
    top_movie_countries = pd.DataFrame()

# 5. Process TV Show Data: Explode, count, and sort descending
if 'countries' in tv_shows_df.columns:
    tv_exploded = tv_shows_df['countries'].dropna().str.split(',').explode().str.strip()
    # .value_counts() naturally sorts from most to least
    top_tv_countries = tv_exploded.value_counts().head(10).to_frame(name='TV Shows')
else:
    top_tv_countries = pd.DataFrame()

# 6. Create Side-by-Side Layout Columns
col1, col2 = st.columns(2)

# Left Column: Most Movies (Most on left -> Least on right)
with col1:
    st.write("#### Most Movies by Country")
    if not top_movie_countries.empty:
        st.bar_chart(top_movie_countries, color="#FF69B4")  # Movie Pink
    else:
        st.warning("No Movie data available for this range.")

# Right Column: Most TV Shows (Most on left -> Least on right)
with col2:
    st.write("#### Most TV Shows by Country")
    if not top_tv_countries.empty:
        st.bar_chart(top_tv_countries, color="#FFDAB9")  # TV Show Peach
    else:
        st.warning("No TV Show data available for this range.")
# 7. Distribution Charts
st.markdown("---")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("📈 Releases Over Time")
    if not filtered_df.empty:
        # 🚀 FIXED: Changed .reset_name() to .reset_index(name=...)
        release_trends = filtered_df.groupby('release_year').size().reset_index(name='titles_released')
        st.line_chart(data=release_trends, x='release_year')
    else:
        
        st.info("No data available for the current filter settings.")

with chart_col2:
    st.subheader("🎯 Top Maturity Ratings Distribution")
    if not filtered_df.empty:
        rating_counts = filtered_df['rating'].value_counts()
        st.bar_chart(rating_counts)
    else:
        st.info("No data available for the current filter settings.")

# 8. Interacting Data Grid Table View
st.subheader("📋 Filtered Catalog Data")
st.dataframe(
    filtered_df[['show_id', 'title', 'type', 'release_year', 'rating', 'duration', 'countries', 'genres']], 
    use_container_width=True,
    hide_index=True
)