# RuralCare / LifeLine — Windows Startup Script
# Run from the repository root: .\run_all.ps1
#
# Services started:
#   Port 5000 — Person 2: Voice Intake Flask API
#   Port 8000 — Person 3: Decision Engine FastAPI (includes Person 1 rules_engine)
#   Port 5173 — Person 4: React Dashboard (Vite dev server)
#
# IMPORTANT: This must be run from the repository root so that the `rules_engine`
# package is importable by the decision_engine module.

$repoRoot = $PSScriptRoot
Set-Location $repoRoot

Write-Host "=== RuralCare / LifeLine — Starting All Services ===" -ForegroundColor Cyan
Write-Host "Repository root: $repoRoot" -ForegroundColor Gray

Write-Host "`n[1/3] Starting Person 2: Voice Intake API (Port 5000)..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "-m", "voice_intake.app.main" -WorkingDirectory $repoRoot

Start-Sleep 2

Write-Host "[2/3] Starting Person 3: Decision Engine API (Port 8000)..." -ForegroundColor Green
# Must run from repo root so rules_engine is on the Python path
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "decision_engine.app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $repoRoot

Start-Sleep 2

Write-Host "[3/3] Starting Person 4: React Dashboard (Port 5173)..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WorkingDirectory "$repoRoot\dashboard\app"


Write-Host "`n=== All services started! ===" -ForegroundColor Cyan
Write-Host "Patient interface : http://localhost:5173" -ForegroundColor Yellow
Write-Host "Doctor dashboard  : http://localhost:5173/doctor/login" -ForegroundColor Yellow
Write-Host "Voice Intake API  : http://localhost:5000/health" -ForegroundColor Gray
Write-Host "Decision Engine   : http://localhost:8000/health" -ForegroundColor Gray
Write-Host "`nPress Ctrl+C to stop this script (background processes will continue)." -ForegroundColor Gray

while ($true) { Start-Sleep -Seconds 5 }
