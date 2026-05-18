# dashboard.ps1 - Run in terminal 3 (after start.ps1 is running)
# Usage: powershell -ExecutionPolicy Bypass -File D:\project\devpost_hackton\incident-bot\dashboard.ps1

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Install streamlit if missing (one-time bootstrap)
$marker = Join-Path $PSScriptRoot "venv\Lib\site-packages\streamlit"
if (-not (Test-Path -LiteralPath $marker)) {
    Write-Host "=== Installing dependencies (first run, ~30s) ===" -ForegroundColor Yellow
    & "$PSScriptRoot\venv\Scripts\python.exe" -m pip install -r "$PSScriptRoot\requirements.txt"
}

Write-Host "=== Launching Streamlit dashboard ===" -ForegroundColor Cyan
Write-Host "Browser opens automatically at http://localhost:8501" -ForegroundColor Cyan
Write-Host ""

& "$PSScriptRoot\venv\Scripts\python.exe" -m streamlit run "$PSScriptRoot\dashboard.py"
