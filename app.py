import numpy as np
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

df_filtered = df_filtered.copy()
df_filtered["Total Goals"] = df_filtered["Home Team Goals"] + df_filtered["Away Team Goals"]

# ---------------------------------------------------------------------------
# 1. Average goals per match per World Cup year, with OLS trendline
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
    title="Average total goals scored per World Cup match per year",
    labels={"Total Goals": "Goals per match"},
    height=500,
    width=900,
    trendline="ols",
)
fig.update_traces(mode="lines+markers", selector=dict(mode="markers"))
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 2. Average total goals per referee
# ---------------------------------------------------------------------------
st.subheader("Average Total Goals per Match by Referee")

# Calculate average goals for each referee
referee_stats = (
    df_filtered
    .groupby("Referee")
    .agg(
        Matches=("Referee", "count"),
        AvgGoals=("Total Goals", "mean")
    )
    .reset_index()
)

# Keep referees with at least 5 matches
referee_stats = referee_stats[referee_stats["Matches"] >= 5]

# Show top 15 referees by number of matches
referee_stats = referee_stats.sort_values(
    "Matches",
    ascending=False
).head(15)

fig_referees = px.bar(
    referee_stats,
    x="Referee",
    y="AvgGoals",
    color="Matches",
    title="Average Total Goals per Match by Referee",
    labels={
        "AvgGoals": "Average Goals",
        "Referee": "Referee",
        "Matches": "Matches Officiated",
    },
)

st.plotly_chart(fig_referees, use_container_width=True)

# ---------------------------------------------------------------------------
# 3. Distribution of scores
# ---------------------------------------------------------------------------
st.subheader("Distribution of Scores")

wmiii = pd.pivot_table(
    df_filtered,
    values="Year",
    index="Home Team Goals",
    columns="Away Team Goals",
    aggfunc="count",
    observed=True,
    fill_value=0,
)

fig_scores = px.imshow(
    wmiii,
    title="Distribution of scores",
    height=500,
    width=900,
)
st.plotly_chart(fig_scores, use_container_width=True)

# ---------------------------------------------------------------------------
# 4. Distribution of goals scored by winning vs losing teams
# ---------------------------------------------------------------------------
st.subheader("Distribution of Goals Scored by Winning vs Losing Teams")

box_df = df_filtered.copy()
box_df["Winning Score"] = np.where(
    box_df["Home Team Goals"] > box_df["Away Team Goals"],
    box_df["Home Team Goals"],
    np.where(box_df["Home Team Goals"] < box_df["Away Team Goals"], box_df["Away Team Goals"], box_df["Home Team Goals"]),
)
box_df["Losing Score"] = np.where(
    box_df["Home Team Goals"] > box_df["Away Team Goals"],
    box_df["Away Team Goals"],
    np.where(box_df["Home Team Goals"] < box_df["Away Team Goals"], box_df["Home Team Goals"], box_df["Away Team Goals"]),
)

fig_box = px.box(
    data_frame=box_df,
    title="Distribution of the goals scored by winning vs. losing teams",
    x=["Losing Score", "Winning Score"],
    height=500,
    width=900,
)
st.plotly_chart(fig_box, use_container_width=True)

# ---------------------------------------------------------------------------
# 5. Attendance by year at each knockout stage
# ---------------------------------------------------------------------------
st.subheader("Attendance by Year at Each Stage")

wmv = df_filtered.groupby(["Year", "Stage"])["Attendance"].mean().reset_index()
wmv = wmv[
    (wmv["Stage"] == "Final")
    | (wmv["Stage"] == "Semi-finals")
    | (wmv["Stage"] == "Match for third place")
    | (wmv["Stage"] == "Quarter-finals")
    | (wmv["Stage"] == "Round of 16")
]

fig_attendance = px.line(
    data_frame=wmv,
    x="Year",
    y="Attendance",
    color="Stage",
    title="Attendance by year at each stage",
    category_orders={"Stage": ["Round of 16", "Quarter-finals", "Semi-finals", "Match for third place", "Final"]},
    height=500,
    width=900,
)
st.plotly_chart(fig_attendance, use_container_width=True)

# ---------------------------------------------------------------------------
# 6. Correlation between attendance and total goals by stage
# ---------------------------------------------------------------------------
st.subheader("Correlation Between Attendance and Total Goals by Stage")

wmvi = df_filtered[
    (df_filtered["Stage"] == "Final")
    | (df_filtered["Stage"] == "Semi-finals")
    | (df_filtered["Stage"] == "Match for third place")
    | (df_filtered["Stage"] == "Quarter-finals")
    | (df_filtered["Stage"] == "Round of 16")
]

fig_attendance_goals = px.scatter(
    data_frame=wmvi,
    x="Attendance",
    y="Total Goals",
    color="Stage",
    opacity=0.7,
    title="Correlation between attendance and total goals scored by stage",
    category_orders={"Stage": ["Round of 16", "Quarter-finals", "Semi-finals", "Match for third place", "Final"]},
    trendline="ols",
)
st.plotly_chart(fig_attendance_goals, use_container_width=True)

# ---------------------------------------------------------------------------
# 7. Total goals scored by country
# ---------------------------------------------------------------------------
st.subheader("Total Goals Scored by Country")

home_goals = df_filtered.groupby("Home Team Name")["Home Team Goals"].sum()
away_goals = df_filtered.groupby("Away Team Name")["Away Team Goals"].sum()
wmvii = home_goals.add(away_goals, fill_value=0).sort_values(ascending=False).head(8).to_frame(name="goals").reset_index()
wmvii = wmvii.rename(columns={"Home Team Name": "Country"})

fig_country_goals = px.bar(
    data_frame=wmvii,
    x="Country",
    y="goals",
    title="Total goals scored by country",
    labels={"Country": "Country", "goals": "Goals"},
)
st.plotly_chart(fig_country_goals, use_container_width=True)
