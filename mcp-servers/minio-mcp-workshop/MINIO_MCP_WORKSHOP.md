🛠️ Workshop: 打造你的 SRE 專屬 MinIO MCP Server
本工作坊將帶領你建置一個具備「生產環境感知能力」的 MCP Server，讓 Claude Code 能夠安全、高效地操作你的 MinIO 儲存空間。

🎯 目標
實作具備 1MB 預覽與 Tail 功能的 MCP Tool。

掌握 boto3 在 S3-compatible 儲存系統的安全性配置。

將 MinIO 操作完全整合進 Claude Code 工作流。

🏗️ 第一階段：開發環境配置
首先，我們使用 uv 建立一個乾淨的開發空間。

```Bash
# 安裝uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env 

# 建立專案目錄
mkdir minio-mcp-workshop && cd minio-mcp-workshop

# 初始化虛擬環境並安裝依賴
# uv venv
source .venv/bin/activate
uv init
uv add "mcp[fastmcp]" boto3

# deploy a minio standalone cluster
helm install minio minio/minio \
--namespace dev \
-f ./deployment/minio-values.yaml


export MINIO_ENDPOINT="http://minio.dev.svc.cluster.local:9000"
export MINIO_ACCESS_KEY="admin"
export MINIO_SECRET_KEY="adminadmin"

uv run mcp dev minio_server.py 
```

