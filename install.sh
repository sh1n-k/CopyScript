#!/bin/zsh
set -euo pipefail

APP_NAME="YouTube 자막 복사"
BUNDLE_ID="com.ytsubtitlecopy.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_APP="$SCRIPT_DIR/dist/$APP_NAME.app"
DEST_APP="/Applications/$APP_NAME.app"
PLIST_PATH="$HOME/Library/LaunchAgents/$BUNDLE_ID.plist"

# --- 빌드 확인 ---
if [ ! -d "$SRC_APP" ]; then
    echo "오류: $SRC_APP 을 찾을 수 없습니다."
    echo "먼저 ./build.sh 를 실행하세요."
    exit 1
fi

# --- 기존 설치 정리 ---
if [ -d "$DEST_APP" ]; then
    echo "기존 앱을 제거합니다..."
    rm -rf "$DEST_APP"
fi

# --- 앱 복사 ---
echo "앱을 /Applications 에 복사합니다..."
cp -R "$SRC_APP" "$DEST_APP"
xattr -cr "$DEST_APP" 2>/dev/null || true

# --- LaunchAgent 등록 ---
echo "로그인 시 자동실행을 등록합니다..."
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$BUNDLE_ID</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-a</string>
        <string>$DEST_APP</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

# 기존 등록 해제 (있으면)
launchctl bootout "gui/$(id -u)/$BUNDLE_ID" 2>/dev/null || true

# 등록
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"

echo ""
echo "=== 설치 완료 ==="
echo "  앱 위치: $DEST_APP"
echo "  자동실행: 로그인 시 자동 시작됩니다"
echo ""
echo "  제거하려면: ./uninstall.sh"
