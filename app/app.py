from dash import Dash, Input, Output, dcc, html
import plotly.express as px
import pandas as pd
from sqlalchemy import create_engine
from dynaconf import Dynaconf

app = Dash()

def build_engine():
    settings = Dynaconf(
        envvar_prefix="DB",
        settings_files=['.env'],
        load_dotenv=True
    )
    return create_engine(settings.ENGINE_URL, echo=False)


engine = build_engine()

def load_elo_data(db_engine):
    query = """
    SELECT
        r.date,
        c.country_name,
        r.rating
    FROM soccer_schema.ratings r
    JOIN soccer_schema.countries c
      ON c.country_id = r.country_id
    WHERE r.date >= '2000-01-01' AND r.date < '2026-01-01'
    ORDER BY r.date
    """
    data = pd.read_sql(query, db_engine)
    data["date"] = pd.to_datetime(data["date"])
    return data

def pull_big_tournament_matches(engine):
    query = """
     SELECT m.match_date, t.tournament_name,
           h.country_name as home_team, a.country_name as away_team,
           m.home_team_score, m.away_team_score,
           m.home_team_rating, m.away_team_rating
    from soccer_schema.matches m
    join soccer_schema.countries   h on m.home_team_id  = h.country_id
    join soccer_schema.countries   a on m.away_team_id  = a.country_id
    join soccer_schema.tournaments t on m.tournament_id = t.tournament_id
    """
    return pd.read_sql(query, engine)

all_tournament_matches = pull_big_tournament_matches(engine)
all_tournament_matches["match_date"] = pd.to_datetime(all_tournament_matches["match_date"])

TOURNAMENTS = [
    "FIFA World Cup",
    "UEFA Euro",
    "Copa América",
    "AFC Asian Cup",
    "Gold Cup",
    "African Cup of Nations",
]

