import pendulum
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task
from etl.etl import extract_data, Transformer, Loader


@dag(
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["soccer", "etl"],

)

def run_etl_dag():
    
    #Create schema and run DDL
    soccer_schema = SQLExecuteQueryOperator(
        task_id="create_soccer_schema",
        sql = "/etl/soccer.sql",
        conn_id= 'soccer_etl',
    )
    
    #ETL process
    @task()
    def run_soccer_etl():
        hook = PostgresHook(postgres_conn_id='soccer_etl')
        engine = hook.get_sqlalchemy_engine()
        results_data = extract_data("/opt/airflow/data/results.csv")
        ratings_data = extract_data("/opt/airflow/data/eloratings.csv")
        transformer = Transformer(ratings_data, results_data)
        transformed_ratings, transformed_results = transformer.transform()
        loader = Loader(transformed_ratings, transformed_results, engine)
        loader.load_all()
        engine.dispose()

    
    
    etl_task = run_soccer_etl()
    soccer_schema >> etl_task 
    
run_etl_dag()