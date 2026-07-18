param(
    [string]$EnvFile = ".env.host",
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot

function Read-DotEnv {
    param([string]$Path)
    $result = @{}
    if (-not (Test-Path $Path)) { return $result }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) { continue }
        $parts = $trimmed.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $result[$key] = $value
    }
    return $result
}

function Get-Setting {
    param([hashtable]$Settings, [string]$Name, [string]$Default)
    if ($Settings.ContainsKey($Name) -and $Settings[$Name] -ne "") { return [string]$Settings[$Name] }
    return $Default
}

function Resolve-ConfiguredPath {
    param([string]$BasePath, [string]$ConfiguredPath)
    if ([System.IO.Path]::IsPathRooted($ConfiguredPath)) {
        return [System.IO.Path]::GetFullPath($ConfiguredPath)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $BasePath $ConfiguredPath))
}

function Convert-ToBool {
    param([string]$Value)
    return @("1", "true", "yes", "on") -contains $Value.Trim().ToLowerInvariant()
}

function Write-JsonAtomic {
    param([string]$Path, [hashtable]$Value)
    $tmp = "$Path.tmp"
    $Value | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}

$envPath = Join-Path $ProjectRoot $EnvFile
$settings = Read-DotEnv $envPath
$hostDirRaw = Get-Setting $settings "PALWORLD_HOST_DIR" ".\host-palworld"
$HostDir = Resolve-ConfiguredPath -BasePath $ProjectRoot -ConfiguredPath $hostDirRaw
$ControlDir = Join-Path $ProjectRoot "runtime\control"
$StatusFile = Join-Path $ControlDir "status.json"
$PidFile = Join-Path $ControlDir "server.pid"
$ServerExe = Join-Path $HostDir "PalServer.exe"
$StopTimeout = [int](Get-Setting $settings "PALWORLD_HOST_STOP_TIMEOUT_SECONDS" "60")
$Port = Get-Setting $settings "PALWORLD_HOST_PORT" "8211"
$QueryPort = Get-Setting $settings "PALWORLD_HOST_QUERY_PORT" "27015"
$PublicLobby = Convert-ToBool (Get-Setting $settings "PALWORLD_HOST_PUBLIC_LOBBY" "true")
$PerfArgs = Convert-ToBool (Get-Setting $settings "PALWORLD_HOST_PERF_ARGS" "false")
$WorkerThreads = Get-Setting $settings "PALWORLD_HOST_WORKER_THREADS" ""
$ExtraArgs = Get-Setting $settings "PALWORLD_HOST_EXTRA_ARGS" ""

New-Item -ItemType Directory -Force -Path $ControlDir | Out-Null
New-Item -ItemType Directory -Force -Path $HostDir | Out-Null

$script:ServerProcess = $null
$script:StartedAt = $null

function Find-ServerProcess {
    if ($script:ServerProcess -and -not $script:ServerProcess.HasExited) { return $script:ServerProcess }
    if (Test-Path $PidFile) {
        $pidText = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($pidText -match '^\d+$') {
            $candidate = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
            if ($candidate) {
                $script:ServerProcess = $candidate
                return $candidate
            }
        }
    }
    $candidate = $null
    foreach ($processName in @("PalServer-Win64-Test-Cmd", "PalServer-Win64-Test", "PalServer-Win64-Shipping", "PalServer")) {
        $candidate = Get-Process -Name $processName -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($candidate) { break }
    }
    if ($candidate) {
        $script:ServerProcess = $candidate
        Set-Content -LiteralPath $PidFile -Value $candidate.Id -Encoding ASCII
    }
    return $candidate
}

function Get-ArgumentList {
    $result = @("-port=$Port", "-queryport=$QueryPort")
    if ($PublicLobby) { $result += "-publiclobby" }
    if ($PerfArgs) {
        $result += @("-useperfthreads", "-NoAsyncLoadingThread", "-UseMultithreadForDS")
    }
    if ($WorkerThreads -match '^\d+$' -and [int]$WorkerThreads -gt 0) {
        $result += "-NumberOfWorkerThreadsServer=$WorkerThreads"
    }
    if ($ExtraArgs) {
        $parseErrors = $null
        $tokens = [System.Management.Automation.PSParser]::Tokenize($ExtraArgs, [ref]$parseErrors)
        if ($parseErrors -and $parseErrors.Count -gt 0) {
            throw "PALWORLD_HOST_EXTRA_ARGS parse error: $($parseErrors[0].Message)"
        }
        $result += $tokens | Where-Object { $_.Type -in @('CommandArgument', 'Command') } | ForEach-Object { $_.Content }
    }
    return $result
}

