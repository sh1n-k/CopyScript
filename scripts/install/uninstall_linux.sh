#!/usr/bin/env bash
set -euo pipefail

APP_NAME="CopyScript"
DEST_APP="$HOME/.local/lib/$APP_NAME"
RUNNING_EXEC_PATH="$DEST_APP/$APP_NAME"
AUTOSTART_PATH="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$APP_NAME.desktop"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/CopyScript"

echo "=== $APP_NAME 제거 ==="

running_pids="$(ps -eo pid=,args= | awk -v exe="$RUNNING_EXEC_PATH" '$2 == exe {print $1}')"
if [ -n "$running_pids" ]; then
    echo "실행 중인 앱을 종료합니다..."
    while IFS= read -r pid; do
        kill "$pid" 2>/dev/null || true
    done << EOF
$running_pids
EOF
    sleep 1
fi

if [ -f "$AUTOSTART_PATH" ]; then
    echo "자동실행 등록을 해제합니다..."
    rm -f "$AUTOSTART_PATH"
    echo "  자동실행 등록 제거 완료"
fi

if [ -d "$DEST_APP" ]; then
    echo "앱을 삭제합니다..."
    rm -rf "$DEST_APP"
    echo "  $DEST_APP 삭제 완료"
fi

if [ -d "$DATA_DIR" ]; then
    echo ""
    printf "설정 데이터도 삭제하시겠습니까? (%s) [y/N]: " "$DATA_DIR"
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        rm -rf "$DATA_DIR"
        echo "  설정 데이터 삭제 완료"
    else
        echo "  설정 데이터를 유지합니다"
    fi
fi

echo ""
echo "=== 제거 완료 ==="
