# bot.ps1 - Run in terminal 4 (Discord bot)
# Usage: powershell -ExecutionPolicy Bypass -File D:\project\devpost_hackton\incident-bot\bot.ps1
# Requires: DISCORD_TOKEN in .env (and optional DISCORD_GUILD_ID for instant sync)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Install discord.py if missing (one-time)
$marker = Join-Path $PSScriptRoot "venv\Lib\site-packages\discord"
if (-not (Test-Path -LiteralPath $marker)) {
    Write-Host "=== Installing discord.py (first run) ===" -ForegroundColor Yellow
    & "$PSScriptRoot\venv\Scripts\python.exe" -m pip install -r "$PSScriptRoot\requirements.txt"
}

Write-Host "=== Starting Discord bot ===" -ForegroundColor Cyan
Write-Host "Make sure FastAPI server is running (start.ps1)" -ForegroundColor Yellow
Write-Host ""

& "$PSScriptRoot\venv\Scripts\python.exe" -m src.discord_bot
