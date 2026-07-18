param(
    [string]$SourceDir = ".\palworld",
    [switch]$Force
)
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot
$volumeName = if ($env:PALWORLD_VOLUME_NAME) { $env:PALWORLD_VOLUME_NAME } else { "palworld-data" }
$sourcePath = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $SourceDir))
if (-not (Test-Path $sourcePath)) { throw "ไม่พบโฟลเดอร์เดิม: $sourcePath" }
$backupDir = Join-Path $ProjectRoot "migration-backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $backupDir "palworld-bind-$stamp.zip"

docker compose --profile admin down
Compress-Archive -Path (Join-Path $sourcePath "*") -DestinationPath $backupFile -CompressionLevel Optimal -Force
docker volume create $volumeName | Out-Null
$count = docker run --rm -v "${volumeName}:/target" alpine:3.20 sh -c "find /target -mindepth 1 -maxdepth 1 | wc -l"
if ([int]$count -gt 0 -and -not $Force) {
    throw "Named volume $volumeName ไม่ว่าง ใช้ -Force เฉพาะเมื่อยืนยันว่าต้องการเขียนทับ"
}
if ([int]$count -gt 0) {
    docker run --rm -v "${volumeName}:/target" alpine:3.20 sh -c "rm -rf /target/* /target/.[!.]* /target/..?* 2>/dev/null || true"
}
docker run --rm -v "${sourcePath}:/source:ro" -v "${volumeName}:/target" alpine:3.20 sh -c "cp -a /source/. /target/"
Write-Host "Migration complete. Backup: $backupFile"
Write-Host "Start with: docker compose --profile admin up -d --build"
