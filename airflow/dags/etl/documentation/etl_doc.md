## Shapes of raw data

eloratings.csv

- Format : CSV
- Row Count: 6679 records
- Columns : date, team, rating, change
- The date(date) column is important as it will signify when the rating update has occurred. This will also be our join key with the matches.
- Team(string) is also going to be our join key, this will be joined with the results_df country.
- Rating(int) is our important data column which will represent a teams ELO rating at a certain date, important for our analysis.
- Change(int) will be dropped as its not really important for our analysis, this can also be computed by ourselves if we need to know.

- Example : date,team,rating,change
            1872-11-30,England,2003,3

results.csv

- Format : CSV
- Row Count : 49478 records
- Columns : date,home_team,away_team,home_score,away_score,tournament,city,country,neutral
- Date(date) column will be important to signify a match date, this will be a join key for our ratings date.
- home_team, away_team(string) will be our team columns, this will be mapped to a id value, foreign key from our country table.
- home_score, away_score are our numeric values indicated the score for both teams.
- tournament(string) will also be mapped to an id, being a foreign key to our tournaments table.
- country(string) will be another foreign key, this will changed to match_location to signify the country were the match took place.
- city and neutral will dropped, as it is unnecessary for our analysis

- Example : date,home_team,away_team,home_score,away_score,tournament,city,country,neutral
        1872-11-30,Scotland,England,0,0,Friendly,Glasgow,Scotland,FALSE

## Transformation/Cleaning

Cleaning
- Drop Nulls
- Cleaning nbsp for country names like "United States", we found that country names with spaces did not match when joining.
- Casting data types, rating and score columns need to be casted as int for our schema, date columns need to casted as date object and be normalized as there are some inconsistencies with date value.

Transformation 
- Normalizing name changes such as "Czechia" to "Czech Republic" 
- Drop/Rename columns
- Add a winner id column to list the id of the winner of the match


## Merging

- Our rating and results datasets will be joined by using a special pandas method merge_asof. 
- What this will do, it will merge ratings to each match, we will join twice once for the home team, away team.
- It will be unique as in case there is no matching date, it will use the most recent previous date. We need to use a previous date as that will be the most updated ELO rating for every team. If there is no match, it will return null.






