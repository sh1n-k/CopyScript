#!/usr/bin/env bash
set -euo pipefail

APP_NAME="CopyScript"
BUNDLE_ID="com.ytsubtitlecopy.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_APP="$PROJECT_ROOT/dist/$APP_NAME.app"
DEST_APP="/Applications/$APP_NAME.app"
EXEC_PATH="$DEST_APP/Contents/MacOS/$APP_NAME"
PLIST_PATH="$HOME/Library/LaunchAgents/$BUNDLE_ID.plist"

bootstrap_agent() {
    local attempt

    for attempt in 1 2 3; do
        if launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"; then
            return 0
        fi

        if [ "$attempt" -lt 3 ]; then
            echo "LaunchAgent 등록 재시도 중... ($attempt/3)"
            sleep 1
        fi
    done

    echo "오류: LaunchAgent 등록에 실패했습니다."
    return 1
}

if [ ! -d "$SRC_APP" ]; then
    echo "오류: $SRC_APP 을 찾을 수 없습니다."
    echo "먼저 ./scripts/build/build.sh 를 실행하세요."
    exit 1
fi

if [ -d "$DEST_APP" ]; then
    echo "기존 앱을 제거합니다..."
    rm -rf "$DEST_APP"
fi

echo "앱을 /Applications 에 복사합니다..."
cp -R "$SRC_APP" "$DEST_APP"
xattr -cr "$DEST_APP" 2>/dev/null || true

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
        <string>$EXEC_PATH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$BUNDLE_ID" 2>/dev/null || true
bootstrap_agent

echo "앱을 실행합니다..."
launchctl kickstart -k "gui/$(id -u)/$BUNDLE_ID"

echo ""
echo "=== 설치 완료 ==="
echo "  앱 위치: $DEST_APP"
echo "  앱 실행: 즉시 메뉴바로 시작했습니다"
echo "  자동실행: 로그인 시 자동 시작됩니다"
echo "  설정 화면: 메뉴바 CC > 설정 열기"
echo ""
echo "  제거하려면: ./scripts/install/uninstall.sh"
