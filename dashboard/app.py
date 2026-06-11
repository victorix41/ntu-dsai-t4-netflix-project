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
# Destination link intro

st.markdown(" ")
st.markdown("<div id='Intro'></div>", unsafe_allow_html=True)
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")

# display title
st.title("Data Analytics Report")
st.markdown("### for Netflix Content Strategy Planning")
st.markdown('##### Source: <a href="https://www.kaggle.com/datasets/shivamb/netflix-shows/data">Netflix</a> public dataset', unsafe_allow_html=True)
st.markdown("##### DSAI- 3F TEAM 4 -- Kenny - Valerie - Hwee Kian - Daniel - Kum Seng - Neville.")
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

# Custom CSS to make the slider track visible against the dark sidebar background
# st.markdown(
#     """
#     <style>
#     /* Targets the unselected background track line */
#     div[data-baseweb="slider"] > div:first-child {
#         background: rgba(255, 255, 255, 0.1) !important;
#     }
    
#     /* Optional: Changes the tick mark label numbers to a clear white/grey if they look dim */
#     div[data-testid="stSlider"] label {
#         color: #000000 !important;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

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

# 4. Sidebar Dynamic Filtering Layer
st.sidebar.header("Content Filters")

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
st.markdown("<h3>Quick Introduction to Netflix (2015-2021)</h3>", unsafe_allow_html=True)
st.markdown("1. Started as a DVD-by-mail video rental service in 1997 by Hastings and Randolf, but was shutdown in 2023")
st.markdown("2. Is considered the king of streaming, alongside YouTube, though they have different strengths.")
st.markdown("3. Over 70% of its membership base resides outside the United States and is fast expanding, particularly in the fast growing Asia-Pacific market.")


# 6. Dashboard Layout Elements
# Summary KPI Cards
total_titles = len(filtered_df)
movies_count = len(filtered_df[filtered_df['type'] == 'Movie'])
shows_count = len(filtered_df[filtered_df['type'] == 'TV Show'])

# pad with space on top
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
# Destination link 1
st.markdown("<div id='Insights 1'></div>", unsafe_allow_html=True)


# st.markdown("### Catalog Title additions, yearly, up to 2021")
# col1, col2, col3 = st.columns(3)
# with col1:
#     st.metric("Total Catalog Titles", f"{total_titles:,}")
# with col2:
#     st.metric("Total Movies", f"{movies_count:,}")
# with col3:
#     st.metric("Total TV Shows", f"{shows_count:,}")

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
# st.markdown(
#     """
#     <style>
#         div[data-testid="stSidebar"] div[data-testid="stSlider"] p {
#             color: white !important;
#         }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

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
    (df_clean['year_added'] >= start_year) & (df_clean['year_added'] <= end_year)
]

df_added = df_added_filtered.groupby(['year_added', 'type']).size().reset_index(name='Count')

# Filter by Release Year and then group
df_release_filtered = df_clean[
    (df_clean['release_year'] >= start_year) & 
    (df_clean['release_year'] <= end_year)
]
df_release = df_release_filtered.groupby(['release_year', 'type']).size().reset_index(name='Count')

# Add links to sidebar for next sections
st.sidebar.markdown(
    '<a href="#Intro" style="display: block; text-align: center; color: #E50914; font-weight: bold; text-decoration: none;"> Intro</a>', 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<a href="#Insights 1" style="display: block; text-align: center; color: #E50914; font-weight: bold; text-decoration: none;"> Insights 1</a>', 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<a href="#Insights 2" style="display: block; text-align: center; color: #E50914; font-weight: bold; text-decoration: none;"> Insights 2</a>', 
    unsafe_allow_html=True
)


# ==========================================
# MOVIES AND TV SHOWS ADDED ANNUALLY
# ==========================================
st.markdown("<div id='Insights 1'></div>", unsafe_allow_html=True)
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown("<h3>Content Added to Netflix (2015-2021)</h3>", unsafe_allow_html=True)
# 1. Display your KPI metric blocks
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.metric("Total Catalog Titles", "8,807")
with col_kpi2:
    st.metric("Total Movies", "6,131")
with col_kpi3:
    st.metric("Total TV Shows", "2,676")

st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")

# 2. Grab your existing global sidebar slider values
start_year, end_year = selected_year_range

# 3. Filter the primary DataFrame based on the global sidebar selection
df_filtered_timeline = df_clean[
    (df_clean["year_added"] >= start_year) & (df_clean["year_added"] <= end_year)
]

# 4. Process data into counts per year per type
df_timeline_counts = (
    df_filtered_timeline.groupby(["year_added", "type"])
    .size()
    .reset_index(name="Total Titles")
    .rename(columns={"year_added": "Year Added"})
)

# 5. Render the simplified trend chart directly (No selectbox dropdown!)
fig_trends = px.line(
    df_timeline_counts,
    x="Year Added",
    y="Total Titles",
    color="type",
    title=f"Content Added to Netflix ({start_year} - {end_year})",
    labels={"Year Added": "Year Added", "Total Titles": "Total Titles"},
    color_discrete_map={"Movie": "#E50914", "TV Show": "#00C853"},  # Red & Green
    markers=True,
)

