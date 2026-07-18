param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop")]
    [string]$Action,
    [int]$TimeoutSeconds = 90
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
if ($Action -eq "stop") {
    $adminPassword = if ($settings.ContainsKey("PALWORLD_ADMIN_PASSWORD")) { $settings["PALWORLD_ADMIN_PASSWORD"] } else { "" }
    $restPort = if ($settings.ContainsKey("PALWORLD_HOST_REST_PORT")) { $settings["PALWORLD_HOST_REST_PORT"] } else { "8212" }
    if ($adminPassword) {
        try {
            $token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:$adminPassword"))
            $headers = @{ Authorization = "Basic $token" }
            $body = @{ waittime = 0; message = "Host script shutdown" } | ConvertTo-Json
            Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$restPort/v1/api/shutdown" -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 15 | Out-Null
        } catch {
            Write-Warning "REST shutdown failed; Host Agent will wait and then force-stop if necessary: $($_.Exception.Message)"
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
