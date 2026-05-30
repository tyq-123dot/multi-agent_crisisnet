@echo off
echo ========================================
echo CrisisNet 前端启动脚本
echo ========================================
echo.

cd frontend

echo [1/3] 检查 node_modules...
if not exist "node_modules" (
    echo 正在安装依赖...
    call npm install
)

echo.
echo [2/3] 检查 Tailwind CSS...
echo.

echo [3/3] 启动开发服务器...
echo.
echo 前端将在 http://localhost:3000 启动
echo.
call npm start

pause
