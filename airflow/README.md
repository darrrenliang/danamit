kubectl create namespace dev

helm repo add minio https://charts.min.io/
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add apache-airflow https://airflow.apache.org

helm repo update

helm install minio minio/minio \
  --namespace dev \
  -f minio-values.yaml

helm install postgresql-01 bitnami/postgresql \
--namespace dev \
-f 01-postgresql-values.yaml

helm install postgresq-02 bitnami/postgresql \
--namespace dev \
-f 02-postgresql-values.yaml


docker build -t aws-psql-client:latest .
docker run --rm -it aws-psql-client:latest /bin/bash



export AWS_ACCESS_KEY_ID=admin
export AWS_SECRET_ACCESS_KEY=adminadmin
export AWS_ENDPOINT_URL=http://minio.dev.svc.cluster.local:9000
aws s3 ls

psql -h poc-01.dev.svc.cluster.local -U postgres -d airflow

pg_isready -h poc-01.dev.svc.cluster.local -p 5432 -U postgres

```
-- 1. 建立一個簡單的 schema (選用，通常用 public 即可，但專業作法會分開)
CREATE SCHEMA IF NOT EXISTS app_schema;

-- 2. 建立一張簡單的資料表 (以使用者清單為例)
CREATE TABLE app_schema.users (
    id SERIAL PRIMARY KEY,           -- 自動遞增的 ID
    username TEXT NOT NULL,          -- 使用者名稱
    email TEXT UNIQUE NOT NULL,      -- 信箱
    created_at TIMESTAMP DEFAULT NOW() -- 建立時間
);

-- 3. 新增一筆測試資料
INSERT INTO app_schema.users (username, email) 
VALUES ('darren', 'darren@example.com');

-- 4. 查詢看看是否成功
SELECT * FROM app_schema.users;

-- 退出 psql
\q
```


helm pull apache-airflow/airflow --version 1.19.0 

helm install airflow apache-airflow/airflow  \
--version 1.16.0 \
--namespace dev \
-f airflow-values.yaml

helm template airflow apache-airflow/airflow  \
--version 1.16.0 \
--namespace dev \
-f airflow-values.yaml > output.yaml
