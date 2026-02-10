#!/bin/bash
# Discord 机器人启动脚本

# 进入脚本所在目录
cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在,请先运行: uv sync"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ .env 文件不存在,请先创建并配置"
    echo "提示: cp .env.example .env"
    exit 1
fi

# 激活虚拟环境并运行
echo "🚀 启动 Discord 机器人..."
source .venv/bin/activate
python apps/oc-discord/main.py
