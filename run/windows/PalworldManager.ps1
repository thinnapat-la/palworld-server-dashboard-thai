param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("setup", "start-all", "start-server", "start-dashboard", "stop-dashboard", "stop-server", "stop-all", "restart-server", "status", "logs", "update", "doctor", "configure", "relocate-host")]
    [string]$Action,
    [string]$EnvFile = ".env.host",
    [switch]$Follow
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot
$RuntimeDir = Join-Path $ProjectRoot "runtime"
$ControlDir = Join-Path $RuntimeDir "control"
$LogDir = Join-Path $RuntimeDir "logs"
$AgentPidFile = Join-Path $ControlDir "agent.pid"
$AgentOutLog = Join-Path $LogDir "host-agent.out.log"
$AgentErrLog = Join-Path $LogDir "host-agent.err.log"
$AgentScript = Join-Path $PSScriptRoot "PalworldHostAgent.ps1"
$RequestScript = Join-Path $PSScriptRoot "Request-HostAction.ps1"
$ConfigScript = Join-Path $PSScriptRoot "Configure-PalworldHost.ps1"
$ComposeFile = Join-Path $ProjectRoot "docker-compose.host.yml"
$EnvPath = Join-Path $ProjectRoot $EnvFile
$SteamCmdDir = Join-Path $RuntimeDir "steamcmd-windows"
$SteamCmdExe = Join-Path $SteamCmdDir "steamcmd.exe"
$SteamCmdZip = Join-Path $RuntimeDir "steamcmd-windows.zip"

New-Item -ItemType Directory -Force -Path $ControlDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Read-DotEnv {
    param([string]$Path)
    $result = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $result }
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
    if ($Settings.ContainsKey($Name) -and [string]$Settings[$Name] -ne "") { return [string]$Settings[$Name] }
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

