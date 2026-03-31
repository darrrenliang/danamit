from airflow import DAG
from airflow.decorators import task
from pendulum import datetime

# 1. Define the DAG context
with DAG(
    dag_id="simple_english_print_dag",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["example", "test"],
) as dag:

    # 2. Define the tasks using the @task decorator
    @task
    def start_task():
        print("Task 1: Starting the process...")

    @task
    def process_task():
        print("Task 2: Currently processing data in the middle...")

    @task
    def end_task():
        print("Task 3: Process completed successfully!")

    # 3. Set the task dependencies (execution order)
    start_task() >> process_task() >> end_task()