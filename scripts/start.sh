#!/usr/bin/env bash
# Start the My Invest Global dashboard.
# Usage: bash scripts/start.sh [--port 8501]
set -euo pipefail
cd "$(dirname "$0")/.."

PORT=${2:-8501}
if [[ "${1:-}" == "--port" ]]; then
    PORT=$2
fi

if [ ! -d ".venv" ]; then
    echo "→ 虚拟环境不存在，先运行 setup..."
    bash scripts/setup.sh
fi

if [ ! -f ".env" ]; then
    echo "⚠  未找到 .env 文件。请先运行: bash scripts/setup.sh"
    exit 1
fi

echo "→ 启动仪表盘 http://localhost:${PORT}"
uv run streamlit run app/dashboard.py \
    --server.port "${PORT}" \
    --server.headless true \
    --browser.gatherUsageStats false