function Get-DefaultShortHostDir {
    $rootPath = [System.IO.Path]::GetPathRoot($ProjectRoot)
    if (-not $rootPath) { $rootPath = "$env:SystemDrive\" }
    return [System.IO.Path]::GetFullPath((Join-Path $rootPath "PalServer"))
}

function Convert-ToEnvPath {
    param([string]$Path)
    return $Path.Replace("\", "/")
}

function Set-DotEnvValue {
    param([string]$Path, [string]$Name, [string]$Value)
    $lines = if (Test-Path -LiteralPath $Path) { @(Get-Content -LiteralPath $Path -Encoding UTF8) } else { @() }
    $replacement = "$Name=$Value"
    $found = $false
    $pattern = "^\s*" + [regex]::Escape($Name) + "\s*="
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match $pattern) {
            $lines[$index] = $replacement
            $found = $true
            break
        }
    }
    if (-not $found) { $lines += $replacement }
    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

function Get-ProjectedSavePathLength {
    param([string]$HostDir)
    $suffix = "\Pal\Saved\SaveGames\0\0123456789ABCDEF0123456789ABCDEF\backup\local\2026.12.31-23.59.59\Players\0123456789ABCDEF0123456789ABCDEF.sav"
    return ($HostDir.TrimEnd('\') + $suffix).Length
}

function Assert-SafeHostPath {
    param([string]$HostDir)
    $projected = Get-ProjectedSavePathLength -HostDir $HostDir
    if ($projected -ge 248) {
        $recommended = Get-DefaultShortHostDir
        throw "PALWORLD_HOST_DIR ยาวเกินไปสำหรับระบบ Save/Backup ของ Palworld Windows`nHost dir: $HostDir`nProjected backup path: $projected characters`nRecommended: $recommended`nรัน run\windows\09-Move-Server-To-Short-Path.bat เพื่อคัดลอก Server/World ไป path สั้นโดยไม่ลบต้นฉบับ"
    }
    if ($projected -ge 220) {
        Write-Warning "PALWORLD_HOST_DIR ค่อนข้างยาว (projected backup path $projected characters). แนะนำ path สั้น เช่น $(Get-DefaultShortHostDir)"
    }
}

function Assert-HostWritable {
    param([string]$HostDir)
    New-Item -ItemType Directory -Force -Path $HostDir | Out-Null
    $probe = Join-Path $HostDir (".palworld-write-test-" + [guid]::NewGuid().ToString('N') + ".tmp")
    try {
        Set-Content -LiteralPath $probe -Value "write-test" -Encoding ASCII
        Remove-Item -LiteralPath $probe -Force
    } catch {
        throw "ไม่มีสิทธิ์เขียน PALWORLD_HOST_DIR: $HostDir`nลองเปิด CMD ด้วย Run as administrator หรือย้ายไป path ที่ผู้ใช้ปัจจุบันเขียนได้`n$($_.Exception.Message)"
    }
}

function Ensure-Env {
    if (-not (Test-Path -LiteralPath $EnvPath)) {
        Copy-Item -LiteralPath (Join-Path $ProjectRoot ".env.host.example") -Destination $EnvPath -Force
        $shortHostDir = Convert-ToEnvPath (Get-DefaultShortHostDir)
        Set-DotEnvValue -Path $EnvPath -Name "PALWORLD_HOST_DIR" -Value $shortHostDir
        Write-Host "Created .env.host"
        Write-Host "Windows server path: $shortHostDir"
        Write-Host "Notepad will open. Edit passwords, save, and close Notepad to continue."
        Start-Process notepad.exe -ArgumentList $EnvPath -Wait
    }
}

function Get-Settings {
    Ensure-Env
    $settings = Read-DotEnv $EnvPath
    $needsEdit = $false
    foreach ($name in @("PALWORLD_ADMIN_PASSWORD", "DASHBOARD_PASSWORD")) {
        $value = Get-Setting $settings $name ""
        if (-not $value -or $value -match "CHANGE_ME") { $needsEdit = $true }
    }
    if ($needsEdit) {
        Write-Host "กรุณาแก้รหัสผ่านใน .env.host แล้ว Save และปิด Notepad"
        Start-Process notepad.exe -ArgumentList $EnvPath -Wait
        $settings = Read-DotEnv $EnvPath
    }
    return $settings
}

function Assert-RequiredSettings {
    param([hashtable]$Settings)
    foreach ($name in @("PALWORLD_ADMIN_PASSWORD", "DASHBOARD_PASSWORD")) {
        $value = Get-Setting $Settings $name ""
        if (-not $value -or $value -match "CHANGE_ME") {
            throw "กรุณาแก้ $name ใน .env.host ก่อน แล้วรันคำสั่งอีกครั้ง"
        }
    }
}

function Assert-Docker {
    & docker version --format '{{.Server.Version}}' *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker Desktop ยังไม่พร้อม กรุณาเปิด Docker Desktop แล้วลองใหม่" }
    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) { throw "ไม่พบ Docker Compose plugin" }
}

function Invoke-Compose {
    param([string[]]$Arguments, [switch]$AllowFailure)
    & docker compose --env-file $EnvPath -f $ComposeFile @Arguments
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) { throw "docker compose ล้มเหลว (exit code $code)" }
}

function Get-HostPaths {
    param([hashtable]$Settings)
    $raw = Get-Setting $Settings "PALWORLD_HOST_DIR" ".\host-palworld"
    $dir = Resolve-ConfiguredPath -BasePath $ProjectRoot -ConfiguredPath $raw
    return @{
        Dir = $dir
        Exe = Join-Path $dir "PalServer.exe"
        Config = Join-Path $dir "Pal\Saved\Config\WindowsServer\PalWorldSettings.ini"
        PalLog = Join-Path $dir "Pal\Saved\Logs\Pal.log"
    }
}

function Ensure-NativeSteamCmd {
    param([hashtable]$Settings)
    if (Test-Path -LiteralPath $SteamCmdExe) { return }

    $downloadUrl = Get-Setting $Settings "PALWORLD_STEAMCMD_DOWNLOAD_URL" "https://client-update.steamstatic.com/installer/steamcmd.zip"
    Write-Host "Downloading native Windows SteamCMD..."
    Write-Host "Source: $downloadUrl"
    New-Item -ItemType Directory -Force -Path $SteamCmdDir | Out-Null

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -OutFile $SteamCmdZip
        Expand-Archive -LiteralPath $SteamCmdZip -DestinationPath $SteamCmdDir -Force
    } catch {
        throw "ดาวน์โหลดหรือแตกไฟล์ SteamCMD for Windows ไม่สำเร็จ: $($_.Exception.Message)"
    } finally {
        Remove-Item -LiteralPath $SteamCmdZip -Force -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path -LiteralPath $SteamCmdExe)) {
        throw "แตกไฟล์ SteamCMD แล้วแต่ไม่พบ $SteamCmdExe"
    }
}

