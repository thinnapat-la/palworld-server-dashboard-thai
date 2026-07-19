param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop")]
    [string]$Action,
    [int]$TimeoutSeconds = 90,
    [switch]$SkipRestShutdown
)
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ControlDir = Join-Path $ProjectRoot "runtime\control"
$envFile = Join-Path $ProjectRoot ".env.host"
$settings = @{}
if (Test-Path $envFile) {
    foreach ($line in Get-Content -LiteralPath $envFile -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) { continue }
        $parts = $trimmed.Split("=", 2)
        $settings[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
    }
}
if ($Action -eq "stop" -and -not $SkipRestShutdown) {
    $adminPassword = if ($settings.ContainsKey("PALWORLD_ADMIN_PASSWORD")) { $settings["PALWORLD_ADMIN_PASSWORD"] } else { "" }
    $restPort = if ($settings.ContainsKey("PALWORLD_HOST_REST_PORT")) { $settings["PALWORLD_HOST_REST_PORT"] } else { "8212" }
    if ($adminPassword) {
        $token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:$adminPassword"))
        $headers = @{ Authorization = "Basic $token" }
        try {
            Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$restPort/v1/api/save" -Headers $headers -TimeoutSec 15 | Out-Null
            Write-Host "Save World: requested"
        } catch {
            Write-Warning "REST save failed before stop: $($_.Exception.Message)"
        }

        $restStopRequested = $false
        try {
            # waittime=0 returns HTTP 400 on some Palworld 1.0 server builds.
            $body = @{ waittime = 1; message = "Host script shutdown" } | ConvertTo-Json -Compress
            Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$restPort/v1/api/shutdown" -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 15 | Out-Null
            $restStopRequested = $true
            Write-Host "REST shutdown: requested (1 second)"
        } catch {
            Write-Warning "REST shutdown failed: $($_.Exception.Message)"
        }

        if (-not $restStopRequested) {
            try {
                Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$restPort/v1/api/stop" -Headers $headers -TimeoutSec 15 | Out-Null
                $restStopRequested = $true
                Write-Host "REST force-stop: requested after Save World"
            } catch {
                Write-Warning "REST force-stop failed; Host Agent/process fallback will be used: $($_.Exception.Message)"
            }
        }
    }
}
New-Item -ItemType Directory -Force -Path $ControlDir | Out-Null
$id = [guid]::NewGuid().ToString("N")
$request = Join-Path $ControlDir "request-$id.json"
$response = Join-Path $ControlDir "response-$id.json"
@{ id=$id; action=$Action; requested_at=(Get-Date).ToString("o") } | ConvertTo-Json | Set-Content -LiteralPath $request -Encoding UTF8
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    if (Test-Path $response) {
        $result = Get-Content -LiteralPath $response -Raw -Encoding UTF8 | ConvertFrom-Json
        Remove-Item -LiteralPath $response -Force -ErrorAction SilentlyContinue
        if (-not $result.ok) { throw $result.error }
        Write-Host $result.message
        exit 0
    }
    Start-Sleep -Milliseconds 500
}
throw "Host Agent did not respond within $TimeoutSeconds seconds"
