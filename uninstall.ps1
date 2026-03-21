Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$appName = "CopyScript"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\\CopyScript"
$runKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$dataDir = Join-Path $env:LOCALAPPDATA "YTSubtitleCopy"

Write-Host "=== $appName 제거 ==="

$running = Get-Process -Name "CopyScript" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "실행 중인 앱을 종료합니다..."
    $running | Stop-Process -Force
    Start-Sleep -Seconds 1
}

if (Get-ItemProperty -Path $runKeyPath -Name $appName -ErrorAction SilentlyContinue) {
    Write-Host "자동실행 등록을 해제합니다..."
    Remove-ItemProperty -Path $runKeyPath -Name $appName
}

if (Test-Path $installDir) {
    Write-Host "설치 폴더를 삭제합니다..."
    Remove-Item -Recurse -Force $installDir
}

if (Test-Path $dataDir) {
    $answer = Read-Host "설정 데이터도 삭제하시겠습니까? ($dataDir) [y/N]"
    if ($answer -match "^[Yy]$") {
        Remove-Item -Recurse -Force $dataDir
        Write-Host "설정 데이터를 삭제했습니다."
    }
    else {
        Write-Host "설정 데이터를 유지합니다."
    }
}

Write-Host ""
Write-Host "=== 제거 완료 ==="