function Install-Or-Update {
    param([hashtable]$Settings)
    Ensure-NativeSteamCmd -Settings $Settings
    $paths = Get-HostPaths $Settings
    Assert-SafeHostPath -HostDir $paths.Dir
    Assert-HostWritable -HostDir $paths.Dir

    $validate = Convert-ToBool (Get-Setting $Settings "PALWORLD_STEAMCMD_VALIDATE" "true")
    $retries = [Math]::Max(1, [int](Get-Setting $Settings "PALWORLD_STEAMCMD_RETRIES" "2"))
    $steamArgs = @(
        "+force_install_dir", $paths.Dir,
        "+login", "anonymous",
        "+app_update", "2394010"
    )
    if ($validate) { $steamArgs += "validate" }
    $steamArgs += "+quit"

    Write-Host "Installing/updating Windows Dedicated Server with native steamcmd.exe..."
    Write-Host "Install directory: $($paths.Dir)"

    for ($attempt = 1; $attempt -le $retries; $attempt++) {
        Write-Host "SteamCMD attempt $attempt/$retries"
        & $SteamCmdExe @steamArgs
        $code = $LASTEXITCODE
        if ($code -eq 0 -and (Test-Path -LiteralPath $paths.Exe)) {
            Write-Host "Windows Dedicated Server is ready: $($paths.Exe)"
            return
        }
        if ($attempt -lt $retries) {
            Write-Warning "SteamCMD ไม่สำเร็จ (exit code $code) กำลังลองใหม่ใน 5 วินาที"
            Start-Sleep -Seconds 5
        }
    }

    if (-not (Test-Path -LiteralPath $paths.Exe)) {
        throw "Native SteamCMD จบแล้วแต่ไม่พบ $($paths.Exe). ห้ามใช้ Linux SteamCMD container เพื่อดาวน์โหลด Windows depot; ตรวจ Internet/Antivirus และลอง 06-Update.bat อีกครั้ง"
    }
    throw "Native SteamCMD ล้มเหลว (exit code $code)"
}

function Configure-Host {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ConfigScript -EnvFile $EnvFile
    if ($LASTEXITCODE -ne 0) { throw "ตั้งค่า Windows PalWorldSettings.ini ไม่สำเร็จ" }
}

function Get-AgentProcess {
    if (-not (Test-Path -LiteralPath $AgentPidFile)) { return $null }
    $pidText = (Get-Content -LiteralPath $AgentPidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($pidText -notmatch '^\d+$') { return $null }
    $process = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    if ($process.ProcessName -notmatch '^(powershell|pwsh)$') { return $null }
    return $process
}

function Test-AgentHeartbeat {
    $statusFile = Join-Path $ControlDir "status.json"
    if (-not (Test-Path -LiteralPath $statusFile)) { return $false }
    try {
        $status = Get-Content -LiteralPath $statusFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $status.heartbeat_at) { return $false }
        $heartbeat = [datetimeoffset]::Parse([string]$status.heartbeat_at)
        return (([datetimeoffset]::Now - $heartbeat).TotalSeconds -lt 10)
    } catch {
        return $false
    }
}

