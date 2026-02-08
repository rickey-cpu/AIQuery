@echo off
echo ========================================
echo    AI Query Agent - Starting...
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "main.py" (
    echo ERROR: main.py not found. Run from project root.
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found in PATH
    pause
    exit /b 1
)

REM Install frontend dependencies if needed
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

echo.
echo Starting Backend (port 8000)...
start "AI Query - Backend" cmd /k "python main.py"

echo Starting Frontend (port 5173)...
cd frontend
start "AI Query - Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo    Both servers starting!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Press any key to open frontend in browser...
pause >nul

start http://localhost:5173
