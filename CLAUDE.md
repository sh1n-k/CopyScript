# CopyScript

## 프로젝트 개요
클립보드에 복사한 YouTube URL을 자동 감지하여 해당 영상의 자막을 클립보드에 넣어주는 macOS/Windows 데스크톱 앱.

## 기술 스택
- **Python 3.10+** / tkinter GUI
- **youtube-transcript-api**: 자막 추출
- **pyperclip**: 클립보드 읽기/쓰기
- **pyobjc (macOS)**: NSPasteboard 감시, NSStatusItem 메뉴바
- **PyInstaller**: `.app` 번들 빌드

## 프로젝트 구조
```
main.py                 # 메인 GUI (App 클래스, tkinter)
clipboard_monitor.py    # URL 감지 → 자막 추출 → 클립보드 복사 로직
clipboard_watchers.py   # 플랫폼별 클립보드 변경 감지기 (macOS: changeCount 폴링, Windows: WM_CLIPBOARDUPDATE)
subtitle_fetcher.py     # YouTube 자막 추출 (SubtitleFetcher, 언어 탐색 순서 로직)
subtitle_cache.py       # 자막 텍스트 LRU 캐시 (디스크 기반, OrderedDict)
url_parser.py           # YouTube URL → video_id 파싱
notifier.py             # OS 알림 (macOS: osascript, Windows: win11toast)
menubar.py              # macOS 전용 NSStatusItem 메뉴바 컨트롤러
app_paths.py            # 앱 데이터 경로 (~Library/Application Support/YTSubtitleCopy/)
build.sh                # PyInstaller 빌드 + ad-hoc 코드서명
install.sh              # /Applications 복사 + LaunchAgent 자동실행 등록
uninstall.sh            # 앱·LaunchAgent·캐시 제거
tests/                  # pytest 테스트
```

## 핵심 흐름
1. `ClipboardWatcher` → 클립보드 변경 감지
2. `ClipboardMonitor.check_and_process()` → URL 파싱 → 캐시 확인 → 자막 추출 → 클립보드 복사
3. 콜백(`_on_status_change`, `_on_processed`)으로 GUI 상태 업데이트

## 개발 환경 설정
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 테스트
```bash
pytest tests/
```

## 빌드
```bash
./build.sh          # dist/CopyScript.app 생성
./install.sh        # /Applications에 설치 + 로그인 자동실행
./uninstall.sh      # 제거
```

## 코딩 컨벤션
- UI 텍스트와 주석은 한국어로 작성
- 변수명/함수명은 영어 snake_case, 클래스명은 PascalCase
- docstring은 한국어
- 설정은 `app_settings.json`에 JSON으로 저장 (경로: `~/Library/Application Support/YTSubtitleCopy/`)
- 캐시 파일은 `subtitle_cache/items/` 디렉토리에 SHA1 해시 파일명으로 저장
- 플랫폼 분기는 `platform.system()` 기반
- 스레드 안전: GUI 업데이트는 반드시 `root.after(0, ...)` 경유
- `_closing` 플래그로 종료 중 콜백 방어

## 주의사항
- `menubar.py`는 macOS 전용 (`pyobjc` 필요)
- Windows에서는 `clipboard_watchers.py`의 `WindowsClipboardWatcher`가 Win32 API 직접 호출
- `subtitle_fetcher.py`에서 `transcript_list._manually_created_transcripts` 등 내부 속성 접근 (youtube-transcript-api 버전 의존)
- `.gitignore`에 `.claude/`, `app_settings.json`, `build/`, `dist/` 포함
