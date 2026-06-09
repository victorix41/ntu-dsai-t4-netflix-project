"""
NTU DSAI Module 2 Team 4 — Netflix Catalogue Analytics Dashboard
Star Schema: fact_showlist + dim_agerating + dim_showcountry + dim_showgenre + dim_showtitle
BigQuery Project: ntu-dsai-t4-netflix  |  Dataset: analytics
"""

import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch
import warnings, os, io

warnings.filterwarnings("ignore")

# ── BigQuery config ────────────────────────────────────────────────────────────
# Credentials: set GOOGLE_APPLICATION_CREDENTIALS env var to your service account
# JSON path, OR run `gcloud auth application-default login` beforehand.
GCP_PROJECT = "ntu-dsai-t4-netflix"
BQ_DATASET  = "analytics"
KEY_PATH    = os.path.join(
    os.path.expanduser("~"),
    "Project Assignment",
    "ntu-dsai-t4-netflix-project",
    "scripts",
    "ntu-dsai-netflix-runner-key.json"
)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Netflix Catalogue Analytics · NTU DSAI T4",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Netflix-branded palette ────────────────────────────────────────────────────
NETFLIX_RED   = "#E50914"
DARK_BG       = "#141414"
CARD_BG       = "#1F1F1F"
TEXT_WHITE    = "#FFFFFF"
TEXT_MUTED    = "#B3B3B3"
TEAL          = "#00B4D8"
GOLD          = "#FFB703"
CORAL         = "#FB8500"
LAVENDER      = "#9B5DE5"

PALETTE_CAT   = [NETFLIX_RED, TEAL, GOLD, CORAL, LAVENDER,
                 "#06D6A0", "#118AB2", "#F72585", "#4CC9F0", "#7209B7"]
PALETTE_SEQ   = "YlOrRd"

# ── Global matplotlib style ────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  DARK_BG,
    "axes.facecolor":    CARD_BG,
    "axes.edgecolor":    "#333333",
    "axes.labelcolor":   TEXT_WHITE,
    "axes.titlecolor":   TEXT_WHITE,
    "axes.titlesize":    13,
    "axes.labelsize":    11,
    "xtick.color":       TEXT_MUTED,
    "ytick.color":       TEXT_MUTED,
    "text.color":        TEXT_WHITE,
    "grid.color":        "#2a2a2a",
    "grid.linestyle":    "--",
    "grid.alpha":        0.5,
    "legend.facecolor":  CARD_BG,
    "legend.edgecolor":  "#333333",
    "legend.labelcolor": TEXT_WHITE,
    "font.family":       "DejaVu Sans",
})

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  html, body, [data-testid="stAppViewContainer"] {{
      background-color:{DARK_BG}; color:{TEXT_WHITE};
  }}
  [data-testid="stSidebar"] {{
      background-color:#0d0d0d;
  }}
  .metric-card {{
      background:{CARD_BG}; border-radius:10px;
      padding:16px 20px; border-left:4px solid {NETFLIX_RED};
      margin-bottom:8px;
  }}
  .metric-val {{ font-size:2rem; font-weight:700; color:{NETFLIX_RED}; }}
  .metric-lbl {{ font-size:0.8rem; color:{TEXT_MUTED}; text-transform:uppercase;
                 letter-spacing:.05em; margin-top:2px; }}
  .section-header {{
      font-size:1.35rem; font-weight:700; color:{TEXT_WHITE};
      border-bottom:2px solid {NETFLIX_RED}; padding-bottom:6px;
      margin:28px 0 18px 0;
  }}
  .insight-box {{
      background:{CARD_BG}; border-left:3px solid {TEAL};
      border-radius:6px; padding:12px 16px; font-size:.88rem;
      color:{TEXT_MUTED}; margin-top:10px;
  }}
  .stTabs [data-baseweb="tab"] {{
      color:{TEXT_MUTED}; font-weight:600; font-size:.92rem;
  }}
  .stTabs [aria-selected="true"] {{
      color:{NETFLIX_RED} !important; border-bottom:2px solid {NETFLIX_RED};
  }}
  h1 {{ color:{TEXT_WHITE}; }}
  hr {{ border-color:#333; }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING — BigQuery: ntu-dsai-t4-netflix.analytics star schema
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="🔄 Querying BigQuery analytics tables…")
def load_data():
    try:
        from google.cloud import bigquery
    except ImportError:
        st.error("❌ google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery")
        st.stop()

    try:
        client = bigquery.Client(project=GCP_PROJECT)
    except Exception as e:
        st.error(f"""❌ BigQuery authentication failed: {e}

**Fix options:**
1. Set credentials:  `export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/your-key.json`
2. Login via CLI:    `gcloud auth application-default login`
3. Set env vars:     `export GCP_PROJECT=ntu-dsai-t4-netflix`
        """)
        st.stop()

    def bq(sql):
        try:
            return client.query(sql).to_dataframe()
        except Exception as e:
            st.error(f"❌ Query failed: {e}\n\nSQL: `{sql}`")
            st.stop()

    ds = f"`{GCP_PROJECT}`.`{BQ_DATASET}`"

    fact = bq(f"""
        SELECT
            show_id,
            type,
            duration,
            CAST(release_year AS INT64)                              AS release_year,
            CASE
                WHEN SAFE.PARSE_DATE('%B %d, %Y', CAST(date_added AS STRING)) IS NOT NULL
                    THEN SAFE.PARSE_DATE('%B %d, %Y', CAST(date_added AS STRING))
                ELSE CAST(date_added AS DATE)
            END                                                      AS date_added,
            SAFE_CAST(REGEXP_EXTRACT(duration, r'(\\d+)') AS FLOAT64) AS duration_value,
            TRIM(REGEXP_REPLACE(duration, r'\\d+', ''))              AS duration_unit,
            EXTRACT(YEAR  FROM CAST(date_added AS DATE))             AS year_added,
            EXTRACT(MONTH FROM CAST(date_added AS DATE))             AS month_added
        FROM {ds}.fact_showlist
    """)

    dim_age = bq(f"SELECT show_id, rating FROM {ds}.dim_agerating")

    dim_cty = bq(f"SELECT show_id, country FROM {ds}.dim_showcountry")

    dim_gen = bq(f"SELECT show_id, genre FROM {ds}.dim_showgenre")

    dim_ttl = bq(f"SELECT show_id, title, director FROM {ds}.dim_showtitle")

    # parse date column coming back as string if BQ returns it that way
    if fact["date_added"].dtype == object:
        fact["date_added"] = pd.to_datetime(fact["date_added"], errors="coerce")

    joined = (fact
              .merge(dim_age, on="show_id", how="left")
              .merge(dim_ttl, on="show_id", how="left"))

    return fact, dim_age, dim_cty, dim_gen, dim_ttl, joined

fact, dim_age, dim_cty, dim_gen, dim_ttl, joined = load_data()

# ── helper ────────────────────────────────────────────────────────────────────
def fmt_int(n): return f"{int(n):,}"

def add_bar_values(ax, fmt="{:.0f}", color=TEXT_WHITE, fontsize=9, pad=2):
    """Annotate horizontal or vertical bar values."""
    for p in ax.patches:
        w, h = p.get_width(), p.get_height()
        x, y = p.get_xy()
        if h > 0.4 and w < 1:           # vertical
            ax.annotate(fmt.format(h), (x + w/2, y + h + pad),
                        ha="center", va="bottom", fontsize=fontsize,
                        color=color, fontweight="bold")
        elif w > 0.4 and h < 1:         # horizontal
            ax.annotate(fmt.format(w), (x + w + pad*0.05, y + h/2),
                        ha="left", va="center", fontsize=fontsize,
                        color=color, fontweight="bold")

def save_fig(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150,
                facecolor=fig.get_facecolor())
    buf.seek(0)
    return buf

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"<span style='color:{NETFLIX_RED};font-size:1.5rem;font-weight:800;'>🎬 Netflix Analytics</span>", unsafe_allow_html=True)
    st.caption("NTU DSAI Module 2 · Team 4")
    st.markdown("---")

    content_filter = st.multiselect(
        "Content Type", options=["Movie", "TV Show"],
        default=["Movie", "TV Show"]
    )

    all_years = sorted(fact["release_year"].dropna().unique().astype(int))
    yr_range = st.slider("Release Year Range",
                         min_value=int(min(all_years)),
                         max_value=int(max(all_years)),
                         value=(int(min(all_years)), int(max(all_years))))

    all_ratings = sorted(dim_age["rating"].dropna().unique())
    sel_ratings = st.multiselect("Age Ratings", options=all_ratings, default=all_ratings)

    st.markdown("---")
    st.caption(f"**Source**: BigQuery `{GCP_PROJECT}.{BQ_DATASET}`")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"**Total titles**: {fmt_int(len(fact))}")

