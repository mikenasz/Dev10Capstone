# International Soccer & ELO Project
Michael Bienasz

This project was done for my Dev10 capstone, and will be looking at International Soccer Matches, as well as ELO ratings and analyzing trends such as teams that upset, top teams based on elo, and goalscoring trends.

## Technologies 

- Python
- Pandas
- Airflow/Docker
- PostgreSQL
- Dash

## Datasets

Primary: International match results(1872-2026)

*Thomas, M. (2023). International football results from 1872 to 2026 [Data set]. Kaggle. Retrieved June 23, 2026, from https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017*

Secondary: International ELO ratings(1872-2025)

*Al-Nimri, S. (2025). International football elo ratings (1872-2025) [Data set]. Kaggle. Retrieved June 23, 2026, from https://www.kaggle.com/datasets/saifalnimri/international-football-elo-ratings*


## Questions

The questions I wanted to analyze from this data focused around ELO in tournament matches and goal scoring across the history of international soccer.

1. Which international teams have upset stronger teams the most in high stakes, tournament games?
2. Which major international tournaments have the lowest ELO gap in matches?
3. How often does the higher rated team win based on ELO rating difference?
4. What are trends in the game we have seen over time, less goals/goal differential?
5. Are draws becoming more common in matches?
6. Who are the top teams based on most recent ELO ratings? 

## ETL Process

Our ETL process will be orchestrated using Airflow and will begin by running the soccer_schema DDL. The ETL process is then dependent on the DDL successfully running.

![ETL](/airflow/dags/etl/documentation/images/ETL.png)

1. Extract

The two main files we will be extracting to a Pandas dataframe are the eloratings.csv and the results.csv

2. Transformation

There are multiple transformations that will be taking place within the data such as

- Standard transformations(dropping columns/nulls, renaming columns)
- Removing nbsp to join countries such as "United States" between the datasets
- Normalizing names of countries that have different names such as "Czechia" to "Czech Republic"
- Casting types to columns
- Adding a winner id column to denote the id of the winning team in our match table
- Joining rankings to matches using merge_asof to get most recent previous rating date

3. Load

The cleaned/transformed data will be then loaded to Postgres into our normalized tables for matches, countries, tournaments, and ratings. The countries and tournaments tables will be loaded first and read back to resolve foreign key dependencies.


## Analysis and Conclusions

For the visualizations, I used Dash as well as Pandas to read the cleaned data from Postgres.
For our ELO charts and analysis, I used data from 2000-2025, this is because there were many inconsistencies with ratings from the prior time period. Our matches analysis will use the full dataset. The major tournaments used for this analysis will be the World Cup, Euros, Copa America, AFC Asian Cup, Gold Cup, and AFCON


## Charts

### Tournament Upsets

The first chart will analyze tournament upsets from multiple tournaments across multiple FIFA confederations. To categorize an upset, we will use an ELO difference of 150 for losses and 250 for draws for the higher rated ELO team.

Upset % will be calculated as total wins/draws as underdog team divided by total games played as underdog.

![Upsets](/images/upsets.png)

### ELO Gap by Tournament

For this chart we will use the median elo gaps by major tournaments we analyzed. The lower the gap the more evenly matched the median matches are.

![TournamentELO](/images/elo_tournament.png)

### Favorite Win %

This chart will visualize percentage of times the favorite has won based on elo gap categories. This is when the higher rated ELO team wins

![FavWin](/images/favwinpct.png)

### Average Total Goals and Goal Differential by Year


![AVGgoals](/images/avggoals.png)

### Draws by Year

![Draws](/images/draws.png)

### Top 10 ELO ratings (as of 12/13/2025)

![Top](/images/top10.png)

### Other Charts

Other charts for more exploration are ELO trends by country and average goals by tournament.

![Trends](/images/elo_trends.png)

![TournamentGoals](/images/goals_tournamnet.png)


## Conclusions

1. Which international teams have upset stronger teams the most in high stakes, tournament games?

From our chart, we saw the teams that have the highest upset % by tournament some in the World Cup are South Korea, Morocco, and Mexico. The highest upset % from our major tournaments we analyzed was Jordan at the AFC Asian Cup with an upset % of 87.5. We noticed that at the Euros there were the fewest upsets, and the highest was 33.33% from Albania. 

We can conclude the top teams that got results from heavy favorites from these high stakes competitive international matches. Which can help identify underrated teams based on ELO ratings.

2. Which major international tournaments have the lowest ELO gap in matches?

What was seen was that the Euros has the lowest median value of 131 in ELO differences across matches, followed closely by AFCON with a value of 143. The highest value was the Gold Cup with a 201.

We can conclude that the Euros has the lowest median ELO gap across games, which means that these games tend to be more even in this tournament. The Gold cup with the highest value can mean that these games tend to be less competitive than the others as there is a higher difference with teams that participate in this tournament.

3. How often does the higher rated team win based on ELO rating difference?

We can see that the favorite win % climbs steadily as the ELO gap gets higher, starting at a marginal difference of 1-50, the higher ranked teams wins around 51% of the time. As the gap raises so does the favorite win %.

In conclusion, we can see that ELO rating is good predictor in our results dataset, a marginal difference for the favorite means the game tends to be more 50/50, and the percentage keeps climbing as gap increases, with the highest gap category around 451-500 has the favorite win 95% of the team.

4. What are trends in the game we have seen over time, less goals/goal differential?

From the cart, it seems as the total goals scored has declined over the years but has stabilized in more modern times. With goal differential it has been more stable over the years without a big indication of a decrease unlike total goals per match.

In conclusion, we can definitely note that total goals per game has dropped since the 1960s, this indicates that some sort of play style might have changed around this time to incorporate more defensive and cautious tactics. 

5. Are draws becoming more common in matches?

Draws have seen a slight increase over time, however nothing signficant worth noting and have stabilized in the past 30 years. This correlates well with what we saw in the total goals per year, stronger evidence that around the 1960s tactics have changed for the game to become more defensive and less attacking.

6. Who are the top teams based on most recent ELO ratings? 

From the chart we can see the top 10 teams as of recent based on ELO. The top 3 for example are Spain, Argentina, and France. This makes sense as these teams were recent winners in tournaments like the World Cup, Euros, and Copa America. Although the ratings are outdated by several months, the current top 10 is around the same with some different placements and 1-2 different teams that entered the top 10.


