#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEM_NAME="$(uname -s)"

case "$SYSTEM_NAME" in
    Darwin)
        exec "$SCRIPT_DIR/install_macos.sh"
        ;;
    Linux)
        exec "$SCRIPT_DIR/install_linux.sh"
        ;;
    *)
        echo "오류: 이 설치 스크립트는 macOS/Linux만 지원합니다."
        exit 1
        ;;
esac
