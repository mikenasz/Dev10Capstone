drop schema if exists soccer_schema cascade;
create schema soccer_schema;
set search_path to soccer_schema;

create table countries(
    country_id serial primary key,
    country_name varchar(100) not null
    );

create table tournaments(
    tournament_id serial primary key,
    tournament_name varchar(100) not null
    ); 

create table matches(
    match_id serial primary key,
    match_date date not null,
    home_team_id integer not null
        references countries(country_id),
    away_team_id integer not null
        references countries(country_id),
    home_team_score integer not null,
    away_team_score integer not null,
    tournament_id integer references tournaments(tournament_id),
    location_country_id integer references countries(country_id),
    winner_id integer references countries(country_id)
    );



create table ratings(
    rating_id serial primary key,
    rating integer not null,
    country_id integer references countries(country_id),
    date date not null
    );