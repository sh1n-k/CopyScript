#!/usr/bin/env bash
set -euo pipefail

APP_NAME="CopyScript"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_APP="$PROJECT_ROOT/dist/$APP_NAME"
DEST_APP="$HOME/.local/lib/$APP_NAME"
EXEC_PATH="$DEST_APP/$APP_NAME"
DESKTOP_PATH="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$APP_NAME.desktop"

if [ ! -x "$SRC_APP/$APP_NAME" ]; then
    echo "오류: $SRC_APP/$APP_NAME 을 찾을 수 없습니다."
    echo "먼저 ./scripts/build/build.sh 를 실행하세요."
    exit 1
fi

running_pids="$(ps -eo pid=,args= | awk -v exe="$DEST_APP/$APP_NAME" '$2 == exe {print $1}')"
if [ -n "$running_pids" ]; then
    echo "실행 중인 앱을 종료합니다..."
    while IFS= read -r pid; do
        kill "$pid" 2>/dev/null || true
    done << EOF
$running_pids
EOF
    sleep 1
fi

if [ -d "$DEST_APP" ]; then
    echo "기존 앱을 제거합니다..."
    rm -rf "$DEST_APP"
fi

echo "앱을 $DEST_APP 에 복사합니다..."
mkdir -p "$(dirname "$DEST_APP")"
cp -R "$SRC_APP" "$DEST_APP"

echo "로그인 시 자동실행을 등록합니다..."
mkdir -p "$(dirname "$DESKTOP_PATH")"
cat > "$DESKTOP_PATH" << EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec="$EXEC_PATH" --hidden
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

chmod +x "$EXEC_PATH"

echo "앱을 실행합니다..."
if command -v setsid >/dev/null 2>&1; then
    setsid "$EXEC_PATH" --hidden >/dev/null 2>&1 < /dev/null &
else
    nohup "$EXEC_PATH" --hidden >/dev/null 2>&1 &
fi

echo ""
echo "=== 설치 완료 ==="
echo "  앱 위치: $EXEC_PATH"
echo "  앱 실행: 즉시 시작했습니다"
echo "  자동실행: 로그인 시 자동 시작됩니다"
echo "  자동실행 파일: $DESKTOP_PATH"
echo ""
echo "  제거하려면: ./scripts/install/uninstall.sh"