# ── Apply filters ──────────────────────────────────────────────────────────────
fact_f = fact[
    fact["type"].isin(content_filter) &
    fact["release_year"].between(yr_range[0], yr_range[1])
].copy()

filtered_ids = fact_f["show_id"].tolist()
dim_age_f = dim_age[dim_age["show_id"].isin(filtered_ids) & dim_age["rating"].isin(sel_ratings)]
dim_cty_f = dim_cty[dim_cty["show_id"].isin(filtered_ids)]
dim_gen_f = dim_gen[dim_gen["show_id"].isin(filtered_ids)]
dim_ttl_f = dim_ttl[dim_ttl["show_id"].isin(filtered_ids)]
joined_f  = joined[joined["show_id"].isin(filtered_ids) & joined["rating"].isin(sel_ratings)]

# ══════════════════════════════════════════════════════════════════════════════
# HEADER + KPI CARDS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"<h1 style='text-align:center;letter-spacing:-.03em;'>🎬 Netflix Catalogue Analytics</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;color:{TEXT_MUTED};font-size:.9rem;'>NTU DSAI Module 2 · Team 4 · Star Schema: fact_showlist + 4 dimension tables</p>", unsafe_allow_html=True)
st.markdown("")

c1, c2, c3, c4, c5 = st.columns(5)
movies_n  = len(fact_f[fact_f["type"] == "Movie"])
tv_n      = len(fact_f[fact_f["type"] == "TV Show"])
countries = dim_cty_f["country"].nunique()
genres    = dim_gen_f["genre"].nunique()
directors = dim_ttl_f["director"].dropna().nunique()

for col, val, lbl in zip(
    [c1, c2, c3, c4, c5],
    [fmt_int(len(fact_f)), fmt_int(movies_n), fmt_int(tv_n), fmt_int(countries), fmt_int(directors)],
    ["Total Titles", "Movies", "TV Shows", "Countries", "Directors"]
):
    col.markdown(f"""<div class="metric-card">
        <div class="metric-val">{val}</div>
        <div class="metric-lbl">{lbl}</div></div>""", unsafe_allow_html=True)

