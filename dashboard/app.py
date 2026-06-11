import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import plotly.express as px
import numpy as np
import base64


# 1. Page config
st.set_page_config(
    page_title="Netflix Analytics",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Destination link introduction to Netflix Analytics

st.markdown(" ")
st.markdown("<div id='Introduction to Netflix Analytics'></div>", unsafe_allow_html=True)
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
st.markdown("3. Netflix's annual revenue in 2020 was 20.99B with 24% year-on-year growth and exceeding 200M subscribers.")
st.markdown("4. Over 70% of its membership base resides outside the United States and is fast expanding, particularly in the fast growing Asia-Pacific market.")
 
st.markdown("<div id='Business Needs'></div>", unsafe_allow_html=True)
st.markdown("<h3>Two overarching Business Needs:</h3>", unsafe_allow_html=True)
st.markdown("1. What is the strategy for content?")
st.markdown("2. How should we invest?")

st.markdown("<h3>Key Business Questions:</h3>", unsafe_allow_html=True)
st.markdown("Q1 What are the insights into content makeup of Netflix's vast catalog?")
st.markdown("Q2 Which countries produce the most movies & TV Shows in Netflix?")
st.markdown("Q3 Do directors influence New Titles acquisition?")
st.markdown("Q4 Which are the top genres and classifications for development?")
st.markdown("Q5 What are insights on gap between media release_year & date_added to catalog?")
st.markdown("Q6 What are insights into sequels and seasons?")

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
st.markdown("<div id='Insights from Content Makeup'></div>", unsafe_allow_html=True)


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
    '<a href="#Introduction to Netflix Analytics" style="display: block; text-align: center; color: #000000; font-weight: normal; text-decoration: none;"> Introduction to Netflix Analytics</a>', 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<a href="#Business Needs" style="display: block; text-align: center; color: #000000; font-weight: normal; text-decoration: none;"> Business Needs</a>', 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<a href="#Insights from Content Makeup" style="display: block; text-align: center; color: #000000; font-weight: normal; text-decoration: none;"> Insights from Content Makeup</a>', 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<a href="#Insights from Countries" style="display: block; text-align: center; color: #000000; font-weight: normal; text-decoration: none;"> Insights from Countries</a>', 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<a href="#Insights from Directors" style="display: block; text-align: center; color: #000000; font-weight: normal; text-decoration: none;"> Insights from Directors</a>', 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<a href="#Gap between release year and date added to catalog" style="display: block; text-align: center; color: #000000; font-weight: normal; text-decoration: none;"> Gap between release year and date added to catalog</a>', 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<a href="#Insights from Sequels and Seasons" style="display: block; text-align: center; color: #000000; font-weight: normal; text-decoration: none;"> Insights from Sequels and Seasons</a>', 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<a href="#Genre by Top 10 Countries" style="display: block; text-align: center; color: #000000; font-weight: normal; text-decoration: none;"> Genre by Top 10 Countries</a>', 
    unsafe_allow_html=True
)

# ==========================================
# MOVIES AND TV SHOWS ADDED ANNUALLY
# ==========================================
st.markdown("<div id='Insights 1'></div>", unsafe_allow_html=True)
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown("<h3>Netflix dataset from 2008 to 2021</h3>", unsafe_allow_html=True)
# 1. Display your KPI metric blocks
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.metric("Total Catalog Titles", "8,807")
with col_kpi2:
    st.metric("Total Movies", "6,131")
with col_kpi3:
    st.metric("Total TV Shows", "2,676")


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
    title=f"Content Makeup ({start_year}-{end_year})",
    labels={"Year Added": "Year Added", "Total Titles": "Total Titles"},
    color_discrete_map={"Movie": "#6495ED", "TV Show": "#DEB887"},  # plotly default
)

