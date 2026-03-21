Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv 명령을 찾을 수 없습니다."
}

Write-Host "=== uv 환경 동기화 ==="
uv sync --group dev

Write-Host "=== 필수 모듈 확인 ==="
uv run python -c "import importlib, sys; modules=('tkinter','youtube_transcript_api','pystray','PIL'); missing=[]`nfor name in modules:`n    try:`n        importlib.import_module(name)`n    except Exception as exc:`n        missing.append(f'{name}: {exc}')`nif missing:`n    print('missing modules:')`n    [print(f'  - {item}') for item in missing]`n    sys.exit(1)`nprint('module-import-ok')"

Write-Host "=== 이전 빌드 정리 ==="
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "=== Windows 앱 빌드 ==="
uv run pyinstaller --noconfirm --clean CopyScript.spec

Write-Host ""
Write-Host "빌드 완료: dist\\CopyScript\\CopyScript.exe"
Write-Host "설치하려면: .\\install.ps1"
