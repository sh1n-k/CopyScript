#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="YouTube 자막 복사"
ENTRY="main.py"
VENV="$SCRIPT_DIR/.venv"

# venv 활성화
if [ ! -d "$VENV" ]; then
    echo "오류: .venv 디렉토리를 찾을 수 없습니다."
    exit 1
fi
source "$VENV/bin/activate"

echo "=== PyInstaller 설치 확인 ==="
pip install --quiet pyinstaller

SPEC_FILE="$APP_NAME.spec"

echo "=== 이전 빌드 정리 ==="
rm -rf build dist

echo "=== .app 번들 빌드 ==="
if [ -f "$SPEC_FILE" ]; then
  echo ".spec 파일 사용: $SPEC_FILE"
  pyinstaller --noconfirm --clean "$SPEC_FILE"
else
  echo ".spec 파일 없음 — 기본 옵션으로 빌드"
  pyinstaller \
    --windowed \
    --onedir \
    --name "$APP_NAME" \
    --noconfirm \
    --clean \
    --hidden-import=AppKit \
    "$ENTRY"
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
