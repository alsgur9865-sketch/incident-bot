# verify.ps1 - Run in terminal 2 (after start.ps1 is running in terminal 1)
# Usage: powershell -ExecutionPolicy Bypass -File D:\project\devpost_hackton\incident-bot\verify.ps1

$ErrorActionPreference = "Continue"

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$base = "http://localhost:8000"

function Show-Step {
    param([string]$Title, [scriptblock]$Block)
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan
    try {
        & $Block
    } catch {
        Write-Host "[ERROR] $_" -ForegroundColor Red
    }
}

Show-Step "STEP 0 - HEALTH CHECK - expect version 0.4.0 and chaos_mode False" {
    irm "$base/" | ConvertTo-Json -Depth 5
}

Show-Step "STEP 1 - STATS RESET - counters back to zero" {
    irm "$base/stats/reset" -Method POST | ConvertTo-Json -Depth 5
}

Show-Step "STEP 2 - SENTRY AND LOGS TOOLS - expect both in tool_calls_made" {
    $body = '{"message":"check sentry errors and logs in api-gateway"}'
    irm "$base/chat/tools" -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 10
}

Show-Step "STEP 3 - CHAOS ON - expect chaos_mode True" {
    irm "$base/chaos/toggle" -Method POST | ConvertTo-Json -Depth 5
}

Show-Step "STEP 4 - CHAOS ON CALL - expect source cache or graceful" {
    $body = '{"message":"check recent commits"}'
    irm "$base/chat/tools" -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 10
}

Show-Step "STEP 5 - CHAOS OFF - expect chaos_mode False" {
    irm "$base/chaos/toggle" -Method POST | ConvertTo-Json -Depth 5
}

Show-Step "STEP 6 - FINAL STATS - expect user_dropped_count 0" {
    irm "$base/stats" | ConvertTo-Json -Depth 5
}

Write-Host ""
Write-Host "=== DONE - copy all output above and paste it back to chat ===" -ForegroundColor Green
