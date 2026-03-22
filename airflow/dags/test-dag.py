from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

BUCKET_NAME = "airflow"
FILE_NAME = "hello_minio.json"

def create_data_func():
    return {"message": "Hello from Airflow!", "timestamp": str(datetime.now())}

def upload_func(ti):
    # 從上一個 task 抓取資料 (XComs)
    data = ti.xcom_pull(task_ids='create_data')
    s3 = S3Hook(aws_conn_id='minio_conn')
    
    # 如果 Bucket 不存在就建立
    if not s3.check_for_bucket(BUCKET_NAME):
        s3.create_bucket(BUCKET_NAME)
        
    s3.load_string(str(data), FILE_NAME, BUCKET_NAME, replace=True)

def check_func():
    s3 = S3Hook(aws_conn_id='minio_conn')
    exists = s3.check_for_key(FILE_NAME, BUCKET_NAME)
    print(f"檔案 {FILE_NAME} 是否存在: {exists}")

with DAG(
    'simple_minio_dag',
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False
) as dag:

    t1 = PythonOperator(task_id='create_data', python_callable=create_data_func)
    t2 = PythonOperator(task_id='upload_to_minio', python_callable=upload_func)
    t3 = PythonOperator(task_id='check_result', python_callable=check_func)

    # 設定依賴關係：t1 -> t2 -> t3
    t1 >> t2 >> t3