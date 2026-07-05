import pandas as pd


def extract_data(file_path):
    
    df = pd.read_csv(file_path)
    return df 

class Transformer:
    
    def __init__(self, ratings_df, results_df):
        self.ratings_df = ratings_df
        self.results_df = results_df
    
    NAME_FIXES = {
    "West Germany": "Germany",
    "Ireland": "Republic of Ireland",        
    "Czechia": "Czech Republic",
    "Democratic Republic of Congo": "DR Congo",
    "East Germany": "German DR",
    }
    
    def normalize_country_names(self):
        self.ratings_df['team'] = self.ratings_df['team'].replace(self.NAME_FIXES)
        self.results_df['home_team'] = self.results_df['home_team'].replace(self.NAME_FIXES)
        self.results_df['away_team'] = self.results_df['away_team'].replace(self.NAME_FIXES)
        self.results_df['country'] = self.results_df['country'].replace(self.NAME_FIXES)
        

    def drop_columns(self):
        
        self.results_df = self.results_df.drop(columns=['city', 'neutral'])
        self.ratings_df = self.ratings_df.drop(columns=['change'])
    
    def drop_nulls(self):
        
        self.ratings_df = self.ratings_df.dropna()
        self.results_df = self.results_df.dropna()
    
    def rename_columns(self):
        
        self.ratings_df = self.ratings_df.rename(columns={'team': 'country'})
        self.results_df = self.results_df.rename(columns={'date': 'match_date', 'home_score': 'home_team_score', 'away_score': 'away_team_score', 'country': 'match_location'})
    
    def clean_nbsp(self):
        self.ratings_df['team'] = self.ratings_df['team'].str.replace('\xa0', ' ', regex=False)
        self.results_df['home_team'] = self.results_df['home_team'].str.replace('\xa0', ' ', regex=False)
        self.results_df['away_team'] = self.results_df['away_team'].str.replace('\xa0', ' ', regex=False)
        self.results_df['country'] = self.results_df['country'].str.replace('\xa0', ' ', regex=False)
       
    def add_winner_column(self):
        
        self.results_df['match_winner'] = 'draw'
        self.results_df.loc[self.results_df['home_team_score'] > self.results_df['away_team_score'], 'match_winner'] = self.results_df['home_team']
        self.results_df.loc[self.results_df['home_team_score'] < self.results_df['away_team_score'], 'match_winner'] = self.results_df['away_team']
        
    def type_cast_columns(self):
        self.ratings_df['rating'] = self.ratings_df['rating'].astype(int)
        self.ratings_df['date'] = pd.to_datetime(self.ratings_df['date'], format= 'mixed')
        self.results_df['home_team_score'] = self.results_df['home_team_score'].astype(int)
        self.results_df['away_team_score'] = self.results_df['away_team_score'].astype(int)
        self.results_df['match_date'] = pd.to_datetime(self.results_df['match_date'], format='mixed')
        
    
        
    def add_ratings(self):
        ratings = self.ratings_df.sort_values('date')
        self.results_df = self.results_df.sort_values('match_date')

        self.results_df = pd.merge_asof(
            self.results_df, ratings[['country', 'date', 'rating']],
            left_on='match_date', right_on='date',
            left_by='home_team', right_by='country',
            direction='backward',
        ).rename(columns={'rating': 'home_team_rating'}).drop(columns=['country', 'date'])

        self.results_df = pd.merge_asof(
            self.results_df, ratings[['country', 'date', 'rating']],
            left_on='match_date', right_on='date',
            left_by='away_team', right_by='country',
            direction='backward',
        ).rename(columns={'rating': 'away_team_rating'}).drop(columns=['country', 'date'])
        

    
    def transform(self):
        
        self.clean_nbsp()
        self.normalize_country_names()
        self.drop_columns()
        self.drop_nulls()
        self.rename_columns()
        self.add_winner_column()
        self.type_cast_columns()
        self.add_ratings()
        return self.ratings_df, self.results_df

class Loader:
    
    def __init__(self, ratings_df, results_df, engine):
        self.ratings_df = ratings_df
        self.results_df = results_df
        self.engine = engine
    
    def load_countries_table(self):
        countries = pd.concat([
            self.results_df['home_team'],
            self.results_df['away_team'],
            self.results_df['match_location'],
            self.ratings_df['country']
            ]).unique()
        countries_df = pd.DataFrame(countries, columns=['country_name'])
        countries_df.to_sql('countries', self.engine, schema='soccer_schema', if_exists='append', index=False)
    
    def load_tournament_table(self):
        tournaments = self.results_df['tournament'].unique()
        tournaments_df = pd.DataFrame(tournaments, columns=['tournament_name'])
        tournaments_df.to_sql('tournaments', self.engine, schema='soccer_schema', if_exists='append', index=False)
    
    def load_matches_table(self):
        countries_df = pd.read_sql('SELECT * FROM soccer_schema.countries', self.engine).set_index('country_name')['country_id']
        tournaments_df = pd.read_sql('SELECT * FROM soccer_schema.tournaments', self.engine).set_index('tournament_name')['tournament_id']
        
        self.results_df['home_team'] = self.results_df['home_team'].map(countries_df)
        self.results_df['away_team'] = self.results_df['away_team'].map(countries_df)
        self.results_df['match_location'] = self.results_df['match_location'].map(countries_df)
        self.results_df['tournament'] = self.results_df['tournament'].map(tournaments_df)
        self.results_df['match_winner'] = self.results_df['match_winner'].map(countries_df)
        
        self.results_df = self.results_df.rename(columns={'home_team': 'home_team_id', 'away_team': 'away_team_id', 'match_location': 'location_country_id', 'tournament': 'tournament_id', 'match_winner': 'winner_id'})
        self.results_df.to_sql('matches', self.engine, schema='soccer_schema', if_exists='append', index=False)
        
    def load_ratings_table(self):
        countries_df = pd.read_sql('SELECT * FROM soccer_schema.countries', self.engine).set_index('country_name')['country_id']
        self.ratings_df['country'] = self.ratings_df['country'].map(countries_df)
        self.ratings_df = self.ratings_df.rename(columns={'country': 'country_id'})
        self.ratings_df.to_sql('ratings', self.engine, schema='soccer_schema', if_exists='append', index=False)
        
    def load_all(self):
        
        self.load_countries_table()
        self.load_tournament_table()
        self.load_matches_table()
        self.load_ratings_table()
    
    
         
    
