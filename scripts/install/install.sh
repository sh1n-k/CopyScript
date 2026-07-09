#!/usr/bin/env bash
set -euo pipefail

APP_NAME="CopyScript"
BUNDLE_ID="com.ytsubtitlecopy.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SYSTEM_NAME="$(uname -s)"

if [ "$SYSTEM_NAME" = "Darwin" ]; then
    SRC_APP="$PROJECT_ROOT/dist/$APP_NAME.app"
    DEST_APP="/Applications/$APP_NAME.app"
    EXEC_PATH="$DEST_APP/Contents/MacOS/$APP_NAME"
    PLIST_PATH="$HOME/Library/LaunchAgents/$BUNDLE_ID.plist"
else
    SRC_APP="$PROJECT_ROOT/dist/$APP_NAME"
    DEST_APP="$HOME/.local/lib/$APP_NAME"
    EXEC_PATH="$DEST_APP/$APP_NAME"
    DESKTOP_PATH="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$APP_NAME.desktop"
fi

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

install_macos() {
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
}

install_linux() {
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
}

if [ "$SYSTEM_NAME" = "Darwin" ]; then
    install_macos
elif [ "$SYSTEM_NAME" = "Linux" ]; then
    install_linux
else
    echo "오류: 이 설치 스크립트는 macOS/Linux만 지원합니다."
    exit 1
fi