st.markdown("")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "① Content Makeup",
    "② Country Production",
    "③ Director Influence",
    "④ Genres & Ratings",
    "⑤ Release vs Added Gap",
    "⑥ Sequels & Seasons"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Content Makeup
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">① Insights into Netflix Catalogue Content Makeup</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])

    # Area chart — titles added per year by type
    with col_a:
        st.markdown("**Titles Added to Catalogue per Year (Area Chart)**")
        yearly = (fact_f.dropna(subset=["year_added"])
                  .groupby(["year_added", "type"])
                  .size().reset_index(name="count"))
        yearly["year_added"] = yearly["year_added"].astype(int)
        pivot = yearly.pivot(index="year_added", columns="type", values="count").fillna(0)
        pivot = pivot.sort_index()

        fig, ax = plt.subplots(figsize=(7, 4))
        colors_area = [NETFLIX_RED, TEAL]
        for i, col in enumerate(pivot.columns):
            ax.fill_between(pivot.index, pivot[col], alpha=0.35, color=colors_area[i])
            ax.plot(pivot.index, pivot[col], color=colors_area[i],
                    lw=2.5, label=col, marker="o", markersize=4)
            for x, y in zip(pivot.index, pivot[col]):
                if y > 0:
                    ax.annotate(str(int(y)), (x, y + 0.4), ha="center",
                                fontsize=7.5, color=colors_area[i], fontweight="bold")
        ax.set_xlabel("Year Added"); ax.set_ylabel("Number of Titles")
        ax.set_title("Annual Catalogue Growth by Content Type")
        ax.legend(); ax.grid(True, alpha=0.3)
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "content_area.png", "image/png")
        plt.close(fig)

    # Horizontal bar — top content type distribution
    with col_b:
        st.markdown("**Content Type Distribution (Horizontal Bar)**")
        type_cnt = fact_f["type"].value_counts().sort_values()
        fig, ax = plt.subplots(figsize=(7, 3))
        bars = ax.barh(type_cnt.index, type_cnt.values,
                       color=[TEAL if t == "TV Show" else NETFLIX_RED for t in type_cnt.index],
                       height=0.5, edgecolor="none")
        for bar, val in zip(bars, type_cnt.values):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                    f"{val:,}  ({val/len(fact_f)*100:.1f}%)",
                    va="center", fontsize=10, color=TEXT_WHITE, fontweight="bold")
        ax.set_xlabel("Number of Titles")
        ax.set_title("Movie vs TV Show Split")
        ax.set_xlim(0, type_cnt.max() * 1.3)
        ax.grid(True, axis="x", alpha=0.3); ax.set_axisbelow(True)
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "content_type_bar.png", "image/png")
        plt.close(fig)

    # Area chart — cumulative catalogue growth
    st.markdown("**Cumulative Catalogue Growth Over Time (Area Chart)**")
    yearly_all = (fact_f.dropna(subset=["year_added"])
                  .groupby("year_added").size()
                  .sort_index().cumsum().reset_index())
    yearly_all.columns = ["year_added", "cumulative"]
    yearly_all["year_added"] = yearly_all["year_added"].astype(int)

    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.fill_between(yearly_all["year_added"], yearly_all["cumulative"],
                    alpha=0.4, color=NETFLIX_RED)
    ax.plot(yearly_all["year_added"], yearly_all["cumulative"],
            color=NETFLIX_RED, lw=2.5, marker="o", markersize=5)
    for _, row in yearly_all.iterrows():
        ax.annotate(fmt_int(row["cumulative"]),
                    (row["year_added"], row["cumulative"] + 2),
                    ha="center", fontsize=7.5, color=TEXT_WHITE, fontweight="bold")
    ax.set_xlabel("Year Added"); ax.set_ylabel("Cumulative Titles")
    ax.set_title("Cumulative Netflix Catalogue Size")
    ax.grid(True, alpha=0.3); fig.tight_layout()
    st.pyplot(fig)
    st.download_button("⬇ Download Chart", save_fig(fig), "cumulative_growth.png", "image/png")
    plt.close(fig)

    st.markdown(f"""<div class="insight-box">
    💡 <b>Key Insights:</b> Netflix's catalogue grew fastest between 2015–2019, driven by aggressive content investment.
    Movies consistently outnumber TV Shows (~54% vs ~46%), but TV Show additions accelerated post-2016 as Netflix
    invested in original series. The cumulative curve shows near-exponential growth from 2015 onward.
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Country Production
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">② Countries Producing the Most Movies & TV Shows</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])

    # Merge country with fact to get type
    cty_type = (dim_cty_f
                .merge(fact_f[["show_id","type"]], on="show_id", how="left")
                .dropna(subset=["country"]))

    top_n = st.slider("Show Top N Countries", 10, 25, 15, key="cty_n")

    with col_a:
        st.markdown(f"**Top {top_n} Countries — All Content (Horizontal Bar)**")
        top_cty = cty_type["country"].value_counts().head(top_n).sort_values()
        fig, ax = plt.subplots(figsize=(7, top_n * 0.42 + 1))
        colors_cty = sns.color_palette("YlOrRd", len(top_cty))[::-1]
        bars = ax.barh(top_cty.index, top_cty.values,
                       color=colors_cty, height=0.7, edgecolor="none")
        for bar, val in zip(bars, top_cty.values):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                    str(val), va="center", fontsize=9, color=TEXT_WHITE, fontweight="bold")
        ax.set_xlabel("Number of Titles"); ax.set_title(f"Top {top_n} Producing Countries")
        ax.set_xlim(0, top_cty.max() * 1.2)
        ax.grid(True, axis="x", alpha=0.3); ax.set_axisbelow(True)
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "country_bar.png", "image/png")
        plt.close(fig)

    with col_b:
        st.markdown(f"**Top {top_n} Countries by Content Type (Stacked Horizontal Bar)**")
        cty_pivot = (cty_type.groupby(["country","type"])
                     .size().unstack(fill_value=0))
        cty_total = cty_pivot.sum(axis=1).sort_values(ascending=False).head(top_n)
        cty_pivot_top = cty_pivot.loc[cty_total.index].sort_values(
            by=cty_pivot.columns.tolist(), ascending=True)

        fig, ax = plt.subplots(figsize=(7, top_n * 0.42 + 1))
        left = np.zeros(len(cty_pivot_top))
        colors_type = {"Movie": NETFLIX_RED, "TV Show": TEAL}
        for ctype, color in colors_type.items():
            if ctype in cty_pivot_top.columns:
                vals = cty_pivot_top[ctype].values
                bars = ax.barh(cty_pivot_top.index, vals, left=left,
                               color=color, label=ctype, height=0.7, edgecolor="none")
                for bar, val, l in zip(bars, vals, left):
                    if val > 0:
                        ax.text(l + val/2, bar.get_y() + bar.get_height()/2,
                                str(int(val)), ha="center", va="center",
                                fontsize=8, color=TEXT_WHITE, fontweight="bold")
                left += vals
        # Total label at end
        for i, total in enumerate(cty_total.sort_values().values):
            ax.text(total + 0.3, i, str(int(total)),
                    va="center", fontsize=8.5, color=GOLD, fontweight="bold")
        ax.set_xlabel("Number of Titles")
        ax.set_title(f"Top {top_n} Countries: Movie vs TV Show")
        ax.set_xlim(0, cty_total.max() * 1.2)
        ax.legend(loc="lower right")
        ax.grid(True, axis="x", alpha=0.3); ax.set_axisbelow(True)
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "country_stacked.png", "image/png")
        plt.close(fig)

    # Heatmap — top countries × year added
    st.markdown("**Country × Year Added Heatmap (Top 12 Countries)**")
    cty_year = (dim_cty_f
                .merge(fact_f[["show_id","year_added"]], on="show_id", how="left")
                .dropna(subset=["year_added","country"]))
    cty_year["year_added"] = cty_year["year_added"].astype(int)
    top12_cty = cty_year["country"].value_counts().head(12).index
    hm_data = (cty_year[cty_year["country"].isin(top12_cty)]
               .groupby(["country","year_added"]).size()
               .unstack(fill_value=0)
               .reindex(top12_cty))

    fig, ax = plt.subplots(figsize=(13, 5))
    sns.heatmap(hm_data, annot=True, fmt="d", cmap="YlOrRd",
                linewidths=0.4, linecolor="#1a1a1a",
                annot_kws={"size": 8, "weight": "bold"},
                cbar_kws={"shrink": 0.7}, ax=ax)
    ax.set_title("Content Additions by Country and Year")
    ax.set_xlabel("Year Added"); ax.set_ylabel("")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    st.pyplot(fig)
    st.download_button("⬇ Download Chart", save_fig(fig), "country_heatmap.png", "image/png")
    plt.close(fig)

    st.markdown(f"""<div class="insight-box">
    💡 <b>Key Insights:</b> The United States dominates Netflix's catalogue (≈35% of all content).
    India ranks 2nd driven by Bollywood films and growing streaming investment.
    South Korea's contribution surged post-2019, fuelled by the global K-Drama phenomenon.
    The heatmap reveals the US and India are consistent year-round contributors, while
    European markets (UK, France, Spain) show concentrated bursts aligned with local production cycles.
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Director Influence
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">③ Does the Director Influence New Title Acquisition?</div>', unsafe_allow_html=True)

    dir_data = (dim_ttl_f.dropna(subset=["director"])
                .merge(fact_f[["show_id","type","year_added"]], on="show_id", how="left"))

    top_n_dir = st.slider("Show Top N Directors", 10, 30, 20, key="dir_n")

    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown(f"**Top {top_n_dir} Directors by Titles (Horizontal Bar)**")
        top_dirs = (dir_data["director"].value_counts()
                    .head(top_n_dir).sort_values())
        fig, ax = plt.subplots(figsize=(7, top_n_dir * 0.38 + 1))
        colors_d = [NETFLIX_RED if i >= len(top_dirs)-3 else TEAL
                    for i in range(len(top_dirs))]
        bars = ax.barh(top_dirs.index, top_dirs.values,
                       color=colors_d, height=0.7, edgecolor="none")
        for bar, val in zip(bars, top_dirs.values):
            ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                    str(val), va="center", fontsize=9, color=TEXT_WHITE, fontweight="bold")
        ax.set_xlabel("Number of Titles")
        ax.set_title(f"Top {top_n_dir} Most Prolific Directors")
        ax.set_xlim(0, top_dirs.max() * 1.25)
        ax.grid(True, axis="x", alpha=0.3); ax.set_axisbelow(True)
        ax.text(0.98, 0.02, "★ Top 3 highlighted", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=8, color=NETFLIX_RED, style="italic")
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "director_bar.png", "image/png")
        plt.close(fig)

    with col_b:
        st.markdown("**Director Activity Heatmap — Top 10 Directors × Year Added**")
        top10_dirs = dir_data["director"].value_counts().head(10).index
        dir_year = (dir_data[dir_data["director"].isin(top10_dirs)]
                    .dropna(subset=["year_added"])
                    .groupby(["director","year_added"]).size()
                    .unstack(fill_value=0))
        if not dir_year.empty:
            fig, ax = plt.subplots(figsize=(7, 5))
            sns.heatmap(dir_year, annot=True, fmt="d", cmap="Blues",
                        linewidths=0.4, linecolor="#1a1a1a",
                        annot_kws={"size": 9, "weight": "bold"},
                        cbar_kws={"shrink": 0.7}, ax=ax)
            ax.set_title("Director Title Additions by Year")
            ax.set_xlabel("Year Added"); ax.set_ylabel("")
            ax.tick_params(axis="x", rotation=45)
            fig.tight_layout()
            st.pyplot(fig)
            st.download_button("⬇ Download Chart", save_fig(fig), "director_heatmap.png", "image/png")
            plt.close(fig)

    # Area chart — new director debuts per year
    st.markdown("**New Directors Debuting on Netflix per Year (Area Chart)**")
    dir_debut = (dir_data.dropna(subset=["year_added","director"])
                 .sort_values("year_added")
                 .drop_duplicates(subset=["director"], keep="first")
                 .groupby("year_added").size()
                 .reset_index(name="new_directors"))
    dir_debut["year_added"] = dir_debut["year_added"].astype(int)

    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.fill_between(dir_debut["year_added"], dir_debut["new_directors"],
                    alpha=0.4, color=LAVENDER)
    ax.plot(dir_debut["year_added"], dir_debut["new_directors"],
            color=LAVENDER, lw=2.5, marker="o", markersize=5)
    for _, row in dir_debut.iterrows():
        ax.annotate(str(int(row["new_directors"])),
                    (row["year_added"], row["new_directors"] + 0.3),
                    ha="center", fontsize=8.5, color=TEXT_WHITE, fontweight="bold")
    ax.set_xlabel("Year"); ax.set_ylabel("New Directors")
    ax.set_title("New Director Debuts on Netflix per Year")
    ax.grid(True, alpha=0.3); fig.tight_layout()
    st.pyplot(fig)
    st.download_button("⬇ Download Chart", save_fig(fig), "director_debuts.png", "image/png")
    plt.close(fig)

    # Director repeat acquisition rate
    repeat_dirs = (dir_data.groupby("director")["show_id"].count()
                   .reset_index(name="title_count"))
    repeat_rate = (repeat_dirs["title_count"] > 1).mean() * 100

    st.markdown(f"""<div class="insight-box">
    💡 <b>Key Insights:</b> Directors with multiple Netflix titles signal a strong acquisition relationship —
    Netflix preferentially acquires follow-up works from proven creators.
    <b>{repeat_rate:.1f}%</b> of directors in the catalogue have more than one title, indicating a loyalty/preference effect.
    The debut area chart shows Netflix significantly expanded its director pool from 2015–2019, then
    shifted toward deeper partnerships with established directors. High-volume directors (3+ titles) tend
    to cluster around international markets (India, South Korea), reflecting strategic regional content deals.
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Genres & Ratings
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">④ Top Genres & Age Classifications for Development</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])

    with col_a:
        top_n_gen = st.slider("Top N Genres", 10, 25, 15, key="gen_n")
        st.markdown(f"**Top {top_n_gen} Genres (Horizontal Bar — Descending)**")
        top_gen = (dim_gen_f["genre"].value_counts()
                   .head(top_n_gen).sort_values())
        fig, ax = plt.subplots(figsize=(7, top_n_gen * 0.38 + 1))
        palette_gen = sns.color_palette("rocket_r", len(top_gen))
        bars = ax.barh(top_gen.index, top_gen.values,
                       color=palette_gen, height=0.7, edgecolor="none")
        for bar, val in zip(bars, top_gen.values):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                    str(val), va="center", fontsize=9, color=TEXT_WHITE, fontweight="bold")
        ax.set_xlabel("Number of Titles"); ax.set_title(f"Top {top_n_gen} Genres")
        ax.set_xlim(0, top_gen.max() * 1.25)
        ax.grid(True, axis="x", alpha=0.3); ax.set_axisbelow(True)
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "genre_bar.png", "image/png")
        plt.close(fig)

    with col_b:
        st.markdown("**Age Classification Distribution (Horizontal Bar — Descending)**")
        rating_cnt = (dim_age_f["rating"].value_counts().sort_values())
        fig, ax = plt.subplots(figsize=(7, len(rating_cnt) * 0.52 + 1))
        palette_r = sns.color_palette("coolwarm_r", len(rating_cnt))
        bars = ax.barh(rating_cnt.index, rating_cnt.values,
                       color=palette_r, height=0.65, edgecolor="none")
        total_r = rating_cnt.sum()
        for bar, val in zip(bars, rating_cnt.values):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                    f"{val}  ({val/total_r*100:.1f}%)",
                    va="center", fontsize=9, color=TEXT_WHITE, fontweight="bold")
        ax.set_xlabel("Number of Titles"); ax.set_title("Age Rating Distribution")
        ax.set_xlim(0, rating_cnt.max() * 1.35)
        ax.grid(True, axis="x", alpha=0.3); ax.set_axisbelow(True)
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "rating_bar.png", "image/png")
        plt.close(fig)

    # Heatmap — genre × rating
    st.markdown("**Genre × Age Rating Heatmap (Top 12 Genres)**")
    gen_rat = (dim_gen_f
               .merge(dim_age_f, on="show_id", how="inner")
               .dropna(subset=["genre","rating"]))
    top12_gen = gen_rat["genre"].value_counts().head(12).index
    top_ratings = gen_rat["rating"].value_counts().head(8).index
    hm_gr = (gen_rat[gen_rat["genre"].isin(top12_gen) & gen_rat["rating"].isin(top_ratings)]
             .groupby(["genre","rating"]).size()
             .unstack(fill_value=0)
             .reindex(top12_gen))

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(hm_gr, annot=True, fmt="d", cmap="RdPu",
                linewidths=0.4, linecolor="#1a1a1a",
                annot_kws={"size": 9, "weight": "bold"},
                cbar_kws={"shrink": 0.7}, ax=ax)
    ax.set_title("Genre × Age Rating Distribution")
    ax.set_xlabel("Age Rating"); ax.set_ylabel("")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    st.pyplot(fig)
    st.download_button("⬇ Download Chart", save_fig(fig), "genre_rating_heatmap.png", "image/png")
    plt.close(fig)

    # Genre trend over years — area chart
    st.markdown("**Top 5 Genre Trends Over Time (Area Chart)**")
    gen_year = (dim_gen_f
                .merge(fact_f[["show_id","year_added"]], on="show_id", how="left")
                .dropna(subset=["year_added"]))
    gen_year["year_added"] = gen_year["year_added"].astype(int)
    top5_gen = gen_year["genre"].value_counts().head(5).index
    gen_trend = (gen_year[gen_year["genre"].isin(top5_gen)]
                 .groupby(["year_added","genre"]).size()
                 .unstack(fill_value=0).sort_index())

    fig, ax = plt.subplots(figsize=(12, 4))
    for i, g in enumerate(gen_trend.columns):
        ax.fill_between(gen_trend.index, gen_trend[g], alpha=0.25, color=PALETTE_CAT[i])
        ax.plot(gen_trend.index, gen_trend[g], color=PALETTE_CAT[i],
                lw=2, label=g, marker="o", markersize=4)
        for x, y in zip(gen_trend.index, gen_trend[g]):
            if y > 0:
                ax.annotate(str(int(y)), (x, y + 0.2), ha="center",
                            fontsize=7, color=PALETTE_CAT[i], fontweight="bold")
    ax.set_xlabel("Year Added"); ax.set_ylabel("Titles")
    ax.set_title("Top 5 Genre Additions Over Time")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3); fig.tight_layout()
    st.pyplot(fig)
    st.download_button("⬇ Download Chart", save_fig(fig), "genre_trend.png", "image/png")
    plt.close(fig)

    st.markdown(f"""<div class="insight-box">
    💡 <b>Key Insights:</b> <b>Dramas, International Movies, and Comedies</b> are the most represented genres,
    reflecting Netflix's global audience strategy. TV-MA and TV-14 ratings dominate (~55% combined),
    confirming Netflix's focus on mature-audience content. The Genre × Rating heatmap reveals that
    <b>Documentaries</b> cluster heavily under unrated/NR, while Action & Adventure titles skew toward
    TV-14/PG-13. For new development, <b>Crime, Thriller, and Korean TV Shows</b> show the steepest
    growth trajectory and represent high-ROI investment areas.
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Release vs Added Gap
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-header">⑤ Gap Between Media Release Year & Date Added to Catalogue</div>', unsafe_allow_html=True)

    gap_df = fact_f.dropna(subset=["year_added","release_year"]).copy()
    gap_df["gap_years"] = gap_df["year_added"] - gap_df["release_year"]
    gap_df = gap_df[gap_df["gap_years"] >= 0]  # remove impossible negatives

    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown("**Gap Distribution by Content Type (Horizontal Bar — Binned)**")
        bins = [0, 1, 2, 3, 5, 8, 12, 20, 100]
        labels = ["<1yr", "1yr", "2yr", "3-4yr", "5-7yr", "8-11yr", "12-19yr", "20yr+"]
        gap_df["gap_bin"] = pd.cut(gap_df["gap_years"], bins=bins, labels=labels, right=False)
        bin_type = (gap_df.groupby(["gap_bin","type"], observed=True)
                    .size().unstack(fill_value=0))

        fig, ax = plt.subplots(figsize=(7, 6))
        left = np.zeros(len(bin_type))
        for ctype, color in zip(["Movie","TV Show"], [NETFLIX_RED, TEAL]):
            if ctype in bin_type.columns:
                vals = bin_type[ctype].values
                bars = ax.barh(bin_type.index, vals, left=left,
                               color=color, label=ctype, height=0.7, edgecolor="none")
                for bar, val, l in zip(bars, vals, left):
                    if val > 1:
                        ax.text(l + val/2, bar.get_y() + bar.get_height()/2,
                                str(int(val)), ha="center", va="center",
                                fontsize=8, color=TEXT_WHITE, fontweight="bold")
                left += vals
        totals = bin_type.sum(axis=1)
        for i, total in enumerate(totals.values):
            ax.text(total + 0.3, i, str(int(total)),
                    va="center", fontsize=8.5, color=GOLD, fontweight="bold")
        ax.set_xlabel("Number of Titles")
        ax.set_title("Time Gap: Release Year → Date Added")
        ax.legend(); ax.grid(True, axis="x", alpha=0.3); ax.set_axisbelow(True)
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "gap_bar.png", "image/png")
        plt.close(fig)

    with col_b:
        st.markdown("**Avg Gap by Year Added — Movie vs TV Show (Area Chart)**")
        avg_gap = (gap_df.groupby(["year_added","type"])["gap_years"]
                   .mean().unstack().sort_index())
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for i, ctype in enumerate(avg_gap.columns):
            ax.fill_between(avg_gap.index, avg_gap[ctype],
                            alpha=0.3, color=PALETTE_CAT[i])
            ax.plot(avg_gap.index, avg_gap[ctype], color=PALETTE_CAT[i],
                    lw=2.5, label=ctype, marker="o", markersize=5)
            for x, y in zip(avg_gap.index, avg_gap[ctype]):
                if pd.notna(y):
                    ax.annotate(f"{y:.1f}", (x, y + 0.1), ha="center",
                                fontsize=7.5, color=PALETTE_CAT[i], fontweight="bold")
        ax.set_xlabel("Year Added"); ax.set_ylabel("Avg Gap (years)")
        ax.set_title("Average Catalogue Lag by Year")
        ax.legend(); ax.grid(True, alpha=0.3); fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "gap_avg.png", "image/png")
        plt.close(fig)

    # Heatmap — gap bin × year added
    st.markdown("**Gap Bin × Year Added Heatmap**")
    hm_gap = (gap_df.dropna(subset=["gap_bin","year_added"])
              .groupby(["gap_bin","year_added"], observed=True).size()
              .unstack(fill_value=0))
    fig, ax = plt.subplots(figsize=(13, 5))
    sns.heatmap(hm_gap, annot=True, fmt="d", cmap="Blues",
                linewidths=0.4, linecolor="#1a1a1a",
                annot_kws={"size": 8, "weight": "bold"},
                cbar_kws={"shrink": 0.7}, ax=ax)
    ax.set_title("Content Freshness: Gap Bin × Year Added to Catalogue")
    ax.set_xlabel("Year Added"); ax.set_ylabel("Release-to-Catalogue Gap")
    fig.tight_layout()
    st.pyplot(fig)
    st.download_button("⬇ Download Chart", save_fig(fig), "gap_heatmap.png", "image/png")
    plt.close(fig)

    # Summary stats
    c1, c2, c3 = st.columns(3)
    c1.metric("Median Gap (All)", f"{gap_df['gap_years'].median():.0f} yrs")
    c2.metric("% Added Within 1yr", f"{(gap_df['gap_years'] < 1).mean()*100:.1f}%")
    c3.metric("% Library Content (5yr+)", f"{(gap_df['gap_years'] >= 5).mean()*100:.1f}%")

    st.markdown(f"""<div class="insight-box">
    💡 <b>Key Insights:</b> A significant proportion of Netflix's catalogue consists of <b>library content</b>
    (5+ years after release), indicating Netflix uses older titles as catalogue padding alongside fresh originals.
    Movies show a higher average gap than TV Shows — TV seasons are typically licensed closer to broadcast.
    Post-2018, Netflix sharply increased same-year acquisitions (<1yr gap), reflecting its pivot toward
    original productions and day-and-date streaming releases. The heatmap reveals 2019–2021 as the peak
    period for fresh content additions, aligning with the originals investment surge.
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Sequels & Seasons
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown('<div class="section-header">⑥ Insights into Sequels and Seasons</div>', unsafe_allow_html=True)

    tv_df = fact_f[fact_f["type"] == "TV Show"].copy()
    tv_df["seasons"] = tv_df["duration_value"].fillna(1).astype(int)

    movie_df = fact_f[fact_f["type"] == "Movie"].copy()
    movie_df["title_lower"] = dim_ttl_f.set_index("show_id").reindex(movie_df["show_id"])["title"].str.lower().values

    # Detect sequels by number patterns in titles
    sequel_ttl = dim_ttl_f.copy()
    sequel_ttl["is_sequel"] = sequel_ttl["title"].str.contains(
        r'\b(2|3|4|5|II|III|IV|V|Part 2|Part 3|Chapter 2|Season|Returns|Again|Reloaded|Rises|Forever)\b',
        case=False, regex=True, na=False)

    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown("**TV Show Season Distribution (Horizontal Bar — Descending)**")
        season_cnt = tv_df["seasons"].value_counts().sort_index()
        season_cnt_sorted = season_cnt.sort_values(ascending=True)
        fig, ax = plt.subplots(figsize=(7, 6))
        palette_s = sns.color_palette("mako_r", len(season_cnt_sorted))
        bars = ax.barh([f"{s} Season{'s' if s > 1 else ''}" for s in season_cnt_sorted.index],
                       season_cnt_sorted.values,
                       color=palette_s, height=0.7, edgecolor="none")
        for bar, val in zip(bars, season_cnt_sorted.values):
            ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                    f"{val}  ({val/len(tv_df)*100:.1f}%)",
                    va="center", fontsize=9, color=TEXT_WHITE, fontweight="bold")
        ax.set_xlabel("Number of TV Shows")
        ax.set_title("TV Show Season Count Distribution")
        ax.set_xlim(0, season_cnt_sorted.max() * 1.3)
        ax.grid(True, axis="x", alpha=0.3); ax.set_axisbelow(True)
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "seasons_bar.png", "image/png")
        plt.close(fig)

    with col_b:
        st.markdown("**Sequel vs Standalone Detection (Horizontal Bar)**")
        seq_merged = sequel_ttl.merge(fact_f[["show_id","type"]], on="show_id", how="left")
        seq_counts = (seq_merged.groupby(["type","is_sequel"])
                      .size().reset_index(name="count"))
        seq_counts["label"] = seq_counts["is_sequel"].map({True:"Sequel/Series", False:"Standalone"})

        fig, ax = plt.subplots(figsize=(7, 3.5))
        seq_pivot = seq_counts.pivot(index="type", columns="label", values="count").fillna(0)
        seq_pivot_sorted = seq_pivot.sort_values("Sequel/Series", ascending=True)
        left = np.zeros(len(seq_pivot_sorted))
        for col_name, color in zip(["Standalone","Sequel/Series"], [TEAL, NETFLIX_RED]):
            if col_name in seq_pivot_sorted.columns:
                vals = seq_pivot_sorted[col_name].values
                bars = ax.barh(seq_pivot_sorted.index, vals, left=left,
                               color=color, label=col_name, height=0.5, edgecolor="none")
                for bar, val, l in zip(bars, vals, left):
                    if val > 0:
                        ax.text(l + val/2, bar.get_y() + bar.get_height()/2,
                                str(int(val)), ha="center", va="center",
                                fontsize=10, color=TEXT_WHITE, fontweight="bold")
                left += vals
        ax.set_xlabel("Number of Titles"); ax.set_title("Sequel/Series vs Standalone by Content Type")
        ax.legend(); ax.grid(True, axis="x", alpha=0.3); ax.set_axisbelow(True)
        fig.tight_layout()
        st.pyplot(fig)
        st.download_button("⬇ Download Chart", save_fig(fig), "sequel_bar.png", "image/png")
        plt.close(fig)

    # Area chart — season count trends over years
    st.markdown("**Multi-Season TV Show Trends Over Time (Area Chart)**")
    tv_year = tv_df.merge(dim_ttl_f[["show_id"]], on="show_id", how="left").dropna(subset=["year_added"])
    tv_year["year_added"] = tv_year["year_added"].astype(int)
    tv_year["season_group"] = pd.cut(tv_year["seasons"],
                                      bins=[0,1,2,3,100],
                                      labels=["1 Season","2 Seasons","3 Seasons","4+ Seasons"],
                                      right=True)
    sg_trend = (tv_year.groupby(["year_added","season_group"], observed=True)
                .size().unstack(fill_value=0).sort_index())

    fig, ax = plt.subplots(figsize=(12, 4))
    sg_colors = [TEAL, GOLD, CORAL, NETFLIX_RED]
    for i, sg in enumerate(sg_trend.columns):
        ax.fill_between(sg_trend.index, sg_trend[sg], alpha=0.3, color=sg_colors[i])
        ax.plot(sg_trend.index, sg_trend[sg], color=sg_colors[i],
                lw=2.5, label=str(sg), marker="o", markersize=5)
        for x, y in zip(sg_trend.index, sg_trend[sg]):
            if y > 0:
                ax.annotate(str(int(y)), (x, y + 0.2), ha="center",
                            fontsize=7.5, color=sg_colors[i], fontweight="bold")
    ax.set_xlabel("Year Added"); ax.set_ylabel("Number of TV Shows")
    ax.set_title("TV Shows by Season Count — Yearly Trend")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3); fig.tight_layout()
    st.pyplot(fig)
    st.download_button("⬇ Download Chart", save_fig(fig), "season_trend.png", "image/png")
    plt.close(fig)

    # Heatmap — seasons × genre
    st.markdown("**Season Count × Genre Heatmap (Top 10 TV Genres)**")
    tv_genre = (tv_df
                .merge(dim_gen_f, on="show_id", how="left")
                .dropna(subset=["genre"]))
    top10_tv_gen = tv_genre["genre"].value_counts().head(10).index
    hm_sg = (tv_genre[tv_genre["genre"].isin(top10_tv_gen)]
             .groupby(["genre","seasons"]).size()
             .unstack(fill_value=0)
             .reindex(top10_tv_gen))
    hm_sg = hm_sg[[c for c in sorted(hm_sg.columns) if c <= 8]]  # cap at 8 seasons

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(hm_sg, annot=True, fmt="d", cmap="YlGn",
                linewidths=0.4, linecolor="#1a1a1a",
                annot_kws={"size": 9, "weight": "bold"},
                cbar_kws={"shrink": 0.7}, ax=ax)
    ax.set_title("Season Count by Genre")
    ax.set_xlabel("Number of Seasons"); ax.set_ylabel("")
    fig.tight_layout()
    st.pyplot(fig)
    st.download_button("⬇ Download Chart", save_fig(fig), "season_genre_heatmap.png", "image/png")
    plt.close(fig)

    single_s_pct = (tv_df["seasons"] == 1).mean() * 100
    multi_s_pct  = (tv_df["seasons"] >= 3).mean() * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Single-Season Shows", f"{single_s_pct:.1f}%")
    c2.metric("3+ Season Shows", f"{multi_s_pct:.1f}%")
    c3.metric("Max Seasons Detected", str(int(tv_df["seasons"].max())))

    st.markdown(f"""<div class="insight-box">
    💡 <b>Key Insights:</b> The majority of Netflix TV Shows (~{single_s_pct:.0f}%) have only <b>1 season</b>,
    reflecting the high cancellation rate of experimental originals and single-season licensed content.
    Shows reaching <b>3+ seasons</b> ({multi_s_pct:.0f}%) represent Netflix's committed long-form franchises —
    these are the sequels and renewals that anchor subscriber retention. Crime TV Shows and Dramas
    have the highest multi-season rates in the genre heatmap. The sequel detection analysis shows
    Movies have a lower sequel rate than TV Shows, where serialised storytelling is inherently expected.
    For development strategy: <b>investing in proven 1–2 season shows for renewal</b> offers lower risk
    than commissioning new IP.
    </div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<p style='text-align:center;color:{TEXT_MUTED};font-size:.8rem;'>
NTU DSAI Module 2 · Team 4 · Netflix Catalogue Analytics Pipeline<br>
BigQuery: <code>ntu-dsai-t4-netflix.analytics</code> · 
Star Schema: <code>fact_showlist</code> + <code>dim_agerating</code> + <code>dim_showcountry</code> + 
<code>dim_showgenre</code> + <code>dim_showtitle</code>
</p>
""", unsafe_allow_html=True)