fig_trends.update_layout(
    hovermode="x unified",
    xaxis=dict(type="linear", dtick=1, showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
)

st.plotly_chart(fig_trends, use_container_width=True)

# 6. Keep your key observations listed clean underneath
st.markdown("""
**Key Observations:**
1. **MOVIES ARE IN SHARP DECLINE:** Movie Additions peaked at 1400 Movies in 2019, but suffered a sharp decline to less than 1000 in 2021.
2. **TV SHOWS REMAIN STABLE:** TV Shows Additions peaked at less than 600 TV Shows a year between 2019 and 2020, but levels off to just above 500 in 2021.
3. **GROWTH OF TV SHOWS:** At its peak in 2019, TV Shows were less than a third of Movies. In Two short years, this ratio shot up to more than half of Movies, signifying a shift in content mix.
""")

# ==============================================================================
# Global Slider & Side-by-Side Top 10 Country Bar Charts
# ==============================================================================

# Destination link 2
st.markdown("<div id='Insights from Countries'></div>", unsafe_allow_html=True)
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

# st.markdown(" ")
# st.markdown("Gap between media release_year and date_added to catalog")
# # 6. Create Side-by-Side Layout Columns
# col1, col2 = st.columns(2)

# # Left Column: Most Movies
# with col1:
#     st.write("#### Most Movies")
#     if not top_movie_countries.empty:
#         st.bar_chart(top_movie_countries, color="#6495ED")  # netflix red
#     else:
#         st.warning("No Movie data available for this range.")

# # Right Column: Most TV Shows
# with col2:
#     st.write("#### Most TV Shows")
#     if not top_tv_countries.empty:
#         st.bar_chart(top_tv_countries, color="#DEB887")  # TV Show Peach
#     else:
#         st.warning("No TV Show data available for this range.")



st.markdown("<h3>Top 10 Countries for Content Production</h3>", unsafe_allow_html=True)
st.markdown(" ")
st.markdown(" ")


# ==============================================================================
# 🌍 NEW COMPONENT: TOP CONTENT PRODUCING COUNTRIES COMPARISON
# ==============================================================================


# 1. Reuse your existing cached DataFrame and apply the global year filters
if 'df' in locals() or 'df' in globals():
    df_countries_raw = df.copy()
else:
    df_countries_raw = load_netflix_data()

# Apply your global slider dates (start_year and end_year)
if 'start_year' in locals() and 'end_year' in locals():
    # Make sure year_added is extracted if not already present
    if 'year_added' not in df_countries_raw.columns:
        if pd.api.types.is_datetime64_any_dtype(df_countries_raw['date_added']):
            df_countries_raw['year_added'] = df_countries_raw['date_added'].dt.year
        else:
            df_countries_raw['year_added'] = pd.to_datetime(df_countries_raw['date_added'].astype(str).str.strip(), errors='coerce').dt.year
            
    df_countries_filtered = df_countries_raw[
        (df_countries_raw['year_added'] >= start_year) & 
        (df_countries_raw['year_added'] <= end_year)
    ]
else:
    df_countries_filtered = df_countries_raw.copy()

# Drop missing records to ensure clean plotting
df_countries_filtered = df_countries_filtered.dropna(subset=['countries', 'type'])

# 2. Explode comma-separated countries so multi-production countries get shared credit
df_countries_filtered['country_list'] = df_countries_filtered['countries'].astype(str).str.split(', ')
df_countries_exploded = df_countries_filtered.explode('country_list')

# 3. Extract the Top 10 countries for Movies and Top 10 for TV Shows separately
top_movies = (
    df_countries_exploded[df_countries_exploded['type'] == 'Movie']
    .groupby('country_list').size()
    .nlargest(10).index.tolist()
)

top_tv_shows = (
    df_countries_exploded[df_countries_exploded['type'] == 'TV Show']
    .groupby('country_list').size()
    .nlargest(10).index.tolist()
)

# Combine unique countries from both Top 10 lists to build a unified Y-axis list
union_countries = list(set(top_movies + top_tv_shows))

# 4. Filter the main dataset to only include these top union countries
df_top_countries = df_countries_exploded[df_countries_exploded['country_list'].isin(union_countries)]

# 5. Group and aggregate counts by country and type
chart_data = (
    df_top_countries.groupby(['country_list', 'type'])
    .size()
    .reset_index(name='titles_count')
)

# Sort the chart data so the highest total volume country appears at the top of the Y-axis
total_volumes = df_top_countries.groupby('country_list').size().sort_values(ascending=True)
chart_data['country_list'] = pd.Categorical(chart_data['country_list'], categories=total_volumes.index, ordered=True)
chart_data = chart_data.sort_values('country_list')

# 6. Generate the Horizontal Grouped Bar Chart
fig_countries = px.bar(
    chart_data,
    x="titles_count",                  # Horizontal length matches title volume
    y="country_list",                  # Grouped categories stacked along the Y-axis
    color="type",                      # Color splits Movie vs TV Show
    barmode="group",                   # Forces bars side-by-side instead of stacking
    orientation="h",                   # Dictates a horizontal chart layout direction
    title=f"Top 10 Countries for Content Production ({start_year}-{end_year})",
    labels={
        "titles_count": "Total Titles Count",
        "country_list": "Country",
        "type": "Content Type"
    },
    color_discrete_map={
        "Movie": "#6495ED",            # Signature Netflix Red (consistent with your palette)
        "TV Show": "#DEB887"              # Standardizing with your blue selection
    },
    template="plotly_white"
)

# 7. Fine-tune layout parameters for slides presentation
fig_countries.update_layout(
    yaxis={'categoryorder': 'total ascending'}, # Displays most prolific producers clearly
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=40, b=20, l=10, r=10),
    height=600 # Extra vertical padding so all country labels stay easily readable
)

