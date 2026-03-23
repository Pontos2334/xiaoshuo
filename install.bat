@echo off
echo ========================================
echo   小说创作助手 - 安装脚本
echo ========================================
echo.

:: 检查Python
echo [检查] Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python已安装

:: 检查Node.js
echo [检查] Node.js...
node --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Node.js，请先安装Node.js 18+
    pause
    exit /b 1
)
echo [OK] Node.js已安装

echo.
echo ========================================
echo   安装后端依赖
echo ========================================
cd backend

:: 创建虚拟环境
if not exist "venv" (
    echo [创建] Python虚拟环境...
    python -m venv venv
)

:: 激活虚拟环境并安装依赖
echo [安装] 后端依赖...
call venv\Scripts\activate && pip install -r requirements.txt

cd ..

echo.
echo ========================================
echo   安装前端依赖
echo ========================================
cd frontend

:: 安装npm依赖
echo [安装] 前端依赖...
call npm install

cd ..

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo   运行 start.bat 启动服务
echo.
pause
