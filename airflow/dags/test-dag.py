from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

# --- Constants ---
BUCKET_NAME = "airflow"
FILE_NAME = "hello_minio.json"

# --- Logic Functions ---

def create_data_func():
    """
    Generates a simple dictionary with a timestamp.
    The return value is automatically pushed to XCom.
    """
    return {"message": "Hello from Airflow!", "timestamp": str(datetime.now())}

def upload_func(ti):
    """
    Pulls data from XCom and uploads it to MinIO using S3Hook.
    """
    # Retrieve data from the 'create_data' task via XCom
    data = ti.xcom_pull(task_ids='create_data')
    
    # Initialize the S3Hook using the connection ID 'minio_conn'
    s3 = S3Hook(aws_conn_id='minio_conn')
    
    # Ensure the target bucket exists; create it if it doesn't
    if not s3.check_for_bucket(BUCKET_NAME):
        s3.create_bucket(BUCKET_NAME)
        
    # Upload the stringified data to MinIO/S3
    s3.load_string(str(data), FILE_NAME, BUCKET_NAME, replace=True)

def check_func():
    """
    Checks if the file was successfully uploaded to the bucket.
    """
    s3 = S3Hook(aws_conn_id='minio_conn')
    exists = s3.check_for_key(FILE_NAME, BUCKET_NAME)
    print(f"File {FILE_NAME} exists in bucket {BUCKET_NAME}: {exists}")

# --- DAG Definition ---

with DAG(
    'simple_minio_dag',
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,  # This DAG must be triggered manually
    catchup=False            # Do not run historical backfills
) as dag:

    # Task 1: Generate the JSON data
    t1 = PythonOperator(
        task_id='create_data', 
        python_callable=create_data_func
    )

    # Task 2: Connect to MinIO and upload the file
    t2 = PythonOperator(
        task_id='upload_to_minio', 
        python_callable=upload_func
    )

    # Task 3: Verify the presence of the file
    t3 = PythonOperator(
        task_id='check_result', 
        python_callable=check_func
    )

    # Set the execution dependency: t1 -> t2 -> t3
    t1 >> t2 >> t3