def build_prediction_plot(df):
    
    d = df[
        df["home_team_rating"].notna()
        & df["away_team_rating"].notna()
        & (df["home_team_score"] != df["away_team_score"])    
        & (df["match_date"] >= "2000-01-01")
        & (df["match_date"] <  "2026-01-01")
    ].copy()
    
    d["fav_is_home"] = d["home_team_rating"] > d["away_team_rating"]
    d["home_win"] = d["home_team_score"] > d["away_team_score"]
    
    d["fav_is_away"] = d["away_team_rating"] > d["home_team_rating"]
    d["away_win"] = d["away_team_score"] > d["home_team_score"]
    
    
    d["fav_won"] = (d["fav_is_home"] & d["home_win"]) | (d["fav_is_away"] & d["away_win"])
    
    
    d['gap'] = (d['home_team_rating'] - d['away_team_rating']).abs()
    
    
    bins = [1, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
    labels = ["1-50", "51-100", "101-150", "151-200", "201-250", "251-300", "301-350", "351-400", "401-450", "451-500"]
    d['elo_gap_bin'] = pd.cut(d['gap'], bins=bins, labels=labels, right=True, include_lowest=True)
    calibration_summary = (
        d.groupby('elo_gap_bin', observed=True, as_index=False)
        .agg(
            matches=('fav_won', 'size'),
            fav_wins=('fav_won', 'sum'),
        ))
    calibration_summary['fav_win_pct'] = (
        100 * calibration_summary['fav_wins'] / calibration_summary['matches']
    ).round(2)
    return calibration_summary
    
def avg_goals_by_year(df):
    out = df.copy()
    out['year'] = out['match_date'].dt.year
    out['total_goals'] = out['home_team_score'] + out['away_team_score']

    goals_per_year = (
        out.groupby('year', as_index=False)
        .agg(
            avg_goals=('total_goals', 'mean'),
        )
    )
    goals_per_year['avg_goals'] = goals_per_year['avg_goals'].round(2)
    return goals_per_year


def avg_goal_diff_by_year(df):
    out = df.copy()
    out['year'] = out['match_date'].dt.year
    out['goal_diff'] = (out['home_team_score'] - out['away_team_score']).abs()

    diff_per_year = (
        out.groupby('year', as_index=False)
        .agg(
            avg_goal_diff=('goal_diff', 'mean'),
        )
    )
    diff_per_year['avg_goal_diff'] = diff_per_year['avg_goal_diff'].round(2)
    return diff_per_year

def get_top_elo_rankings(df):
    latest_date = df['date'].max()
    latest_rankings = df[df['date'] == latest_date]
    latest_rankings = latest_rankings[latest_rankings['rating'] > 0]
    top_countries = latest_rankings.nlargest(10, 'rating')

    return top_countries


def build_top_elo_chart(df):
    top_countries = get_top_elo_rankings(df)
    top_countries = top_countries.sort_values("rating", ascending=True)

    latest_date = pd.to_datetime(df["date"]).max().date()
    fig = px.bar(
        top_countries,
        x="rating",
        y="country_name",
        orientation="h",
        title=f"Top 10 ELO Ratings (as of {latest_date})",
        labels={"country_name": "Country", "rating": "ELO Rating"},
        color_discrete_sequence=["#1a6193"],
    )
    fig.update_layout(height=650, showlegend=False)
    return fig



def build_tournament_performance_summary(df, tournament="FIFA World Cup", min_matches=6, loss_gap=150, draw_gap=250):
    
    if tournament in TOURNAMENTS:
        f = df[df["tournament_name"] == tournament].copy()
    else:
        f = df[df["tournament_name"].isin(TOURNAMENTS)].copy()
   
    f["rating_gap"] = (f["home_team_rating"] - f["away_team_rating"]).abs()
    
    f["favorite_team"] = f["home_team"]
    f.loc[f["away_team_rating"] > f["home_team_rating"], "favorite_team"] = f["away_team"]
    
    f["underdog_team"] = f["away_team"]
    f.loc[f["away_team_rating"] > f["home_team_rating"], "underdog_team"] = f["home_team"]
    
    fav_is_home = f["favorite_team"] == f["home_team"]
    fav_is_away = f["favorite_team"] == f["away_team"]
    
    fav_lost = (fav_is_home & (f["home_team_score"] < f["away_team_score"])) | (fav_is_away & (f["away_team_score"] < f["home_team_score"]))
    fav_drew = f["home_team_score"] == f["away_team_score"]
    fav_won  = (fav_is_home & (f["home_team_score"] > f["away_team_score"])) | (fav_is_away & (f["away_team_score"] > f["home_team_score"]))

    valid_loss = fav_lost & (f["rating_gap"] >= loss_gap)
    valid_draw = fav_drew & (f["rating_gap"] >= draw_gap)
    valid_win  = fav_won  & (f["rating_gap"] >= loss_gap)
    
    f = f[valid_loss | valid_draw | valid_win].copy()

    f["is_event"] = (valid_loss | valid_draw).astype(int)
    group_col = "underdog_team"
    pct_col_name = "underdog_upset_pct"
    matches_col = "underdog_matches"
    events_col = "underdog_upsets"

    summary = (
        f.groupby(group_col, as_index=False)
        .agg(
            total_matches=("is_event", "size"),
            total_events=("is_event", "sum"),
        )
    )
    
    summary[pct_col_name] = (100 * summary["total_events"] / summary["total_matches"]).round(2)
    summary = summary.rename(columns={"total_matches": matches_col, "total_events": events_col})
    
    summary = summary[summary[matches_col] >= min_matches]
    
    return summary.sort_values(pct_col_name, ascending=False)


elo_filtered_matches = all_tournament_matches[
    all_tournament_matches["home_team_rating"].notna()
    & all_tournament_matches["away_team_rating"].notna()
    & (all_tournament_matches["match_date"] >= "2000-01-01")
    & (all_tournament_matches["match_date"] < "2026-03-01")
].copy()

def tournament_competitiveness(df):
    comp = df
    
    comp = comp[comp["tournament_name"].isin(TOURNAMENTS)].copy()
    comp = comp[
        comp["home_team_rating"].notna() &
        comp["away_team_rating"].notna()
    ].copy()
    comp["elo_gap"] = (comp["home_team_rating"] - comp["away_team_rating"]).abs()
    
    get_summary = (
        comp.groupby("tournament_name", as_index=False)
        .agg(
            matches=("elo_gap", "size"),
            median_elo_gap=("elo_gap", "median"),
        )
    )

   
    get_summary["median_elo_gap"] = get_summary["median_elo_gap"].round(2)
    get_summary = get_summary.sort_values("median_elo_gap", ascending=True)
    return get_summary



competitiveness_summary = tournament_competitiveness(elo_filtered_matches)

def goals_by_tournament(df):
    d = df[df["tournament_name"].isin(TOURNAMENTS)].copy()
    d["total_goals"] = d["home_team_score"] + d["away_team_score"]
    out = (d.groupby("tournament_name", as_index=False)
             .agg(
                  avg_goals=("total_goals", "mean")))
    out["avg_goals"] = out["avg_goals"].round(2)
    return out.sort_values("avg_goals", ascending=False)


def draws_over_time(df):
    df = df.copy()
    df["year"] = df["match_date"].dt.year
    df["is_draw"] = (df["home_team_score"] == df["away_team_score"])
    out = (df.groupby("year", as_index=False)
              .agg(matches=("is_draw", "size"),
                     draws=("is_draw", "sum")))
    out["draw_pct"] = (100 * out["draws"] / out["matches"]).round(2)
    out = out[out["year"] > 1903]
    out = out[out["matches"] >= 10]
    return out



def build_goals_by_tournament_chart():
    goals_summary = goals_by_tournament(all_tournament_matches)
    fig = px.bar(
        goals_summary,
        x="tournament_name",
        y="avg_goals",
        title="Average Goals per Match by Tournament",
        labels={"tournament_name": "Tournament", "avg_goals": "Average Goals per Match"},
    )
    return fig

def build_calibration_graph():
    calibration = build_prediction_plot(all_tournament_matches)
    fig = px.line(
        calibration,
        x="elo_gap_bin",
        y="fav_win_pct",
        markers=True,
        title="Favorite Win Percentage by ELO Rating Gap",
        labels={
            "elo_gap_bin": "Rating Gap (ELO Points)",
            "fav_win_pct": "Favorite Win %",
        },
    )
    fig.update_traces(line=dict(width=3), mode ="lines+markers")
    fig.update_yaxes(range=[49, 101])      
    fig.update_layout(height=450)
    return fig

elo_data = load_elo_data(engine)

all_countries = elo_data["country_name"].unique()

def render_elo_tab():
    return html.Div(
        [
            html.H1("Tournament Upsets (2000-2025)", style={"marginTop": "30px", "marginBottom": "28px"}),
            html.Hr(style={"margin": "24px auto", "maxWidth": "900px"}),
            html.P("Which teams have performed the best when playing against stronger opponents?"),
            html.P("We define an upset as a match where the underdog team wins or draws against a team with an ELO rating at least 150 points higher (for losses) or 250 points higher (for draws)."),
            dcc.Dropdown(
                id="elo-tournament-filter",
                options=[{"label": t, "value": t} for t in TOURNAMENTS],
                value= "FIFA World Cup",
                clearable=False,
                style={"maxWidth": "520px", "margin": "0 auto 16px"},
            ),
            dcc.Graph(id="underdog-chart"),
            
            html.Hr(style={"margin": "30px auto", "maxWidth": "900px"}),
            html.H1("Skill Gap Across Tournaments", style={"marginTop": "34px", "marginBottom": "22px"}),
            html.P("The median ELO rating gap between teams in each tournament. A smaller gap indicates a more evenly matched tournament."),
            dcc.Graph(id="competitiveness-chart", figure=build_comp_graph()),
            html.Hr(style={"margin": "30px auto", "maxWidth": "900px"}),
            html.H1("ELO Ratings Over Time", style={"marginTop": "34px", "marginBottom": "22px"}),
            html.P("Select one or more countries to compare ELO ratings over time."),
            dcc.Dropdown(
                id="country-filter",
                options=[{"label": c, "value": c} for c in all_countries],
                value=["England", "Brazil", "Argentina"],
                multi=True,
                placeholder="Choose countries",
                style={"maxWidth": "680px", "margin": "0 auto 16px"},
            ),
            dcc.Graph(id="elo-trend-chart"),
            html.Hr(style={"margin": "30px auto", "maxWidth": "900px"}),
            html.H1("Top 10 ELO Ratings", style={"marginTop": "34px", "marginBottom": "22px"}),
            html.P("Top 10 ELO ratings as of the most recent date in the dataset."),
            html.Div(
                [
                    dcc.Graph(id="elo-top-rankings-chart", figure=build_top_elo_chart(elo_data), style={"width": "100%"}),
                ],
                style={"display": "flex", "gap": "12px", "alignItems": "stretch"},
            ),
            html.Hr(style={"margin": "30px auto", "maxWidth": "900px"}),
            html.H1("Match Outcomes by ELO Rating", style={"marginTop": "34px", "marginBottom": "22px"}),
            html.P("How often does the higher ranked team based on gaps in ELO ratings win?"),
            dcc.Graph(id="elo-calibration-chart", figure=build_calibration_graph()),
            
        ],
        style={"maxWidth": "1200px", "margin": "0 auto", "padding": "10px 16px 36px", "textAlign": "center"},
    )


def render_goals_tab():
    return html.Div(
        [
            html.H1("Tournament Goals Analysis", style={"marginTop": "30px", "marginBottom": "28px"}),
            dcc.Dropdown(
                id="goals-tournament-filter",
                options=[{"label": "All", "value": "All"}] + [{"label": t, "value": t} for t in TOURNAMENTS],
                value="All",
                clearable=False,
                style={"maxWidth": "520px", "margin": "0 auto 16px"},
            ),
            html.P("Average goals and goal differential per match by year."),
            dcc.Graph(id="goals-chart"),
            html.Hr(style={"margin": "30px auto", "maxWidth": "900px"}),
            html.P("Percentage of matches that ended in a draw by year."),
            dcc.Graph(id="draws-chart"),
            html.Hr(style={"margin": "30px auto", "maxWidth": "900px"}),
            html.P("Goal difference between tournaments."),
            dcc.Graph(id="goal-diff-tournament-chart", figure=build_goals_by_tournament_chart()),
            
        ],
        style={"maxWidth": "1200px", "margin": "0 auto", "padding": "10px 16px 36px", "textAlign": "center"},
    )
    
def build_comp_graph():
    fig = px.bar(
        competitiveness_summary,
        x="tournament_name",
        y="median_elo_gap",
        title="Median ELO Gap by Tournament (2000-2025)",
        labels={"tournament_name": "Tournament", "median_elo_gap": "Median ELO Gap"},
    )
    return fig


app.layout = html.Div([
    html.Div(
        [
            html.H1("International Soccer Data Visualizations", style={"marginTop": "18px", "marginBottom": "28px"}),
            html.A(
                "International Match Results Dataset",
                href="https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017/data?select=results.csv",
                target="_blank",
                style={"display": "inline-block", "margin": "0 12px"},
            ),
            html.A(
                "ELO Ratings Dataset",
                href="https://www.kaggle.com/datasets/saifalnimri/international-football-elo-ratings",
                target="_blank",
                style={"display": "inline-block", "margin": "0 12px"},
            ),
        ],
        style={"textAlign": "center", "marginBottom": "34px", "marginTop": "20px"},
    ),
    
    dcc.Tabs(
        [
            dcc.Tab(render_elo_tab(), label="ELO Analysis"),
            dcc.Tab(render_goals_tab(), label="Goals Analysis"),
            
        ]
    )
   
])


@app.callback(
    Output("elo-trend-chart", "figure"),
    Input("country-filter", "value"),
)
def update_elo_chart(selected_countries):
    if not selected_countries:
        empty_fig = px.line(title="Select at least one country")
        return empty_fig

    filtered = elo_data[elo_data["country_name"].isin(selected_countries)]
    fig = px.line(
        filtered,
        x="date",
        y="rating",
        color="country_name",
        title="ELO Rating Trends by Country",
        labels={"date": "Date", "rating": "ELO Rating", "country_name": "Country"},
    )
    fig.update_layout(legend_title_text="Country")
    return fig


@app.callback(
    Output("underdog-chart", "figure"),
    Input("elo-tournament-filter", "value"),
)
def update_underdog_chart(selected_tournament):


    plot_df = build_tournament_performance_summary(
        elo_filtered_matches, 
        tournament=selected_tournament,
        min_matches=6,
        loss_gap=150,
        draw_gap=250
    )

    plot_df = plot_df[plot_df['underdog_upset_pct'] > 0]
    plot_df = plot_df.sort_values("underdog_upset_pct", ascending=False).head(5).reset_index(drop=True)
    fig = px.bar(
        plot_df,
        x="underdog_upset_pct",
        y="underdog_team",
        orientation="h",
        title=f"Teams with the Highest Upset Rate ({selected_tournament})",
        labels={"underdog_team": "Team", "underdog_upset_pct": "Upsets %", "underdog_matches": "Matches Played"},
        hover_data={"underdog_matches": True}
    )
    fig.update_traces(marker_color="#248f47")
    fig.update_layout(
        height=600,
        margin=dict(l=130, r=10, t=50, b=50),
        yaxis=dict(autorange="reversed")
    )
    return fig


@app.callback(
    Output("goals-chart", "figure"),
    Input("goals-tournament-filter", "value"),
)
def update_goals_chart(selected_tournament):

    if selected_tournament == "All":
        tournament_df = all_tournament_matches
        chart_label = "All"
    else:
        tournament_df = all_tournament_matches[
            all_tournament_matches["tournament_name"] == selected_tournament
        ]
        chart_label = selected_tournament
    goals_summary = avg_goals_by_year(tournament_df)
    diff_summary = avg_goal_diff_by_year(tournament_df)
    combined = goals_summary.merge(diff_summary[["year", "avg_goal_diff"]], on="year", how="inner")
    combined_long = combined.melt(
        id_vars=["year"],
        value_vars=["avg_goals", "avg_goal_diff"],
        var_name="metric",
        value_name="value",
    )
    combined_long["metric"] = combined_long["metric"].map(
        {
            "avg_goals": "Average Goals",
            "avg_goal_diff": "Average Goal Differential",
        }
    )
    goals_fig = px.line(
        combined_long,
        x="year",
        y="value",
        color="metric",
        markers=True,
        title=f"Average Goals and Goal Differential by Year ({chart_label})",
        labels={"year": "Year", "value": "Average per Match", "metric": "Metric"},
    )
    goals_fig.update_traces(line=dict(width=3))

    return goals_fig

@app.callback(
    Output("draws-chart", "figure"), 
    Input("goals-tournament-filter", "value")
)
def update_draws_chart(selected_tournament):
    if selected_tournament == "All":
        tournament_df = all_tournament_matches
        chart_label = "All"
    else:
        tournament_df = all_tournament_matches[
            all_tournament_matches["tournament_name"] == selected_tournament
        ]
        chart_label = selected_tournament

    draws_summary = draws_over_time(tournament_df)
    fig = px.line(
        draws_summary,
        x="year",
        y="draw_pct",
        markers=True,
        title=f"Draws as a Percentage of Matches by Year ({chart_label})",
        labels={"year": "Year", "draw_pct": "Draws as % of Matches"},
    )
    fig.update_traces(line=dict(width=3))
    return fig


if __name__ == "__main__":
    app.run(debug=True)
