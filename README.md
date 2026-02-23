# CopyScript

[![Release](https://img.shields.io/github/v/release/sh1n-k/CopyScript?sort=semver)](https://github.com/sh1n-k/CopyScript/releases)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-0A84FF)

**클립보드에 복사한 YouTube URL을 감지해서, 해당 영상 자막을 다시 클립보드에 넣어주는 데스크톱 앱**입니다.

URL 복사 한 번으로 자막 텍스트를 바로 붙여넣을 수 있어, 요약/번역/메모 작업 시간을 줄이는 것이 목적입니다.

## 주요 기능
- **YouTube URL 자동 감지**: 클립보드 변경을 감시해 YouTube 링크를 찾습니다.
- **자막 자동 추출 후 복사**: 영상 ID를 파싱한 뒤 자막을 가져와 클립보드에 복사합니다.
- **언어 선택 지원**: 한국어/영어/일본어/중국어 등과 `영상 기본 언어`, `Auto (any)`를 지원합니다.
- **타임스탬프 옵션**: `[00:00]` 형식으로 시간 정보를 포함할 수 있습니다.
- **중복 처리 방지**: 이미 처리한 영상은 LRU 캐시로 재처리를 줄입니다.
- **최근 처리 내역 표시**: GUI에서 최근 성공/실패 결과를 확인할 수 있습니다.

## 빠른 실행
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 사용 방법
1. 앱을 실행하면 메뉴바에 `CC` 아이콘이 나타납니다.
2. 설정 화면이 필요하면 메뉴바 `CC > 설정 열기`를 누릅니다.
3. 모니터링을 시작합니다.
4. YouTube 영상 URL을 복사합니다.
5. 잠시 후 자막이 클립보드로 교체됩니다.
6. 원하는 곳에 붙여넣기 합니다.

예시: 메모장에 링크를 복사했다가, 바로 `Cmd+V` 하면 자막 본문이 붙습니다.

## 빌드 (선택)
```bash
./build.sh
```

## 요구 사항
- Python 3.10+
- macOS 또는 Windows
- 인터넷 연결 (자막 조회 시 필요)
