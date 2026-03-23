@echo off
echo ========================================
echo   小说创作助手 - 启动脚本
echo ========================================
echo.

:: 启动后端
echo [1/2] 启动后端服务...
cd backend
start cmd /k "title 小说创作助手-后端 && python -m uvicorn app.main:app --reload --port 8000"
cd ..

:: 等待后端启动
timeout /t 3 /nobreak > nul

:: 启动前端
echo [2/2] 启动前端服务...
cd frontend
start cmd /k "title 小说创作助手-前端 && npm run dev"
cd ..

echo.
echo ========================================
echo   服务已启动！
echo ========================================
echo.
echo   前端: http://localhost:3000
echo   后端: http://localhost:8000
echo   API文档: http://localhost:8000/docs
echo.
echo   按任意键退出...
pause > nul
