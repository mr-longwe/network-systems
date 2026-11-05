# Launch script for Edge Video Monitoring System
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "LOCAL EDGE VIDEO MONITORING SYSTEM" -ForegroundColor Green
Write-Host "Host IP: 192.168.1.161 | Port: 8000" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green

$pythonExe = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[!] Virtual environment not found at .venv. Creating..." -ForegroundColor Yellow
    python -m venv .venv
    & .\.venv\Scripts\pip.exe install -r requirements.txt
}

Write-Host "[*] Launching Edge Server..." -ForegroundColor Cyan
& $pythonExe scripts\run_server.py