function Start-PalworldServer {
    $existing = Find-ServerProcess
    if ($existing) { return @{ ok = $true; message = "Server already running"; pid = $existing.Id } }
    if (-not (Test-Path $ServerExe)) {
        throw "ไม่พบ $ServerExe กรุณารัน 00-Setup.bat ก่อน"
    }
    $arguments = Get-ArgumentList
    Write-Host "Starting Palworld host server: $ServerExe $($arguments -join ' ')"
    $script:ServerProcess = Start-Process -FilePath $ServerExe -ArgumentList $arguments -WorkingDirectory $HostDir -PassThru
    $script:StartedAt = (Get-Date).ToString("o")
    Set-Content -LiteralPath $PidFile -Value $script:ServerProcess.Id -Encoding ASCII
    Start-Sleep -Seconds 2
    $active = Find-ServerProcess
    if (-not $active) {
        throw "PalServer.exe หยุดทันทีหลัง Start"
    }
    return @{ ok = $true; message = "Server started"; pid = $active.Id }
}

function Stop-PalworldServer {
    $process = Find-ServerProcess
    if (-not $process) {
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        return @{ ok = $true; message = "Server already stopped" }
    }
    $deadline = (Get-Date).AddSeconds($StopTimeout)
    $active = $process
    while ((Get-Date) -lt $deadline) {
        $active = Find-ServerProcess
        if (-not $active) { break }
        Start-Sleep -Seconds 1
    }
    $active = Find-ServerProcess
    if ($active) {
        Write-Warning "Server did not exit after REST shutdown timeout; stopping process tree."
        & taskkill.exe /PID $active.Id /T /F | Out-Null
        Start-Sleep -Seconds 2
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    $script:ServerProcess = $null
    return @{ ok = $true; message = "Server stopped" }
}

function Write-AgentStatus {
    $process = Find-ServerProcess
    $running = $null -ne $process
    $status = @{
        agent = "windows-powershell"
        running = $running
        status = $(if ($running) { "running" } else { "stopped" })
        pid = $(if ($running) { $process.Id } else { $null })
        started_at = $script:StartedAt
        finished_at = $(if ($running) { $null } else { (Get-Date).ToString("o") })
        heartbeat_at = (Get-Date).ToString("o")
        host_dir = $HostDir
    }
    Write-JsonAtomic -Path $StatusFile -Value $status
}

function Process-ControlRequests {
    Get-ChildItem -LiteralPath $ControlDir -Filter "request-*.json" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime |
        ForEach-Object {
            $requestFile = $_.FullName
            try {
                $request = Get-Content -LiteralPath $requestFile -Raw -Encoding UTF8 | ConvertFrom-Json
                $response = switch ($request.action) {
                    "start" { Start-PalworldServer }
                    "stop" { Stop-PalworldServer }
                    default { throw "Unsupported action: $($request.action)" }
                }
            } catch {
                $response = @{ ok = $false; error = $_.Exception.Message }
            }
            $response["id"] = $request.id
            $response["responded_at"] = (Get-Date).ToString("o")
            $responseFile = Join-Path $ControlDir "response-$($request.id).json"
            Write-JsonAtomic -Path $responseFile -Value $response
            Remove-Item -LiteralPath $requestFile -Force -ErrorAction SilentlyContinue
        }
}

Write-Host "Palworld Host Agent 1.1.0"
Write-Host "Project: $ProjectRoot"
Write-Host "Host data: $HostDir"
Write-Host "Control: $ControlDir"

if (-not $NoStart) {
    try { Start-PalworldServer | Out-Null } catch { Write-Error $_; exit 1 }
}

try {
    while ($true) {
        Process-ControlRequests
        Write-AgentStatus
        Start-Sleep -Milliseconds 750
    }
} finally {
    Write-JsonAtomic -Path $StatusFile -Value @{
        agent = "windows-powershell"
        running = $null -ne (Find-ServerProcess)
        status = "agent-stopped"
        heartbeat_at = (Get-Date).ToString("o")
    }
}
