#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

APP_NAME="CopyScript"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
SYSTEM_NAME="$(uname -s)"

if ! command -v uv >/dev/null 2>&1; then
    echo "오류: uv 명령을 찾을 수 없습니다."
    exit 1
fi

echo "=== uv 환경 동기화 ==="
uv sync --group dev --python "$PYTHON_BIN"

echo "=== 필수 모듈 확인 ==="
uv run --python "$PYTHON_BIN" python - <<'PY'
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

if [ "$SYSTEM_NAME" = "Linux" ]; then
    if ! command -v xclip >/dev/null 2>&1 && ! command -v xsel >/dev/null 2>&1 && ! command -v wl-copy >/dev/null 2>&1; then
        echo "오류: Linux 클립보드 도구를 찾을 수 없습니다. xclip, xsel, wl-clipboard 중 하나를 설치하세요."
        exit 1
    fi
fi

SPEC_FILE="packaging/pyinstaller/$APP_NAME.spec"

echo "=== 이전 빌드 정리 ==="
rm -rf build dist

if [ "$SYSTEM_NAME" = "Darwin" ]; then
    echo "=== .app 번들 빌드 ==="
else
    echo "=== 실행 파일 빌드 ==="
fi
if [ -f "$SPEC_FILE" ]; then
  echo ".spec 파일 사용: $SPEC_FILE"
  uv run --python "$PYTHON_BIN" python -m PyInstaller --noconfirm --clean "$SPEC_FILE"
else
  echo ".spec 파일 없음 — 기본 옵션으로 빌드"
  hidden_import_args=(--hidden-import=youtube_transcript_api)
  if [ "$SYSTEM_NAME" = "Darwin" ]; then
    hidden_import_args+=(--hidden-import=AppKit)
  fi
  uv run --python "$PYTHON_BIN" python -m PyInstaller \
    --windowed \
    --onedir \
    --name "$APP_NAME" \
    --noconfirm \
    --clean \
    "${hidden_import_args[@]}" \
    copyscript/main.py
fi

if [ "$SYSTEM_NAME" = "Darwin" ]; then
    echo "=== ad-hoc 코드 서명 ==="
    # 내부 바이너리를 안에서 바깥 순서로 서명
    APP_PATH="dist/$APP_NAME.app"
    find "$APP_PATH" -name "*.so" -exec codesign --force --sign - {} \; 2>/dev/null || true
    find "$APP_PATH" -name "*.dylib" -exec codesign --force --sign - {} \; 2>/dev/null || true
    find "$APP_PATH" -path "*/Python.framework/*" -name "Python" -type f -exec codesign --force --sign - {} \; 2>/dev/null || true
    codesign --force --sign - "$APP_PATH" 2>/dev/null || true

    # Gatekeeper 격리 속성 제거 (로컬 빌드용)
    xattr -cr "$APP_PATH" 2>/dev/null || true
fi

echo ""
if [ "$SYSTEM_NAME" = "Darwin" ]; then
    echo "빌드 완료: dist/$APP_NAME.app"
else
    echo "빌드 완료: dist/$APP_NAME/$APP_NAME"
fi
echo "설치하려면: ./scripts/install/install.sh"
