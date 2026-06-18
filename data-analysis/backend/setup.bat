@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
  echo ^>^>^> 创建虚拟环境 .venv ...
  python -m venv .venv
)

echo ^>^>^> 升级 pip 并安装依赖 ...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo ✅ 环境就绪。激活方式：
echo    .venv\Scripts\activate
echo    启动服务：uvicorn app.main:app --reload --port 8000
