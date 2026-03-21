Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$appName = "CopyScript"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDir = Join-Path $projectRoot "dist\\CopyScript"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\\CopyScript"
$exePath = Join-Path $installDir "CopyScript.exe"
$runKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$dataDir = Join-Path $env:LOCALAPPDATA "YTSubtitleCopy"

if (-not (Test-Path $sourceDir)) {
    throw "빌드 결과를 찾을 수 없습니다. 먼저 .\\build.ps1 를 실행하세요."
}

Write-Host "=== $appName 설치 ==="

$running = Get-Process -Name "CopyScript" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "실행 중인 앱을 종료합니다..."
    $running | Stop-Process -Force
    Start-Sleep -Seconds 1
}

if (Test-Path $installDir) {
    Write-Host "기존 설치를 제거합니다..."
    Remove-Item -Recurse -Force $installDir
}

Write-Host "앱을 설치 폴더에 복사합니다..."
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $sourceDir "*") $installDir

Write-Host "로그인 시 자동 실행을 등록합니다..."
New-Item -Path $runKeyPath -Force | Out-Null
Set-ItemProperty -Path $runKeyPath -Name $appName -Value "`"$exePath`" --hidden"

Write-Host ""
Write-Host "=== 설치 완료 ==="
Write-Host "  앱 위치: $exePath"
Write-Host "  자동실행: 로그인 시 트레이로 자동 시작됩니다"
Write-Host "  설정 데이터: $dataDir"
Write-Host ""
Write-Host "  제거하려면: .\\uninstall.ps1"
