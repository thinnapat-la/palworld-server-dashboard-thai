param(
    [string]$EnvFile = ".env.host"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot

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

function Convert-ToIniString {
    param([string]$Value)
    $escaped = $Value.Replace("\", "\\").Replace('"', '\"')
    return '"' + $escaped + '"'
}

function Set-OptionSetting {
    param([string]$Content, [string]$Name, [string]$Value)
    $escapedName = [regex]::Escape($Name)
    $pattern = '(?<prefix>[\(,])\s*{0}\s*=\s*(?:"(?:\\.|[^"])*"|[^,\)]*)' -f $escapedName
    if ([regex]::IsMatch($Content, $pattern)) {
        return [regex]::Replace($Content, $pattern, { param($m) $m.Groups['prefix'].Value + $Name + "=" + $Value }, 1)
    }
    $marker = "OptionSettings=("
    $index = $Content.IndexOf($marker, [System.StringComparison]::Ordinal)
    if ($index -lt 0) { throw "ไม่พบ OptionSettings=(...) ใน PalWorldSettings.ini" }
    $insertAt = $index + $marker.Length
    return $Content.Insert($insertAt, "$Name=$Value,")
}

$envPath = Join-Path $ProjectRoot $EnvFile
if (-not (Test-Path -LiteralPath $envPath)) {
    throw "ไม่พบ $envPath กรุณารัน 00-Setup.bat ก่อน"
}
$settings = Read-DotEnv $envPath
$hostDirRaw = Get-Setting $settings "PALWORLD_HOST_DIR" ".\host-palworld"
$hostDir = Resolve-ConfiguredPath -BasePath $ProjectRoot -ConfiguredPath $hostDirRaw
$defaultConfig = Join-Path $hostDir "DefaultPalWorldSettings.ini"
$configDir = Join-Path $hostDir "Pal\Saved\Config\WindowsServer"
$configFile = Join-Path $configDir "PalWorldSettings.ini"

if (-not (Test-Path -LiteralPath $defaultConfig)) {
    throw "ไม่พบ $defaultConfig กรุณาติดตั้งหรืออัปเดตไฟล์เกมก่อน"
}

$adminPassword = Get-Setting $settings "PALWORLD_ADMIN_PASSWORD" ""
$dashboardPassword = Get-Setting $settings "DASHBOARD_PASSWORD" ""
if (-not $adminPassword -or $adminPassword -match "CHANGE_ME") {
    throw "กรุณาแก้ PALWORLD_ADMIN_PASSWORD ใน .env.host ก่อน"
}
if (-not $dashboardPassword -or $dashboardPassword -match "CHANGE_ME") {
    throw "กรุณาแก้ DASHBOARD_PASSWORD ใน .env.host ก่อน"
}

New-Item -ItemType Directory -Force -Path $configDir | Out-Null
if (-not (Test-Path -LiteralPath $configFile)) {
    Copy-Item -LiteralPath $defaultConfig -Destination $configFile -Force
    Write-Host "Created Windows config: $configFile"
}

$content = Get-Content -LiteralPath $configFile -Raw -Encoding UTF8
if ($content -notmatch "\[/Script/Pal.PalGameWorldSettings\]" -or $content -notmatch "OptionSettings\s*=\s*\(") {
    throw "PalWorldSettings.ini มีรูปแบบไม่ถูกต้อง"
}

$changes = [ordered]@{
    "ServerName" = Convert-ToIniString (Get-Setting $settings "PALWORLD_SERVER_NAME" "Mien Palworld Windows")
    "ServerPassword" = Convert-ToIniString (Get-Setting $settings "PALWORLD_SERVER_PASSWORD" "")
    "AdminPassword" = Convert-ToIniString $adminPassword
    "PublicPort" = Get-Setting $settings "PALWORLD_HOST_PORT" "8211"
    "RCONEnabled" = "True"
    "RCONPort" = Get-Setting $settings "PALWORLD_HOST_RCON_PORT" "25575"
    "RESTAPIEnabled" = "True"
    "RESTAPIPort" = Get-Setting $settings "PALWORLD_HOST_REST_PORT" "8212"
    "bIsMultiplay" = "True"
}

$updated = $content
foreach ($entry in $changes.GetEnumerator()) {
    $updated = Set-OptionSetting -Content $updated -Name $entry.Key -Value $entry.Value
}

if ($updated -ne $content) {
    $backupDir = Join-Path $ProjectRoot "runtime\config-backups"
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupFile = Join-Path $backupDir "PalWorldSettings-Windows-$stamp.ini"
    Copy-Item -LiteralPath $configFile -Destination $backupFile -Force
    [System.IO.File]::WriteAllText($configFile, $updated, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Updated REST/RCON/Admin settings. Backup: $backupFile"
} else {
    Write-Host "Windows config already matches .env.host"
}

Write-Host "Config: $configFile"
Write-Host "REST API: http://127.0.0.1:$($changes['RESTAPIPort'])/v1/api"
