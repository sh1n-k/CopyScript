#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="CopyScript"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

if ! command -v uv >/dev/null 2>&1; then
    echo "오류: uv 명령을 찾을 수 없습니다."
    exit 1
fi

echo "=== uv 환경 동기화 ==="
uv sync --group dev --python "$PYTHON_BIN"

echo "=== 필수 모듈 확인 ==="
uv run python - <<'PY'
import importlib
import sys

required_modules = ("tkinter", "youtube_transcript_api")
missing = []
for module_name in required_modules:
    try:
        importlib.import_module(module_name)
    except Exception as error:
        missing.append(f"{module_name}: {error}")

if missing:
    print("다음 모듈을 불러오지 못했습니다:")
    for item in missing:
        print(f"  - {item}")
    sys.exit(1)

print("필수 모듈 import 확인 완료")
PY

SPEC_FILE="$APP_NAME.spec"

echo "=== 이전 빌드 정리 ==="
rm -rf build dist

echo "=== .app 번들 빌드 ==="
if [ -f "$SPEC_FILE" ]; then
  echo ".spec 파일 사용: $SPEC_FILE"
  uv run pyinstaller --noconfirm --clean "$SPEC_FILE"
else
  echo ".spec 파일 없음 — 기본 옵션으로 빌드"
  uv run pyinstaller \
    --windowed \
    --onedir \
    --name "$APP_NAME" \
    --noconfirm \
    --clean \
    --hidden-import=AppKit \
    --hidden-import=youtube_transcript_api \
    copyscript/main.py
fi

echo "=== ad-hoc 코드 서명 ==="
# 내부 바이너리를 안에서 바깥 순서로 서명
APP_PATH="dist/$APP_NAME.app"
find "$APP_PATH" -name "*.so" -exec codesign --force --sign - {} \; 2>/dev/null || true
find "$APP_PATH" -name "*.dylib" -exec codesign --force --sign - {} \; 2>/dev/null || true
find "$APP_PATH" -path "*/Python.framework/*" -name "Python" -type f -exec codesign --force --sign - {} \; 2>/dev/null || true
codesign --force --sign - "$APP_PATH" 2>/dev/null || true

# Gatekeeper 격리 속성 제거 (로컬 빌드용)
xattr -cr "$APP_PATH" 2>/dev/null || true

echo ""
echo "빌드 완료: dist/$APP_NAME.app"
echo "설치하려면: ./install.sh"
