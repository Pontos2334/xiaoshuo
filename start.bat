@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   Novel Assistant - Start Script
echo ========================================
echo.

echo [1/2] Starting backend...
cd backend
start cmd /k "title Novel-Assistant-Backend && python -m uvicorn app.main:app --reload --port 8002"
cd ..

timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend...
cd frontend
start cmd /k "title Novel-Assistant-Frontend && npm run dev"
cd ..

echo.
echo ========================================
echo   Services Started
echo ========================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8002
echo   API Docs: http://localhost:8002/docs
echo.
echo   Press any key to exit...
pause >nul
