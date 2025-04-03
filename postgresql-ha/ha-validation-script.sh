#!/bin/bash
set -euo pipefail

# 請根據實際環境修改以下參數
NAMESPACE="dev"
DATABASE="postgres"
USER="postgres"

# 定義 Pod 名稱
INSERT_POD="poc-pg-ha-dev-fz1-postgresql-0"
QUERY_PODS=("poc-pg-ha-dev-fz1-postgresql-1" "poc-pg-ha-dev-fz1-postgresql-2")

echo "在 Pod ${INSERT_POD} 插入測試資料..."

# 在 INSERT_POD 中建立資料表（如果尚未存在）
kubectl exec -n "$NAMESPACE" "$INSERT_POD" -- \
  psql -U "$USER" -d "$DATABASE" -c "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, name VARCHAR(50));"

# 使用當前 UNIX 時間作為唯一識別，建立測試資料
TEST_VALUE="test_data_$(date +%s)"
kubectl exec -n "$NAMESPACE" "$INSERT_POD" -- \
  psql -U "$USER" -d "$DATABASE" -c "INSERT INTO test_table (name) VALUES ('$TEST_VALUE');"

echo "已在 ${INSERT_POD} 插入測試資料: ${TEST_VALUE}"

# 等待一段時間讓資料同步（根據實際情況調整等待時間）
echo "等待 5 秒讓資料同步..."
sleep 5

# 在每個查詢 Pod 中查詢剛剛插入的資料
for pod in "${QUERY_PODS[@]}"; do
  echo "從 Pod ${pod} 查詢資料..."
  kubectl exec -n "$NAMESPACE" "$pod" -- \
    psql -U "$USER" -d "$DATABASE" -c "SELECT * FROM test_table WHERE name = '$TEST_VALUE';"
done