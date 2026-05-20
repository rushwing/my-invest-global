#!/usr/bin/env bash
# One-time environment setup for my-invest-global.
# Run once after cloning: bash scripts/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "→ 创建虚拟环境..."
uv venv

echo "→ 安装依赖 (core + data + macro)..."
uv sync --extra data --extra macro

echo "→ 初始化数据目录..."
mkdir -p data/{db,processed,cache,agent_input/cn}

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠  已创建 .env — 请编辑以下两项："
    echo "   DASHBOARD_PASSPHRASE_HASH  → 运行以下命令生成："
    echo "   uv run python -c \"import bcrypt; print(bcrypt.hashpw(b'你的口令', bcrypt.gensalt()).decode())\""
    echo "   ANTHROPIC_API_KEY          → 填入你的 Anthropic API Key"
    echo ""
else
    echo "→ .env 已存在，跳过创建"
fi

echo "✓ 完成。运行 ./scripts/start.sh 启动仪表盘。"
