import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="World Cup Matches Dashboard", layout="wide")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("World-cup-matches.csv")
    # Normalize a historical naming split so team totals aren't fragmented
    df["Home Team Name"] = df["Home Team Name"].replace({"Germany FR": "Germany"})
    df["Away Team Name"] = df["Away Team Name"].replace({"Germany FR": "Germany"})
    return df

df = load_data()

st.title("World Cup Matches Dashboard")

# ---------------------------------------------------------------------------
# Sidebar filters — kept minimal on purpose:
# Year range and Team selection are the only two that meaningfully change
# every chart below. Extra filters (stadium, referee, etc.) mostly add noise.
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

min_year, max_year = int(df["Year"].min()), int(df["Year"].max())
year_range = st.sidebar.slider(
    "Year range",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),
    step=4,  # World Cups occur every 4 years
)

all_teams = sorted(set(df["Home Team Name"]) | set(df["Away Team Name"]))
selected_teams = st.sidebar.multiselect(
    "Teams (leave empty for all)",
    options=all_teams,
    default=[],
)

# Apply year filter globally
mask_year = df["Year"].between(year_range[0], year_range[1])
df_year = df[mask_year]

# Apply team filter (a match counts if either side is a selected team)
if selected_teams:
    mask_team = df_year["Home Team Name"].isin(selected_teams) | df_year["Away Team Name"].isin(selected_teams)
    df_filtered = df_year[mask_team]
else:
    df_filtered = df_year

# ---------------------------------------------------------------------------
# 1. Home vs Away goals distribution (grouped bar)
# ---------------------------------------------------------------------------
st.subheader("Home vs Away Goals Distribution")

home_counts = df_filtered["Home Team Goals"].value_counts().sort_index()
away_counts = df_filtered["Away Team Goals"].value_counts().sort_index()
all_goals = sorted(set(home_counts.index) | set(away_counts.index))
home_counts = home_counts.reindex(all_goals, fill_value=0)
away_counts = away_counts.reindex(all_goals, fill_value=0)

dist_df = pd.concat(
    [
        pd.DataFrame({"Goals": all_goals, "Matches": home_counts.values, "Type": "Home Team Goals"}),
        pd.DataFrame({"Goals": all_goals, "Matches": away_counts.values, "Type": "Away Team Goals"}),
    ]
)

fig_dist = px.bar(
    dist_df,
    x="Goals",
    y="Matches",
    color="Type",
    barmode="group",
    title="Distribution of Home vs Away Team Goals",
)
st.plotly_chart(fig_dist, use_container_width=True)

# ---------------------------------------------------------------------------
# 2. Home vs Away goals pivot heatmap (scoreline frequency)
# ---------------------------------------------------------------------------
st.subheader("Scoreline Frequency (Home Goals x Away Goals)")

pivot = pd.pivot_table(
    df_filtered,
    index="Home Team Goals",
    columns="Away Team Goals",
    values="Year",
    aggfunc="count",
    fill_value=0,
)

fig_heatmap = px.imshow(
    pivot,
    labels=dict(x="Away Team Goals", y="Home Team Goals", color="Matches"),
    color_continuous_scale="Blues",
    title="Number of Matches per Scoreline",
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# ---------------------------------------------------------------------------
# 3. Average goals per match per World Cup year, with OLS trendline
# ---------------------------------------------------------------------------
st.subheader("Average Total Goals per World Cup Match per Year")

goals_by_year = df_filtered.groupby("Year").apply(
    lambda g: g["Home Team Goals"].sum() + g["Away Team Goals"].sum()
)
matches_by_year = df_filtered.groupby("Year").size()
wmi = (goals_by_year / matches_by_year).rename("Total Goals").reset_index()

fig = px.scatter(
    data_frame=wmi,
    x="Year",
    y="Total Goals",
    # markers = True,
    title="Average total goals scored per World Cup match per year",
    labels={"Total Goals": "Goals per match"},
    height=500,
    width=900,
    trendline="ols",
)
fig.update_traces(mode="lines+markers", selector=dict(mode="markers"))
st.plotly_chart(fig, use_container_width=True)