st.plotly_chart(fig_countries, use_container_width=True)

# ==============================================================================
# 🎬 NEW COMPONENT: DIRECTOR INFLUENCE & PIPELINE STRATEGY
# ==============================================================================
st.markdown("<div id='Insights from Directors'></div>", unsafe_allow_html=True)
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown(" ")
st.markdown("<h3>Nurturing Creative directors</h3>", unsafe_allow_html=True)
st.markdown(
    "Directors are creative visionaries and we want to understand their contribution to Netflix. "
    "This chart visualizes contributions to title catalog from new or returning directors."
)

# 1. Reuse your existing cached DataFrame
if 'df' in locals() or 'df' in globals():
    df_directors_raw = df.copy()
else:
    df_directors_raw = load_netflix_data()

# 🚀 2. FIX: Safely extract the year since 'date_added' is already a datetime object!
if pd.api.types.is_datetime64_any_dtype(df_directors_raw['date_added']):
    df_directors_raw['year_added'] = df_directors_raw['date_added'].dt.year
else:
    # Safe fallback just in case it behaves like a string object somewhere else
    df_directors_raw['year_added'] = pd.to_datetime(df_directors_raw['date_added'].astype(str).str.strip(), errors='coerce').dt.year

# 3. Apply your global sidebar filter variables dynamically
if 'start_year' in locals() and 'end_year' in locals():
    df_directors = df_directors_raw[
        (df_directors_raw['year_added'] >= start_year) & 
        (df_directors_raw['year_added'] <= end_year)
    ]
else:
    df_directors = df_directors_raw[
        (df_directors_raw['year_added'] >= 2017) & 
        (df_directors_raw['year_added'] <= 2021)
    ]

# Drop missing records to ensure accurate data plotting
df_directors = df_directors.dropna(subset=['director', 'year_added'])

# 4. Explode co-directors so every individual partner gets proper analytical credit
df_directors['director_list'] = df_directors['director'].astype(str).str.split(', ')
df_exploded = df_directors.explode('director_list').sort_values(by='year_added')

