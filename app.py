import pandas as pd
import numpy as np
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
# Top-level KPIs
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Matches", len(df_filtered))
total_goals = df_filtered["Home Team Goals"].sum() + df_filtered["Away Team Goals"].sum()
col2.metric("Total Goals", int(total_goals))
avg_goals = total_goals / len(df_filtered) if len(df_filtered) else 0
col3.metric("Avg Goals / Match", f"{avg_goals:.2f}")

st.divider()

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
# 3. Goals per game by team (only shown when teams are selected, or top N overall)
# ---------------------------------------------------------------------------
st.subheader("Goals per Game by Team")

home_goals = df_year.groupby("Home Team Name")["Home Team Goals"].sum()
away_goals = df_year.groupby("Away Team Name")["Away Team Goals"].sum()
total_goals_team = home_goals.add(away_goals, fill_value=0)

home_games = df_year.groupby("Home Team Name").size()
away_games = df_year.groupby("Away Team Name").size()
total_games_team = home_games.add(away_games, fill_value=0)

goals_per_game = (total_goals_team / total_games_team).rename("Goals per Game")
team_summary = pd.concat([total_goals_team.rename("Total Goals"), total_games_team.rename("Games Played"), goals_per_game], axis=1)

if selected_teams:
    team_summary_view = team_summary.loc[team_summary.index.intersection(selected_teams)]
else:
    # Avoid a cluttered, low-sample-size chart: default to top 15 by games played
    team_summary_view = team_summary.sort_values("Games Played", ascending=False).head(15)

team_summary_view = team_summary_view.sort_values("Goals per Game", ascending=False)

fig_gpg = px.bar(
    team_summary_view.reset_index().rename(columns={"index": "Team"}),
    x="Team",
    y="Goals per Game",
    hover_data=["Total Goals", "Games Played"],
    title="Goals per Game" + (" (Selected Teams)" if selected_teams else " (Top 15 by Games Played)"),
)
st.plotly_chart(fig_gpg, use_container_width=True)

# ---------------------------------------------------------------------------
# 4. Total goals per World Cup year, with trendline
# ---------------------------------------------------------------------------
st.subheader("Total Goals per World Cup Year")

goals_by_year = (
    df_filtered.groupby("Year")
    .apply(lambda g: g["Home Team Goals"].sum() + g["Away Team Goals"].sum())
    .rename("Total Goals")
    .reset_index()
)

fig_year = px.scatter(goals_by_year, x="Year", y="Total Goals", title="Total Goals per World Cup Year")

if len(goals_by_year) > 1:
    z = np.polyfit(goals_by_year["Year"], goals_by_year["Total Goals"], 1)
    trend = np.poly1d(z)
    fig_year.add_scatter(
        x=goals_by_year["Year"],
        y=trend(goals_by_year["Year"]),
        mode="lines",
        name="Trendline",
    )

fig_year.update_traces(mode="lines+markers", selector=dict(mode="markers"))
st.plotly_chart(fig_year, use_container_width=True)
