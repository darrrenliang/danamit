## Scheduler
- Airflow scheduler 是 Airflow 核心元件之一，它負責「看哪些 DAG 該執行」，然後「安排哪些 task 要送給 worker 去跑」。
- Scheduler 負責掃描 DAG、排程執行 DAG Run 和 Task Instance，然後把任務丟給 Executor 執行。
- `replicas`: Airflow 2.0 allows users to run multiple schedulers, However this feature is only recommended for MySQL 8+ and Postgres
- Airflow 2.7+ 支援 scheduler HA 模式，你可以跑多個 scheduler，但只有一個是 active，其他是 standby。

![AirflowSchedulerInformation](/danamit/apache-airflow/AirflowSchedulerInformation.png)


## Triggerer
- triggerer 是負責監聽「等待條件完成」的輕量級元件，幫忙在特定條件達成時重新喚醒任務（不需要佔用 worker）。

⚙️ Triggerer 是怎麼運作的？
- 每個 deferrable operator 都會 yield 一個 Trigger，Triggerer 會非同步地跑它們的 run 方法，直到它觸發完成，然後通知 scheduler 任務可以繼續。

🔍 Triggerer 的工作內容
  	1.	接收 deferrable operator 進入「等待中」的狀態
  	2.	使用非同步協程（async I/O）監控外部條件（如 sensor, webhook）
  	3.	條件滿足時，喚醒該任務繼續執行，交還給 worker
🎯 哪些東西需要 triggerer？
  - 凡是「可延遲」的 Operators（多數是新版的 sensors）都會透過 triggerer 來等待事件：
    - AsyncSensor（如 AsyncHttpSensor, AsyncS3Sensor 等）
    - ExternalTaskSensor（deferrable）
    - TimeSensorAsync
    - 自定義的 deferrable operator


## dagProcessor
- dagProcessor 是負責定期掃描 DAG 檔案並解析 DAG 結構，將它們送進 Metadata DB 或 scheduler 的元件。

Non-serialized DAGs --> Scheduler、Webserver 自己讀 .py 檔案
Serialized DAGs ✅  --> 專門由 dagProcessor 處理 DAG，再寫進 Metadata DB，Webserver & Scheduler 從那裡讀


🎯 dagProcessor 的功能
- 掃描 DAGs 資料夾中的 .py 檔案
- 執行 import、解析 DAG 結構
- 序列化（Serialize）DAG 並寫入 metadata database
- Scheduler 與 Webserver 從 DB 讀取 DAG，而不是自己載入 DAG 原始碼（效能更好）

📦 為什麼需要獨立出 dagProcessor？
- ✅ 降低 Webserver 和 Scheduler 負擔
- ✅ 避免每個 component 各自解析 DAG，造成重複運算
- ✅ 幫助 DAG 解析更穩定與可控（可獨立 scale）


❗ 注意：dagProcessor 只在啟用序列化時才發揮作用

- 需要在 Airflow config 中啟用，否則 Webserver 和 Scheduler 還是會自己讀 .py 檔案。
```
airflow:
  config:
    AIRFLOW__CORE__STORE_SERIALIZED_DAGS: "true"
    AIRFLOW__CORE__DAG_SERIALIZER: "airflow.serialization.serialized_objects"
```

## pgbouncer
- pgbouncer 是一個輕量級的 PostgreSQL 連線池（connection pooler），它的主要任務是幫忙管理和優化與 PostgreSQL 資料庫之間的連線，減少資源消耗、提升效率與可擴展性。
- pgbouncer 讓你可以同時支援大量應用連線，而不讓 PostgreSQL 本身被連線數壓垮。

![PgbouncerInformation](/danamit/images/PgbouncerInformation.png)

📌 為什麼在 Airflow 裡會想用 pgbouncer？

Airflow 各個元件（Scheduler、Webserver、Worker、Triggerer、DagProcessor）都會連 PostgreSQL metadata DB。

每個元件預設可能會開數十個 connection，如果沒有控制，幾個元件加起來就會超過 PostgreSQL 的 max_connections，導致：
- ❌ DAG 掛掉
- ❌ Task 卡住
- ❌ Web UI 無法開啟

✨ pgbouncer 能在這裡幫你集中處理連線，只讓 10~20 條連線給 PostgreSQL，但服務多個元件。

![PgbouncerInformation](/danamit/images/PgbouncerOperationMode.png)

💡 什麼時候該加 pgbouncer？
- 你用的應用（例如 Airflow、Superset、Metabase、Grafana）開超多連線
- PostgreSQL 負載飆高
- 出現 too many connections 錯誤
- 想在高併發下擴容而不改 PostgreSQL 設定

`maxClientConn`: Maximum clients that can connect to PgBouncer (higher = more file descriptors)



## Can pgbouncer 對接到 pgpool-II ?
- 當你把 pgbouncer 對接到 pgpool-II（或反過來），這其實是一種「連線代理疊加連線代理」的架構，要特別注意運作方式與效能瓶頸，才能發揮雙方優勢。

🤝 基本架構
```
[Airflow / App]
    ↓
pgbouncer  (連線池 + 快速切換)
    ↓
pgpool-II  (負載平衡 / 讀寫分離 / Failover)
    ↓
PostgreSQL 主 + 從 節點
```

🔍 pgbouncer + pgpool 各自負責什麼？
- pgbouncer	--> 快速連線池（減少 app 端連線數、快取連線）
- pgpool-II	--> 讀寫分離、主從同步監控、Failover、自動切換主節點

🔄 流程說明
  1.  App 連接到 pgbouncer（如 Airflow）
  2.  pgbouncer 建立少數實體連線，對接 pgpool-II
  3.  pgpool-II 根據 SQL 判斷是否為讀/寫，轉發給主節點或 replica
  4.  整個連線流程從 app 看起來仍是單一點（connection endpoint）
  
⚠️ 注意事項

1. pgbouncer 的 pooling 模式 務必是 session 或 transaction
	•	pgbouncer 不理解 SQL 本身，不知道一個語句是 SELECT 還是 INSERT
	•	所以如果用 statement 模式會打亂 pgpool-II 的連線語境（破壞事務）

✅ 建議設定：
```
[pgbouncer]
pool_mode = transaction
```

2. pgbouncer 對 pgpool 是「共享一組 DB 資訊」，帳號密碼要一致
	•	建議在 pgpool-II 設定好 user 與密碼，再把同一組帳號給 pgbouncer 用
	•	pgbouncer 不會做身份驗證，只 pass-through，驗證由 pgpool 負責

3. 加了 pgbouncer 會損失 pgpool-II 的一部分功能

例如：
	•	connection-level 的 SQL rewrite 或 failover 可能不會生效
	•	pgbouncer 把多個 app connection 合併成一個時，有些 session 變數會衝突
	•	有些 session-based 操作（如 temp tables）會被切斷

✅ 哪種情境適合用 pgbouncer + pgpool？

- 條件	建議:
  - 多個 app 接入 PostgreSQL，每個都會暴力開很多連線	✅ 加 pgbouncer
  - 有主從架構、希望自動 failover 或讀寫分離	✅ 加 pgpool-II
  - 希望兼具連線池 + failover 功能	✅ 可以疊加，但要謹慎設定


📌 架構建議（穩定組合）
	•	Option A: App → pgbouncer → PostgreSQL（簡單穩定，低延遲）
	•	Option B: App → pgpool → PostgreSQL（有 failover、讀寫分離）
	•	Option C: App → pgbouncer → pgpool → PostgreSQL（需 tuning）

![AirflowPgbouncerPgpool](/danamit/images/AirflowPgbouncerPgpool.png)