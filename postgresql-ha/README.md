# Postgresql-ha

### Services
- poc-pg-ha-dev-fz1-pgpool: 提供應用程式連線用（pgpool 會自動轉流量）
- poc-pg-ha-dev-fz1-postgresql: 每個 Pod 的 ClusterIP，用於內部連線（可直接連主）
- poc-pg-ha-dev-fz1-postgresql-headless: StatefulSet 專用，Pod 可以彼此溝通
- poc-pg-ha-dev-fz1-postgresql-metrics: 用來讓 Prometheus 收集 PostgreSQL metrics 的

### PODS Architecture (After Initialization) 
  
- PODS: `poc-pg-ha-dev-fz1-postgresql-0 poc-pg-ha-dev-fz1-postgresql-1 poc-pg-ha-dev-fz1-postgresql-2`
  - MASTER: `poc-pg-ha-dev-fz1-postgresql-0`
  - SLAVES: `poc-pg-ha-dev-fz1-postgresql-1` `poc-pg-ha-dev-fz1-postgresql-2`

### Failover 說明

在典型的 PostgreSQL HA 叢集（例如使用 repmgr 或 Patroni 進行自動故障轉移管理）中，如果原本的主節點（例如 poc-pg-ha-dev-fz1-postgresql-0）發生故障並下線，叢集會自動選舉一個現有的 standby（備用節點）升級成為新的主節點。這個選舉的規則依賴於你的 HA 解決方案的配置，例如設定的優先順序、延遲狀態與健康檢查結果。

假設叢集中只有三個節點：poc-pg-ha-dev-fz1-postgresql-0、poc-pg-ha-dev-fz1-postgresql-1 與 poc-pg-ha-dev-fz1-postgresql-2，如果 poc-pg-ha-dev-fz1-postgresql-0（原來的主節點）失效，通常其中一個 standby（例如 poc-pg-ha-dev-fz1-postgresql-1 或 poc-pg-ha-dev-fz1-postgresql-2）會被自動提升為新的主節點。當 poc-pg-ha-dev-fz1-postgresql-0 復原後，通常它會以 standby 的身份重新加入叢集，並且會從新的主節點進行資料同步。

- 總結：
  - 若 poc-pg-ha-dev-fz1-postgresql-0 掉線，依 HA 解決方案的故障轉移邏輯，poc-pg-ha-dev-fz1-postgresql-1 或 poc-pg-ha-dev-fz1-postgresql-2 其中之一會被自動提升為主節點。
  - 當 poc-pg-ha-dev-fz1-postgresql-0 重啟後，它通常會作為 standby 加入到新的主從架構中，而不會自動成為主節點。



### Pgpool 
每個 PostgreSQL 節點都會裝 repmgr
  - repmgr 是 PostgreSQL 高可用的重要套件，它會：
  - 掃描主從狀態（PostgreSQL 的 streaming replication）
  - 定時心跳檢查
  - 偵測故障
  - 自動 promote 從節點為新的主節點

Pgpool 啟動時會連線到 repmgr，查詢主節點是誰
Pgpool 有設定內部的健康檢查邏輯，它會：
  - 定期 ping 所有 PostgreSQL 節點
  - 查詢哪個節點是 PRIMARY
  - 自動標記該節點為「可寫入」，其他為只讀（SELECT）



### (Commands): Show all nodes status

- Execution
```
kubectl exec -it poc-pg-ha-dev-fz1-postgresql-0 -n dev -- psql -U postgres -d postgres -c "SELECT pg_is_in_recovery();";
kubectl exec -it poc-pg-ha-dev-fz1-postgresql-1 -n dev -- psql -U postgres -d postgres -c "SELECT pg_is_in_recovery();";
kubectl exec -it poc-pg-ha-dev-fz1-postgresql-2 -n dev -- psql -U postgres -d postgres -c "SELECT pg_is_in_recovery();";
```

- Output
```
Defaulted container "postgresql" out of: postgresql, metrics
 pg_is_in_recovery 
-------------------
 f
(1 row)

Defaulted container "postgresql" out of: postgresql, metrics
 pg_is_in_recovery 
-------------------
 t
(1 row)

Defaulted container "postgresql" out of: postgresql, metrics
 pg_is_in_recovery 
-------------------
 t
(1 row)
```

### (Commands) Connect to postgres node in the pgpool container
```
psql -Upostgres -dpostgres -h poc-pg-ha-dev-fz1-postgresql-0.poc-pg-ha-dev-fz1-postgresql-headless.dev.svc.cluster.local
```



### MISC
- master or slave 狀態會被記錄在pvc --> 下掉deployment時建議刪除pvc, 否則重新上線會壞掉
- `podManagementPolicy` 可以設定OrderedReady，會一個完成後才建立下一個節點
- `REPMGRD_START_DELAY` env 可以控制等 ？ 秒再啟動 repmgrd，檢查其他節點是否可以replication
  