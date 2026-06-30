from dash import Dash, dcc, html, dash_table, Input, Output, callback
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

def load_match_data(engine):
    query = """
        SELECT
            m.match_id,
            m.match_date,
            h.country_name as home_team,
            a.country_name as away_team,
            m.home_team_score,
            m.away_team_score,
            t.tournament_name,
            coalesce(w.country_name, 'Draw') as winner_team_name,
            m.home_team_rating,
            m.away_team_rating,
            m.home_team_rating - m.away_team_rating as rating_difference
            from soccer_schema.matches m
            join soccer_schema.countries h on m.home_team_id = h.country_id
            join soccer_schema.countries a on m.away_team_id = a.country_id
            join soccer_schema.tournaments t on m.tournament_id = t.tournament_id
            left join soccer_schema.countries w on m.winner_id = w.country_id
    """
    return pd.read_sql(query, engine)

full_match_data = load_match_data(engine)
print(full_match_data.head())



app.layout = html.Div([
    html.H1("International Soccer Match Analytics(1872)"),
    dash_table.DataTable(
        data=full_match_data.to_dict('records'),
        columns=[{"name": i, "id": i} for i in full_match_data.columns],
        page_size=15,
        sort_action='native',
        filter_action='native',
        id='match-table',
    )
])


if __name__ == "__main__":
    app.run(debug=True)