function Start-Agent {
    $existing = Get-AgentProcess
    if ($existing -and (Test-AgentHeartbeat)) { return $existing }
    if ($existing) {
        Stop-Process -Id $existing.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
    Remove-Item -LiteralPath $AgentPidFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $ControlDir "status.json") -Force -ErrorAction SilentlyContinue
    Get-ChildItem -LiteralPath $ControlDir -Filter "request-*.json" -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -LiteralPath $ControlDir -Filter "response-*.json" -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"' + $AgentScript + '"'),
        "-EnvFile", ('"' + $EnvFile + '"'),
        "-NoStart"
    )
    $process = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $AgentOutLog -RedirectStandardError $AgentErrLog -PassThru
    Set-Content -LiteralPath $AgentPidFile -Value $process.Id -Encoding ASCII
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        if ($process.HasExited) {
            $detail = if (Test-Path $AgentErrLog) { (Get-Content -LiteralPath $AgentErrLog -Tail 20 -ErrorAction SilentlyContinue) -join "`n" } else { "" }
            throw "Host Agent หยุดทันที`n$detail"
        }
        $statusFile = Join-Path $ControlDir "status.json"
        if (Test-Path -LiteralPath $statusFile) { return $process }
        Start-Sleep -Milliseconds 500
    }
    throw "Host Agent ไม่สร้าง status.json ภายใน 15 วินาที ดู $AgentErrLog"
}

function Request-ServerAction {
    param([ValidateSet("start", "stop")][string]$RequestAction, [hashtable]$Settings)
    Start-Agent | Out-Null
    $timeout = [int](Get-Setting $Settings "PALWORLD_EXTERNAL_CONTROL_TIMEOUT" "90")
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $RequestScript -Action $RequestAction -TimeoutSeconds $timeout
    if ($LASTEXITCODE -ne 0) { throw "Host Agent ทำคำสั่ง $RequestAction ไม่สำเร็จ" }
}

function Stop-Agent {
    $process = Get-AgentProcess
    if ($process) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
    Remove-Item -LiteralPath $AgentPidFile -Force -ErrorAction SilentlyContinue
}

function Get-BasicAuthHeader {
    param([string]$Password)
    $token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:$Password"))
    return @{ Authorization = "Basic $token" }
}

function Test-Rest {
    param([hashtable]$Settings, [int]$TimeoutSeconds = 3)
    $port = Get-Setting $Settings "PALWORLD_HOST_REST_PORT" "8212"
    $password = Get-Setting $Settings "PALWORLD_ADMIN_PASSWORD" ""
    try {
        Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:$port/v1/api/info" -Headers (Get-BasicAuthHeader $password) -TimeoutSec $TimeoutSeconds | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Wait-Rest {
    param([hashtable]$Settings)
    $timeout = [int](Get-Setting $Settings "PALWORLD_HOST_START_TIMEOUT_SECONDS" "900")
    $deadline = (Get-Date).AddSeconds($timeout)
    Write-Host "Waiting for Palworld REST API..."
    while ((Get-Date) -lt $deadline) {
        if (Test-Rest -Settings $Settings -TimeoutSeconds 3) {
            Write-Host "REST API online"
            return
        }
        Start-Sleep -Seconds 5
    }
    $paths = Get-HostPaths $Settings
    $tail = if (Test-Path -LiteralPath $paths.PalLog) { (Get-Content -LiteralPath $paths.PalLog -Tail 30 -ErrorAction SilentlyContinue) -join "`n" } else { "Pal.log not found" }
    throw "REST API ยัง Offline หลังรอ $timeout วินาที`nตรวจ AdminPassword/RESTAPIEnabled/Firewall`n--- Pal.log ---`n$tail"
}

function Start-Dashboard {
    Assert-Docker
    Invoke-Compose -Arguments @("--profile", "host-admin", "up", "-d", "--build", "dashboard-host") | Out-Null
}

function Wait-Dashboard {
    param([hashtable]$Settings)
    $port = Get-Setting $Settings "DASHBOARD_PORT" "8080"
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        try {
            $result = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/health" -TimeoutSec 3
            if ($result.StatusCode -eq 200) { return }
        } catch {}
        Start-Sleep -Seconds 2
    }
    throw "Dashboard healthcheck ไม่พร้อมที่ http://127.0.0.1:$port/health"
}