# 5. Map the first baseline milestone year each director ever appeared in the catalog
director_debut_years = df_exploded.groupby('director_list')['year_added'].min().to_dict()

# 6. Classify every individual asset addition as New vs. Returning Directors
df_exploded['talent_status'] = df_exploded.apply(
    lambda row: "New Director" if row['year_added'] == director_debut_years[row['director_list']] 
    else "Returning Director", axis=1
)

# 7. Aggregate data structures for Plotly
chart_metrics = df_exploded.groupby(['year_added', 'talent_status']).size().reset_index(name='additions_count')

# E.g., Use bright color for emphasis, dark/gray for base.
individual_color_config = {
    "New Director": "#6495ED",          # plotly default
    "Returning Director": "#DEB887"    # blue
    }
# 8. Render the presentation-ready Stacked Bar Chart (Fixing the barnorm argument)
fig_director = px.bar(
    chart_metrics, 
    x="year_added", 
    y="additions_count", 
    color="talent_status",
    title=f"New and Returning Directors ({start_year} - {end_year})",
    labels={
        "year_added": "Year Added to Catalog", 
        "additions_count": "Title Additions", 
        "talent_status": "Talent Segment"
    },
   # 🚀 APPLY THE INDIVIDUAL MAP HERE
    color_discrete_map=individual_color_config,
    template="plotly_white"
)
  



# # 8. Render the presentation-ready Stacked Bar Chart
# fig_director = px.bar(
#     chart_metrics, 
#     x="year_added", 
#     y="additions_count", 
#     color="talent_status",
#     labels={
#         "year_added": "Year Added to Catalog", 
#         "additions_count": "Volume of Credits", 
#         "talent_status": "Talent Segment"
#     },

# )


# 9. Configure the layout and enforce the 100% normalized stacked view here safely
fig_director.update_layout(
    xaxis_type='category',
    barmode='stack',                # Ensures bars stack on top of each other
    barnorm='percent',              # Forces the 100% distributed percentage view
    yaxis=dict(tickformat=".0f"),   # Clean integer layout format for the y-axis
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=30, b=20, l=10, r=10)
)