fig_trends.update_layout(
    hovermode="x unified",
    xaxis=dict(type="linear", dtick=1, showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
)

st.plotly_chart(fig_trends, use_container_width=True)

# 6. Keep your key observations listed clean underneath
st.markdown(" ")
st.markdown("""
**Key Observations:**
1. **MOVIES ARE IN SHARP DECLINE:** Movie Additions peaked at 1400 Movies in 2019, but suffered a sharp decline to less than 1000 in 2021.
2. **TV SHOWS REMAIN STABLE:** TV Shows Additions peaked at less than 600 TV Shows a year between 2019 and 2020, but levels off to just above 500 in 2021.
3. **GROWTH OF TV SHOWS:** At its peak in 2019, TV Shows were less than a third of Movies. In Two short years, this ratio shot up to more than half of Movies, signifying a shift in content mix.
4. **CROSSOVER EXPECTED IN 2023-2024 SEASON:** Expect capacity for production of TV Shows due to diminished release of movies.
""")

# ==============================================================================
# Global Slider & Side-by-Side Top 10 Country Bar Charts
# ==============================================================================
st.markdown("<h2>Content Added to Netflix (2015-2021)</h2>", unsafe_allow_html=True)
# Destination link 2
st.markdown("<div id='Insights 2'></div>", unsafe_allow_html=True)
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

st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown("<h3>Top Countries for Content Production</h3>", unsafe_allow_html=True)
st.markdown(" ")
st.markdown("Gap between media release_year and date_added to catalog")
# 6. Create Side-by-Side Layout Columns
col1, col2 = st.columns(2)

# Left Column: Most Movies
with col1:
    st.write("#### Most Movies")
    if not top_movie_countries.empty:
        st.bar_chart(top_movie_countries, color="#FF69B4")  # Movie Pink
    else:
        st.warning("No Movie data available for this range.")

# Right Column: Most TV Shows
with col2:
    st.write("#### Most TV Shows")
    if not top_tv_countries.empty:
        st.bar_chart(top_tv_countries, color="#FFDAB9")  # TV Show Peach
    else:
        st.warning("No TV Show data available for this range.")

st.markdown(" ")
st.markdown(" ")
st.markdown(" ")



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
st.markdown("1. However, TV Shows have almost no lag between release and catalog dates.")

# -------------------
st.write("### Insights from Sequels and Seasons")

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
    
    # =========================
    # LEFT CHART: Movie Sequels
    # =========================
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

    # ============================
    # RIGHT CHART: TV Show Seasons
    # ============================
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
    st.write("#### Movies")
    if not movie_sequels_dist.empty:
        # Limit to the top 5 largest categories by movie count
        movie_sequels_dist_limited = (
            movie_sequels_dist.sort_values(by="movie_count", ascending=False)
            .head(5)
            .copy()
        )
        # Re-sort by sequel count so the x-axis reads naturally (e.g., 0, 1, 2...)
        movie_sequels_dist_limited["sequel_count_int"] = movie_sequels_dist_limited["sequel_count"].astype(int)
        movie_sequels_dist_limited = movie_sequels_dist_limited.sort_values(by="sequel_count_int")

        fig_sequels = px.bar(
            movie_sequels_dist_limited,
            x="sequel_count",
            y="movie_count",
            title="Top 5 Sequels",
            labels={"sequel_count": "No. of Sequels", "movie_count": "Total Movies"},
            color_discrete_sequence=["#E50914"]  # Netflix Red
        )
        fig_sequels.update_layout(
            xaxis=dict(type="category", showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            showlegend=False,
            margin=dict(t=50, b=50, l=50, r=20)
        )
        st.plotly_chart(fig_sequels, use_container_width=True)
    else:
        st.warning("No Movie sequel data calculated for this range. Check if 'title' column exists.")

# Right Column: TV Shows Duration Bar Chart
with col2:
    st.write("#### TV Shows")
    if not tv_duration_dist.empty:
        # Limit to the first 5 seasonal lengths (Seasons 1 through 5)
        tv_duration_dist_limited = (
            tv_duration_dist.sort_values(by="seasons", key=lambda x: x.astype(int))
            .head(5)
            .copy()
        )

        fig_tv_duration = px.bar(
            tv_duration_dist_limited,
            x="seasons",
            y="tv_show_count",
            title="Top 5 Seasons",
            labels={"seasons": "Number of Seasons", "tv_show_count": "Total TV Show Count"},
            color_discrete_sequence=["#00C853"]  # Green
        )
        fig_tv_duration.update_layout(
            xaxis=dict(type="category", showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            showlegend=False,
            margin=dict(t=50, b=50, l=50, r=20)
        )
        st.plotly_chart(fig_tv_duration, use_container_width=True)
    else:
        st.warning("No TV Show duration data available. Check if 'duration' column exists.")
# Key observations below
st.markdown("""
**Key Observations:**
1. **SEQUELS OF MOVIES:** 90% of movies on Netflix are standalone films.
2. **SEASONS OF TV SHOWS:** Across the time range, 80% of TV Shows are 1 or 2 season runs.
""")

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