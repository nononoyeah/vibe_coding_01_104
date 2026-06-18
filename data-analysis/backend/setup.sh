#!/usr/bin/env bash
# 创建并初始化 backend 独立 Python 虚拟环境
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  echo ">>> 创建虚拟环境 .venv ..."
  python -m venv .venv
fi

if [[ -f .venv/Scripts/python.exe ]]; then
  PY=".venv/Scripts/python.exe"
else
  PY=".venv/bin/python"
fi

echo ">>> 升级 pip 并安装依赖 ..."
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt

echo ""
echo "✅ 环境就绪。激活方式："
if [[ -f .venv/Scripts/activate ]]; then
  echo "   source .venv/Scripts/activate   # Git Bash / Windows"
else
  echo "   source .venv/bin/activate       # Linux / macOS"
fi
echo "   启动服务：uvicorn app.main:app --reload --port 8000"
