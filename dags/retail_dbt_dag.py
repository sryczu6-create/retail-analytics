"""
Airflow DAG: orchestrate the dbt transformation layer on BigQuery.

Replaces the tail of the old PostgreSQL ETL DAG: Airflow now triggers
dbt (deps -> run -> test) against BigQuery instead of loading Postgres.
Tasks are split so a failure in `test` does not force re-running `run`
(granular recovery) — the same design principle as the original DAG.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Absolute paths: Airflow tasks may execute from a different working directory.
DBT_PROJECT_DIR = "/home/asus/retail-analytics/dbt"
DBT_BIN = "/home/asus/retail-analytics/.venv/bin/dbt"
# 'export HOME' lets dbt find ~/.dbt/profiles.yml and the gcloud ADC credentials.
BASE = f"export HOME=/home/asus && cd {DBT_PROJECT_DIR} &&"

default_args = {
    "owner": "sry",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="retail_dbt_pipeline",
    description="Build and test the dbt models on BigQuery",
    start_date=datetime(2024, 1, 1),
    schedule=None,          # manual / triggered runs
    catchup=False,
    default_args=default_args,
    tags=["retail", "dbt", "bigquery"],
) as dag:

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{BASE} {DBT_BIN} deps",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"{BASE} {DBT_BIN} run",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{BASE} {DBT_BIN} test",
    )

    dbt_deps >> dbt_run >> dbt_test
