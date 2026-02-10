#!/bin/zsh
set -euo pipefail

APP_NAME="YouTube 자막 복사"
BUNDLE_ID="com.ytsubtitlecopy.app"
DEST_APP="/Applications/$APP_NAME.app"
PLIST_PATH="$HOME/Library/LaunchAgents/$BUNDLE_ID.plist"
DATA_DIR="$HOME/Library/Application Support/YTSubtitleCopy"

echo "=== $APP_NAME 제거 ==="

# --- 실행 중인 앱 종료 ---
if pgrep -f "$APP_NAME" > /dev/null 2>&1; then
    echo "실행 중인 앱을 종료합니다..."
    pkill -f "$APP_NAME" 2>/dev/null || true
    sleep 1
fi

# --- LaunchAgent 해제 ---
if [ -f "$PLIST_PATH" ]; then
    echo "자동실행 등록을 해제합니다..."
    launchctl bootout "gui/$(id -u)/$BUNDLE_ID" 2>/dev/null || true
    rm -f "$PLIST_PATH"
    echo "  LaunchAgent 제거 완료"
fi

# --- 앱 삭제 ---
if [ -d "$DEST_APP" ]; then
    echo "앱을 삭제합니다..."
    rm -rf "$DEST_APP"
    echo "  $DEST_APP 삭제 완료"
fi

# --- 설정 데이터 ---
if [ -d "$DATA_DIR" ]; then
    echo ""
    read -rp "설정 데이터도 삭제하시겠습니까? ($DATA_DIR) [y/N]: " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        rm -rf "$DATA_DIR"
        echo "  설정 데이터 삭제 완료"
    else
        echo "  설정 데이터를 유지합니다"
    fi
fi

echo ""
echo "=== 제거 완료 ==="
