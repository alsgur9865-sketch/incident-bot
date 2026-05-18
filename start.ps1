# start.ps1 - Run in terminal 1 (server)
# Usage: powershell -ExecutionPolicy Bypass -File D:\project\devpost_hackton\incident-bot\start.ps1

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Clear stale chaos mode from previous session
Remove-Item Env:CHAOS_MODE -ErrorAction SilentlyContinue

# Kill any zombie process holding port 8000
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Write-Host "=== Starting incident-bot server on :8000 ===" -ForegroundColor Cyan

& "$PSScriptRoot\venv\Scripts\python.exe" -m uvicorn src.main:app --host 127.0.0.1 --port 8000
