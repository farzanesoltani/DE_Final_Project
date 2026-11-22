from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

def run_incremental_etl():
    from extract_to_staging import extract_and_load
    extract_and_load()

default_args = {
    'owner': 'farzaneh',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'students_etl_pipeline',
    default_args=default_args,
    description='Incremental ETL pipeline from SQL Server to PostgreSQL Staging',
    schedule_interval='@daily',
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    etl_task = PythonOperator(
        task_id='run_sqlserver_to_postgres_etl',
        python_callable=run_incremental_etl,
    )

    etl_task
