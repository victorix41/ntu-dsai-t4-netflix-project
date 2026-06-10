import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import plotly.express as px

import base64

# 1. Page config
st.set_page_config(
    page_title="Netflix Analytics",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)
# display title
st.title("Data Analytics for Netflix Content Strategy")
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

# 3. Cached Data Fetching (Reading cleanly from updated 11-column view)
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


# 1. Function to convert local image to a base64 string
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        # Fallback if the path is slightly off during testing
        return ""


# 2. Convert local asset file
local_image_path = "assets/Netflix_Logo_RGB.png"
img_base64 = get_base64_image(local_image_path)

# 3. Render the centered logo using the base64 string
if img_base64:
    st.sidebar.markdown(
        f"""
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_base64}" width="150">
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.sidebar.error(f"Could not find logo at {local_image_path}")

# Your existing filter code follows below..

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
st.markdown("2. Is considered the king of streaming, alongside YouTube, though they have different strengths.")
st.markdown("3. Over 70% of its membership base resides outside the United States and is fast expanding, particularly in the fast growing Asia-Pacific market.")

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

# 2. Setup a Yearly Integer Slider inside the sidebar
min_year = int(df_clean['year_added'].min())
max_year = int(df_clean['year_added'].max())

# Inject custom CSS to turn the slider label text white
st.markdown(
    """
    <style>
        div[data-testid="stSidebar"] div[data-testid="stSlider"] p {
            color: white !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. GET SLIDER VALUES ---
selected_year_range = st.sidebar.slider(
    "Select Year Range",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),  # Default to full range
    step=1,                      # Move by 1 year increments
    format="%d"                  # Displays numbers cleanly without commas (e.g., 2021)
)
# Split the tuple into start and end years
start_year, end_year = selected_year_range

# --- 2. FILTER & AGGREGATE DATA GLOBALLY ---
# Filter by Year Added and then group
df_added_filtered = df_clean[
    (df_clean['year_added'] >= start_year) & 
    (df_clean['year_added'] <= end_year)
]
df_added = df_added_filtered.groupby(['year_added', 'type']).size().reset_index(name='Count')

# Filter by Release Year and then group
df_release_filtered = df_clean[
    (df_clean['release_year'] >= start_year) & 
    (df_clean['release_year'] <= end_year)
]
df_release = df_release_filtered.groupby(['release_year', 'type']).size().reset_index(name='Count')


# --- 3. PLOT THE FILTERED DATA ---
view_option = st.selectbox(
    "Choose Timeline Metric:",
    ["Show Trends by Date Added to Netflix", "Show Trends by Content Release Year"]
)

if "Date Added" in view_option:
    fig = px.line(
        df_added,  # Uses the filtered dataframe
        x="year_added",
        y="Count",
        color="type",
        title=f"Content Added to Netflix ({start_year} - {end_year})",
        labels={"year_added": "Year Added", "Count": "Total Titles"},
        color_discrete_map={"Movie": "#E50914", "TV Show": "#00C853"},
        markers=True
    )
else:
    fig = px.line(
        df_release,  # Uses the filtered dataframe
        x="release_year",
        y="Count",
        color="type",
        title=f"Content Trends by Original Release Year ({start_year} - {end_year})",
        labels={"release_year": "Original Release Year", "Count": "Total Titles"},
        color_discrete_map={"Movie": "#E50914", "TV Show": "#00C853"},
        markers=True
    )

st.plotly_chart(fig, use_container_width=True)
# ----

# ----
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
            color_palette.append("#8B0000")  # Pink hex code
        elif col == "TV Show":
            color_palette.append("#1C1C1C")  # Peach hex code
        else:
            color_palette.append("#FF4C4C")  # Fallback blue
            
    # Pass the clean list of colors to the chart
    st.area_chart(chart_data, color=color_palette)
else:
    st.warning("No data available for the selected year range.")

st.markdown("Business : What is the current situation?")
st.markdown("Key Observations:")
st.markdown("4. Movie adding trend peaked at 1400 Movies in 2019, but suffered a sharp decline to less than 1000 in 2021.")
st.markdown("5. TV Shows adding trend peaked at less than 600 TV Shows a year between 2019 and 2020, but levels off to just above 500 in 2021")
st.markdown("6. At its peak in 2019, TV Shows were less than a third of Movies. In Two short years, this ratio became more than half of Movies, signifying a shift in content mix.")

# ==============================================================================
# Global Slider & Side-by-Side Top 10 Country Bar Charts
# ==============================================================================
st.write("### Top 10 Countries producing Content")

# 1. REMOVED the local st.slider widget block completely.
# It now references your global 'selected_year_range' from the sidebar.
start_year, end_year = selected_year_range

# 2. Filter the primary DataFrame based on the shared global sidebar selection
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
    top_movie_countries = movies_exploded.value_counts().head(10).to_frame(name='Movies')
else:
    top_movie_countries = pd.DataFrame()

# 5. Process TV Show Data: Explode, count, and sort descending
if 'countries' in tv_shows_df.columns:
    tv_exploded = tv_shows_df['countries'].dropna().str.split(',').explode().str.strip()
    top_tv_countries = tv_exploded.value_counts().head(10).to_frame(name='TV Shows')
else:
    top_tv_countries = pd.DataFrame()

# 6. Create Side-by-Side Layout Columns
col1, col2 = st.columns(2)

# Left Column: Most Movies
with col1:
    st.write("#### Most Movies by Country")
    if not top_movie_countries.empty:
        st.bar_chart(top_movie_countries, color="#FF69B4")  # Movie Pink
    else:
        st.warning("No Movie data available for this range.")

# Right Column: Most TV Shows
with col2:
    st.write("#### Most TV Shows by Country")
    if not top_tv_countries.empty:
        st.bar_chart(top_tv_countries, color="#FFDAB9")  # TV Show Peach
    else:
        st.warning("No TV Show data available for this range.")
# ----------------

# --------------------------------------
# Q5 CHART SHOWING GAP BETWEEN RELEASE_YEAR AND DATE_ADDED
# --- 1. SAMPLE DATA SETUP ---
if "df_clean" not in locals():
    data = {
        "type": ["Movie", "Movie", "TV Show", "Movie", "TV Show"] * 100,
        "release_year": [2018, 2019, 2020, 2021, 2015] * 100,
        "date_added": pd.to_datetime(
            ["2019-01-01", "2019-05-01", "2020-01-01", "2021-01-01", "2016-06-01"]
            * 100
        ),
    }
    df_clean = pd.DataFrame(data)

# Extract year from date_added
df_clean["year_added"] = df_clean["date_added"].dt.year


# --- 2. GLOBAL SIDEBAR FILTER ---
min_year = int(df_clean["year_added"].min())
max_year = int(df_clean["year_added"].max())

# Custom CSS to ensure the sidebar slider label is white
st.markdown(
    """
    <style>
        div[data-testid="stSidebar"] .stSlider label {
            color: white !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Single global timeline slider in the sidebar (Set to your 2014-2021 window)
selected_year_range = st.sidebar.slider(
    "Select Year Range",
    min_value=min_year,
    max_value=max_year,
    value=(2014, 2021),
    step=1,
    format="%d"
)

start_year, end_year = selected_year_range


# --- 3. DATA PROCESSING FOR UNIFIED HORIZONTAL AXIS ---
# Strict Filter: Keep only data within the slider's window based on year_added
df_filtered = df_clean[
    (df_clean["year_added"] >= start_year) & (df_clean["year_added"] <= end_year)
]

# A. Group by Year Added
df_added_group = (
    df_filtered.groupby(["year_added", "type"])
    .size()
    .reset_index(name="Count")
    .rename(columns={"year_added": "Year"})
)
df_added_group["Metric"] = df_added_group["type"] + "s Added (Platform Year)"

# B. Group by Release Year
df_release_group = (
    df_filtered.groupby(["release_year", "type"])
    .size()
    .reset_index(name="Count")
    .rename(columns={"release_year": "Year"})
)
# Keep only the rows where the release year fits within our current visible axis window
df_release_group = df_release_group[
    (df_release_group["Year"] >= start_year) & (df_release_group["Year"] <= end_year)
]
df_release_group["Metric"] = df_release_group["type"] + "s Released (Original Year)"

# C. Merge both sets together into a single master timeline dataframe
df_timeline = pd.concat([df_added_group, df_release_group], ignore_index=True)


# --- 4. STREAMLIT INTERFACE & PLOTTING ---
st.title("📈 Gap between media release_year and date_added to catalog")
st.markdown(f"Direct comparison of original release years to catalog additions from **{start_year} to {end_year}**.")

# Plot all 4 lines together on the same horizontal axis
fig = px.line(
    df_timeline,
    x="Year",
    y="Count",
    color="Metric",
    title=f"Title Release to Catalog Timeline Analysis ({start_year} - {end_year})",
    labels={"Year": "Year", "Count": "Total Titles"},
    color_discrete_map={
        "Movies Added Year": "#E50914",       # Solid Netflix Red
        "Movies Release Year": "#FF6B6B",    # Light Red
        "TV Shows Added Year": "#00C853",     # Solid Green
        "TV Shows Released Year": "#69F0AE"   # Light Green
    },
    markers=True,
)

# Customize chart layout to look sharp
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(type="linear", tickmode="linear", dtick=1, showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
    legend=dict(title_text="Series Legend", orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
)

# Display the interactive chart
st.plotly_chart(fig, use_container_width=True)

st.markdown("Key Observations:")
st.markdown("1. Movie catalog dates lag release dates by approx. 2 years as seen from 2017 peak to 2019 peak.")
st.markdown("1. However, the two TV Shows curves shows almost no lag between catalog and release dates.")

# -------------------
st.write("### 🎬 Franchise Sequels vs. 📺 TV Show Durations")

# 1. Use your existing global sidebar slider values
start_year, end_year = selected_year_range

# 2. Filter the core dataframe based on the global sidebar slider
filtered_charts_df = df_clean[
    (df_clean["year_added"] >= start_year) & (df_clean["year_added"] <= end_year)
].copy()

# Initialize dataframes as empty structures
movie_sequels_dist = pd.DataFrame()
tv_duration_dist = pd.DataFrame()

if not filtered_charts_df.empty:
    # Normalize column names to lowercase to prevent KeyErrors
    filtered_charts_df.columns = filtered_charts_df.columns.str.lower()
    
    # ==========================================
    # LEFT CHART: Movie Sequels / Franchise Count
    # ==========================================
    movies_df = filtered_charts_df[filtered_charts_df["type"].str.lower() == "movie"].copy()

    if not movies_df.empty and "title" in movies_df.columns:
        def get_franchise_base(title_val):
            import re
            title_val = str(title_val).strip()
            # Strips out trailing numbers, Part II, Chapter 3, etc.
            base = re.sub(
                r"(\s+v(ol|olume)?\.?\s*\d+|\s+\d+|:\s+.*|\s+part\s+.*|\s+chapter\s+.*)$",
                "",
                title_val,
                flags=re.IGNORECASE,
            )
            return base.strip()

        movies_df["franchise_base"] = movies_df["title"].apply(get_franchise_base)
        franchise_counts = (
            movies_df.groupby("franchise_base").size().reset_index(name="total_movies")
        )
        franchise_counts["sequel_count"] = franchise_counts["total_movies"] - 1

        movie_sequels_dist = (
            franchise_counts.groupby("sequel_count").size().reset_index(name="movie_count")
        )
        movie_sequels_dist["sequel_count"] = movie_sequels_dist["sequel_count"].astype(str)

    # ==========================================
    # RIGHT CHART: TV Show Season Durations
    # ==========================================
    tv_shows_df = filtered_charts_df[filtered_charts_df["type"].str.lower() == "tv show"].copy()

    if not tv_shows_df.empty and "duration" in tv_shows_df.columns:
        # Extracts digits from strings like "1 Season" or "3 Seasons"
        tv_shows_df["seasons"] = (
            tv_shows_df["duration"].astype(str).str.extract(r"(\d+)").astype(float)
        )
        tv_duration_dist = (
            tv_shows_df.groupby("seasons").size().reset_index(name="tv_show_count")
        )
        tv_duration_dist = tv_duration_dist.sort_values(by="seasons")
        tv_duration_dist["seasons"] = tv_duration_dist["seasons"].astype(int).astype(str)


# ==========================================
# RENDER SIDE-BY-SIDE COLUMNS
# ==========================================
col1, col2 = st.columns(2)

# Left Column: Movie Sequels Bar Chart
with col1:
    st.write("#### Movie Franchise & Sequel Distribution")
    if not movie_sequels_dist.empty:
        fig_sequels = px.bar(
            movie_sequels_dist,
            x="sequel_count",
            y="movie_count",
            title="Number of Sequels per Film Title",
            labels={"sequel_count": "Number of Sequels (0 = Standalone)", "movie_count": "Total Movies"},
            color_discrete_sequence=["#E50914"]  # Netflix Red
        )
        fig_sequels.update_layout(
            xaxis=dict(type="category", showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            showlegend=False
        )
        st.plotly_chart(fig_sequels, use_container_width=True)
    else:
        st.warning("No Movie sequel data calculated for this range. Check if 'title' column exists.")

# Right Column: TV Shows Duration Bar Chart
with col2:
    st.write("#### TV Shows Duration Distribution")
    if not tv_duration_dist.empty:
        fig_tv_duration = px.bar(
            tv_duration_dist,
            x="seasons",
            y="tv_show_count",
            title="TV Show Length by Total Seasons",
            labels={"seasons": "Duration (Number of Seasons)", "tv_show_count": "Total TV Show Count"},
            color_discrete_sequence=["#00C853"]  # Green
        )
        fig_tv_duration.update_layout(
            xaxis=dict(type="category", showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            showlegend=False
        )
        st.plotly_chart(fig_tv_duration, use_container_width=True)
    else:
        st.warning("No TV Show duration data available. Check if 'duration' column exists.")

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