st.plotly_chart(fig_director, use_container_width=True)
# ==============================================================================
# Keep your key observations listed clean underneath
st.markdown("""
**Key Observations:**
1. **GROWING TREND OF RETURNING DIRECTORS:** From 2017 returning directors grow steadily from 1 in 3 to more than 1 in 2 in 2021.
""")
# --------------------------------------
# Q5 CHART SHOWING GAP BETWEEN RELEASE_YEAR AND DATE_ADDED
st.markdown("<div id='Gap between release year and date added to catalog'></div>", unsafe_allow_html=True)
# --- 1. SAMPLE DATA SETUP (FIXED WITH GEOGRAPHY AND GENRES) ---
if "df_clean" not in locals():
    data = {
        "show_id": [f"s{i}" for i in range(1, 501)],
        "type": ["Movie", "Movie", "TV Show", "Movie", "TV Show"] * 100,
        "title": [f"Title {i}" for i in range(1, 501)],
        "release_year": [2018, 2019, 2020, 2021, 2015] * 100,
        "date_added": pd.to_datetime(
            ["2019-01-01", "2019-05-01", "2020-01-01", "2021-01-01", "2016-06-01"]
            * 100
        ),
        # ADDED: Essential columns to prevent downstream KeyErrors
        "country": ["United States", "India", "United Kingdom, United States", "Canada", "Japan"] * 100,
        "listed_in": ["Dramas, Independent Movies", "Comedies, International Movies", "Docuseries", "Children & Family Movies", "Anime Series, International TV"] * 100
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

# Plot all 4 lines together on the same horizontal axis
fig = px.line(
    df_timeline,
    x="Year",
    y="Count",
    color="Metric",
    title=f"Gap between Title Release Year and Date Added to Catalog ({start_year} - {end_year})",
    labels={"Year": "Year", "Count": "Total Titles"},
    # FIXED: Keys now exactly match the strings generated in the "Metric" column
    color_discrete_map={
        "Movies Added (Platform Year)": "#6495ED",       # Teal/Greenish
        "TV Shows Added (Platform Year)": "#DEB887",     # Light Green
        "Movies Released (Original Year)": "#4169E1",    # Orange
        "TV Shows Released (Original Year)": "#BD8B68"   # Yellow
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
st.markdown("1. Movie catalog dates lag release dates by minnimum of 2 years as seen from 2017 peak to 2019 peak.")
st.markdown("1.AI adds that Netflix usually buys the rights, putting Netflix at the end of the line of all licensees.")
st.markdown("2. However, TV Shows have almost no lag between release and catalog dates.")
# ------


# -------------------
st.markdown("<div id='Insights from Sequels and Seasons'></div>", unsafe_allow_html=True)
st.markdown("<h3>Insights from Sequels and Seasons</h3>", unsafe_allow_html=True)

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
            title=f"Top 5 Sequels ({start_year} - {end_year})",
            labels={"sequel_count": "No. of Sequels", "movie_count": "Total Movies"},
            color_discrete_sequence=["#6495ED"]  # cornflowerblue
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
            title=f"Top 5 Seasons ({start_year} - {end_year})",
            labels={"seasons": "Number of Seasons", "tv_show_count": "Total TV Show Count"},
            color_discrete_sequence=["#DEB887"]  # burlywood
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
# -------
# --- GENRE BY COUNTRY ANALYSIS (ENHANCED DISPLAY SIZE) ---
st.markdown("<div id='Genre by Top 10 Countries'></div>", unsafe_allow_html=True)
# Drop rows missing your target columns safely
df_geo = df_clean.dropna(subset=["countries", "genres"]).copy()

# 1. Unnest comma-separated strings into individual rows
df_geo_exploded = df_geo.assign(
    country_single=df_geo["countries"].astype(str).str.split(", "),
    genre_single=df_geo["genres"].astype(str).str.split(", ")
).explode("country_single").explode("genre_single")

# 2. Grab the Top 10 categories to keep the matrix clean and readable
top_countries = df_geo_exploded["country_single"].value_counts().nlargest(10).index
top_genres = df_geo_exploded["genre_single"].value_counts().nlargest(10).index

df_geo_filtered = df_geo_exploded[
    df_geo_exploded["country_single"].isin(top_countries) & 
    df_geo_exploded["genre_single"].isin(top_genres)
]

# 3. Create a Row-Normalized Contingency Table 
contingency_pct = pd.crosstab(
    df_geo_filtered["country_single"].values,  
    df_geo_filtered["genre_single"].values,    
    normalize="index"
) * 100

# 4. Plot the Plotly Heatmap with custom height sizing
fig_heatmap = px.imshow(
    contingency_pct,
    labels=dict(x="Genre", y="Country", color="Percentage (%)"),
    x=contingency_pct.columns,
    y=contingency_pct.index,
    color_continuous_scale="Blues",
    title="What Genres Do Top 10 Countries Focus On? (Normalized by Country)",
    text_auto=".1f",
    height=650,  # INCREASED: Forces the canvas height to be tall, enlarging individual squares
)

# 5. Fine-tune layout and margins to prevent label clipping
fig_heatmap.update_layout(
    xaxis_tickangle=-45,
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(autorange="reversed"),
    margin=dict(l=150, r=20, t=80, b=150)  # ADDED: Allocates extra pixel padding for country & genre labels
)

# Display the expanded interactive chart
st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("Key Observations:")
st.markdown("1. South Korea and Japan are top countries for International TV Shows")
st.markdown("2. India and Spain are top countries in International Movies")
st.markdown("3. U.S. has well diversified genres production")

# ------
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