# Aspexa Automa - Start All Services
# Runs API Gateway, Test Target Agent, and Viper Command Center

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot

Write-Host "Starting Aspexa Automa Services..." -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Start API Gateway (port 8081)
Write-Host "`n[1/3] Starting API Gateway on port 8081..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot'; .\.venv\Scripts\python.exe -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8081 --reload"

Start-Sleep -Seconds 2

# Start Test Target Agent (port 8082)
Write-Host "[2/3] Starting Test Target Agent on port 8082..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot'; .\.venv\Scripts\python.exe -m uvicorn test_target_agent.main:app --host 0.0.0.0 --port 8082 --reload"

Start-Sleep -Seconds 2

# Start Viper Command Center (Vite dev server)
Write-Host "[3/3] Starting Viper Command Center (frontend)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot\viper-command-center'; npm run dev"

Write-Host "`n=================================" -ForegroundColor Cyan
Write-Host "All services starting!" -ForegroundColor Green
Write-Host "`nEndpoints:" -ForegroundColor Cyan
Write-Host "  API Gateway:        http://localhost:8081" -ForegroundColor White
Write-Host "  API Gateway Docs:   http://localhost:8081/docs" -ForegroundColor White
Write-Host "  Test Target Agent:  http://localhost:8082" -ForegroundColor White
Write-Host "  Target Agent Docs:  http://localhost:8082/docs" -ForegroundColor White
Write-Host "  Viper Command Center: http://localhost:5173 (or check terminal)" -ForegroundColor White
Write-Host "`nEach service runs in its own terminal window." -ForegroundColor Gray
Write-Host "Close the terminal windows to stop the services." -ForegroundColor Gray