function Test-DashboardToHostRest {
    param([hashtable]$Settings)
    $hostName = Get-Setting $Settings "PALWORLD_HOST_API_HOST" "host.docker.internal"
    $port = Get-Setting $Settings "PALWORLD_HOST_REST_PORT" "8212"
    $password = Get-Setting $Settings "PALWORLD_ADMIN_PASSWORD" ""
    $token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:$password"))
    $python = "import urllib.request; u='http://$hostName`:$port/v1/api/info'; r=urllib.request.Request(u,headers={'Authorization':'Basic $token'}); print(urllib.request.urlopen(r,timeout=5).status)"
    & docker compose --env-file $EnvPath -f $ComposeFile --profile host-admin exec -T dashboard-host python3 -c $python *> $null
    return $LASTEXITCODE -eq 0
}

function Show-Status {
    param([hashtable]$Settings)
    $paths = Get-HostPaths $Settings
    $agent = Get-AgentProcess
    $server = Get-Process -Name "PalServer*" -ErrorAction SilentlyContinue | Select-Object -First 1
    $rest = Test-Rest -Settings $Settings
    Write-Host "Project: $ProjectRoot"
    Write-Host "Host dir: $($paths.Dir)"
    Write-Host "Agent: $(if ($agent) { 'running PID ' + $agent.Id } else { 'stopped' })"
    Write-Host "Server: $(if ($server) { 'running PID ' + $server.Id } else { 'stopped' })"
    Write-Host "REST API: $(if ($rest) { 'online' } else { 'offline' })"
    Assert-Docker
    Invoke-Compose -Arguments @("--profile", "host-admin", "ps") -AllowFailure
}

function Show-Logs {
    param([hashtable]$Settings)
    $paths = Get-HostPaths $Settings
    Write-Host "=== Host Agent stderr ==="
    if (Test-Path -LiteralPath $AgentErrLog) { Get-Content -LiteralPath $AgentErrLog -Tail 80 }
    Write-Host "=== Host Agent stdout ==="
    if (Test-Path -LiteralPath $AgentOutLog) { Get-Content -LiteralPath $AgentOutLog -Tail 80 }
    Write-Host "=== Palworld Pal.log ==="
    if (Test-Path -LiteralPath $paths.PalLog) {
        if ($Follow) { Get-Content -LiteralPath $paths.PalLog -Tail 100 -Wait }
        else { Get-Content -LiteralPath $paths.PalLog -Tail 100 }
    } else {
        Write-Host "Pal.log not found: $($paths.PalLog)"
    }
}

