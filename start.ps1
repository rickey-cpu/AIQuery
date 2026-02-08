# AI Query Agent - Start Script (PowerShell)
# Run: .\start.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   AI Query Agent - Starting..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check directory
if (-not (Test-Path "main.py")) {
    Write-Host "ERROR: main.py not found. Run from project root." -ForegroundColor Red
    exit 1
}

# Install frontend deps if needed
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location frontend
    npm install
    Set-Location ..
}

Write-Host ""
Write-Host "Starting Backend (port 8000)..." -ForegroundColor Green

# Start backend in new terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python main.py" -WindowStyle Normal

Write-Host "Starting Frontend (port 5173)..." -ForegroundColor Green

# Start frontend in new terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Both servers starting!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend:  " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Blue
Write-Host "Frontend: " -NoNewline; Write-Host "http://localhost:5173" -ForegroundColor Blue
Write-Host ""

# Wait a bit then open browser
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host "Browser opened!" -ForegroundColor Green
