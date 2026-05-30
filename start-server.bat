@echo off
echo ========================================
echo CrisisNet WebSocket 服务器启动
echo ========================================
echo.

echo [1/2] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo 错误：Python 未安装或未配置到 PATH
    pause
    exit /b 1
)

echo.
echo [2/2] 启动 WebSocket 服务器...
echo.
echo 服务器将在 http://localhost:8000 启动
echo.
python web_server.py

pause