function Relocate-HostToShortPath {
    param([hashtable]$Settings)
    $paths = Get-HostPaths $Settings
    $source = $paths.Dir
    $configuredDestination = Get-Setting $Settings "PALWORLD_HOST_SHORT_DIR" ""
    $destination = if ($configuredDestination) {
        Resolve-ConfiguredPath -BasePath $ProjectRoot -ConfiguredPath $configuredDestination
    } else {
        Get-DefaultShortHostDir
    }

    if ([string]::Equals($source.TrimEnd('\'), $destination.TrimEnd('\'), [System.StringComparison]::OrdinalIgnoreCase)) {
        Write-Host "PALWORLD_HOST_DIR ใช้ path สั้นอยู่แล้ว: $source"
        Assert-SafeHostPath -HostDir $source
        return
    }
    if (-not (Test-Path -LiteralPath $source)) { throw "ไม่พบ Source server directory: $source" }
    if (Get-Process -Name "PalServer*" -ErrorAction SilentlyContinue) {
        Write-Host "Stopping Palworld before copy..."
        try { Request-ServerAction -RequestAction "stop" -Settings $Settings } catch { Write-Warning $_.Exception.Message }
    }
    if ((Get-Command docker -ErrorAction SilentlyContinue)) {
        Invoke-Compose -Arguments @("--profile", "host-admin", "down") -AllowFailure | Out-Null
    }
    Stop-Agent

    if (Test-Path -LiteralPath $destination) {
        $existing = Get-ChildItem -LiteralPath $destination -Force -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($existing) { throw "Destination มีข้อมูลอยู่แล้ว: $destination`nเปลี่ยน PALWORLD_HOST_SHORT_DIR ใน .env.host หรือย้ายข้อมูลปลายทางออกก่อน" }
    }
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Assert-SafeHostPath -HostDir $destination
    Assert-HostWritable -HostDir $destination

    Write-Host "Copying Windows server and world data..."
    Write-Host "Source:      $source"
    Write-Host "Destination: $destination"
    & robocopy.exe $source $destination /E /COPY:DAT /DCOPY:DAT /R:2 /W:2 /XJ /NFL /NDL /NP
    $copyCode = $LASTEXITCODE
    if ($copyCode -ge 8) { throw "Robocopy ล้มเหลว (exit code $copyCode). Source เดิมยังไม่ถูกลบ" }
    if (-not (Test-Path -LiteralPath (Join-Path $destination "PalServer.exe"))) {
        throw "คัดลอกเสร็จแต่ไม่พบ PalServer.exe ที่ปลายทาง Source เดิมยังไม่ถูกลบ"
    }

    Set-DotEnvValue -Path $EnvPath -Name "PALWORLD_HOST_DIR" -Value (Convert-ToEnvPath $destination)
    $updated = Read-DotEnv $EnvPath
    Assert-HostWritable -HostDir $destination
    Configure-Host
    Write-Host ""
    Write-Host "Relocation complete. Source เดิมยังอยู่สำหรับ rollback:"
    Write-Host $source
    Write-Host "New PALWORLD_HOST_DIR: $(Convert-ToEnvPath $destination)"
    Write-Host "Run 01-Start-All.bat แล้วทดสอบ Save ก่อนลบ Source เดิม"
}

function Run-Doctor {
    param([hashtable]$Settings)
    Assert-RequiredSettings $Settings
    $paths = Get-HostPaths $Settings
    Write-Host "[1/9] Safe Windows path"
    Assert-SafeHostPath -HostDir $paths.Dir
    Write-Host "OK - projected backup path: $(Get-ProjectedSavePathLength -HostDir $paths.Dir) characters"
    Write-Host "[2/9] Write permission"
    Assert-HostWritable -HostDir $paths.Dir
    Write-Host "OK"
    Write-Host "[3/9] Native Windows SteamCMD"
    Ensure-NativeSteamCmd -Settings $Settings
    Write-Host "OK - $SteamCmdExe"
    Write-Host "[4/9] Docker Desktop (Dashboard only)"
    Assert-Docker
    Write-Host "OK"
    Write-Host "[5/9] Server files"
    if (-not (Test-Path -LiteralPath $paths.Exe)) { throw "ไม่พบ $($paths.Exe) กรุณารัน 00-Setup.bat หรือ 06-Update.bat" }
    Write-Host "OK"
    Write-Host "[6/9] Config"
    Configure-Host
    Write-Host "OK"
    Write-Host "[7/9] Host Agent"
    Start-Agent | Out-Null
    Write-Host "OK"
    Write-Host "[8/9] Host REST API"
    if (-not (Test-Rest -Settings $Settings)) {
        Write-Host "Server/REST ยังไม่พร้อม กำลัง Start เพื่อทดสอบ"
        Request-ServerAction -RequestAction "start" -Settings $Settings
        Wait-Rest -Settings $Settings
    }
    Write-Host "Online"
    Write-Host "[9/9] Dashboard to Windows REST"
    Start-Dashboard
    Wait-Dashboard -Settings $Settings
    if (Test-DashboardToHostRest -Settings $Settings) {
        Write-Host "OK - Dashboard container เรียก REST API บน Windows ได้"
    } else {
        Write-Warning "Dashboard container เรียก REST ไม่ได้ แต่ Host อาจเรียกได้ ตรวจ Windows Firewall, VPN/EDR และ PALWORLD_HOST_API_HOST"
    }
}

try {
    $settings = Get-Settings
    switch ($Action) {
        "setup" {
            Assert-RequiredSettings $settings
            Install-Or-Update -Settings $settings
            Configure-Host
            Write-Host "Setup complete. Native Windows server files and config are ready."
            Write-Host "Run 01-Start-All.bat to start PalServer.exe and the Dashboard."
        }
        "configure" {
            Assert-RequiredSettings $settings
            $paths = Get-HostPaths $settings
            Assert-SafeHostPath -HostDir $paths.Dir
            Assert-HostWritable -HostDir $paths.Dir
            Configure-Host
        }
        "relocate-host" {
            Assert-RequiredSettings $settings
            Relocate-HostToShortPath -Settings $settings
        }
        "start-server" {
            Assert-RequiredSettings $settings
            $paths = Get-HostPaths $settings
            Assert-SafeHostPath -HostDir $paths.Dir
            Assert-HostWritable -HostDir $paths.Dir
            if (-not (Test-Path -LiteralPath $paths.Exe)) { Install-Or-Update -Settings $settings }
            Configure-Host
            Request-ServerAction -RequestAction "start" -Settings $settings
            Wait-Rest -Settings $settings
        }
        "start-dashboard" {
            Assert-RequiredSettings $settings
            Start-Dashboard
            Wait-Dashboard -Settings $settings
            Write-Host "Dashboard: http://127.0.0.1:$((Get-Setting $settings 'DASHBOARD_PORT' '8080'))"
        }
        "start-all" {
            Assert-RequiredSettings $settings
            Assert-Docker
            $paths = Get-HostPaths $settings
            Assert-SafeHostPath -HostDir $paths.Dir
            Assert-HostWritable -HostDir $paths.Dir
            if (-not (Test-Path -LiteralPath $paths.Exe)) { Install-Or-Update -Settings $settings }
            Configure-Host
            Request-ServerAction -RequestAction "start" -Settings $settings
            Wait-Rest -Settings $settings
            Start-Dashboard
            Wait-Dashboard -Settings $settings
            if (-not (Test-DashboardToHostRest -Settings $settings)) {
                throw "Host REST API Online แต่ Dashboard container เชื่อมต่อไม่ได้ ตรวจ Windows Firewall/VPN/Endpoint Security และ PALWORLD_HOST_API_HOST"
            }
            $url = "http://127.0.0.1:$((Get-Setting $settings 'DASHBOARD_PORT' '8080'))"
            Write-Host "Dashboard: $url"
            if (Convert-ToBool (Get-Setting $settings "PALWORLD_HOST_AUTO_OPEN_DASHBOARD" "true")) { Start-Process $url }
        }
        "stop-dashboard" {
            Assert-Docker
            Invoke-Compose -Arguments @("--profile", "host-admin", "stop", "dashboard-host") | Out-Null
        }
        "stop-server" {
            Request-ServerAction -RequestAction "stop" -Settings $settings
        }
        "restart-server" {
            Request-ServerAction -RequestAction "stop" -Settings $settings
            Configure-Host
            Request-ServerAction -RequestAction "start" -Settings $settings
            Wait-Rest -Settings $settings
        }
        "stop-all" {
            try { Request-ServerAction -RequestAction "stop" -Settings $settings } catch { Write-Warning $_.Exception.Message }
            Stop-Agent
            if ((Get-Command docker -ErrorAction SilentlyContinue)) {
                Invoke-Compose -Arguments @("--profile", "host-admin", "down") -AllowFailure | Out-Null
            }
        }
        "update" {
            Assert-RequiredSettings $settings
            try { Request-ServerAction -RequestAction "stop" -Settings $settings } catch { Write-Warning $_.Exception.Message }
            Install-Or-Update -Settings $settings
            Configure-Host
            Request-ServerAction -RequestAction "start" -Settings $settings
            Wait-Rest -Settings $settings
        }
        "status" { Show-Status -Settings $settings }
        "logs" { Show-Logs -Settings $settings }
        "doctor" { Run-Doctor -Settings $settings }
    }
    exit 0
} catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Host Agent log: $AgentErrLog"
    exit 1
}
