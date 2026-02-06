"""YouTube 자막 추출 모듈"""

from youtube_transcript_api import YouTubeTranscriptApi

# 지원 언어 목록 (표시명, 코드)
SUPPORTED_LANGUAGES = [
    ("영상 기본 언어", "video-default"),
    ("한국어", "ko"),
    ("English", "en"),
    ("日本語", "ja"),
    ("中文", "zh-Hans"),
    ("Español", "es"),
    ("Français", "fr"),
    ("Deutsch", "de"),
    ("Auto (any)", "auto"),
]


def format_timestamp(seconds: float) -> str:
    """초를 MM:SS 또는 HH:MM:SS 형식으로 변환"""
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class SubtitleFetcher:
    """YouTube 자막 추출 클래스"""

    def __init__(self, preferred_lang: str = "ko", include_timestamp: bool = False):
        self.preferred_lang = preferred_lang
        self.include_timestamp = include_timestamp
        self.api = YouTubeTranscriptApi()

    def set_language(self, lang_code: str):
        """선호 언어 설정"""
        self.preferred_lang = lang_code

    def set_timestamp(self, include: bool):
        """타임스탬프 포함 여부 설정"""
        self.include_timestamp = include

    def fetch(self, video_id: str) -> tuple[str, str | None]:
        """
        자막을 가져옵니다.

        탐색 순서:
        1. 영상 기본 언어 자막 (자동 생성 포함)
        2. 선호 언어의 수동 자막
        3. 선호 언어의 자동생성 자막
        4. 다른 언어 자막을 선호 언어로 번역
        5. 아무 자막이나 (수동 우선)

        Args:
            video_id: YouTube video ID

        Returns:
            (자막 텍스트, 에러 메시지 또는 None)
        """
        try:
            transcript_list = self.api.list(video_id)

            transcript = None

            if self.preferred_lang == "video-default":
                transcript = self._get_video_default_transcript(transcript_list)
            elif self.preferred_lang == "auto":
                # 아무 자막이나 (수동 우선)
                transcript = self._get_any_transcript(transcript_list)
            else:
                # 1. 선호 언어 자막 (수동 + 자동생성 모두 검색)
                try:
                    transcript = transcript_list.find_transcript([self.preferred_lang])
                except Exception:
                    pass

                # 2. 다른 언어를 선호 언어로 번역
                if transcript is None:
                    transcript = self._try_translate(
                        transcript_list, self.preferred_lang
                    )

                # 3. 최후의 수단: 아무 자막이나
                if transcript is None:
                    transcript = self._get_any_transcript(transcript_list)

            if transcript is None:
                return "", "자막을 찾을 수 없습니다"

            # 자막 데이터 가져오기
            transcript_data = transcript.fetch()

            # 텍스트 추출 (타임스탬프 옵션에 따라)
            lines = []
            if hasattr(transcript_data, "snippets"):
                for snippet in transcript_data.snippets:
                    if self.include_timestamp:
                        ts = format_timestamp(snippet.start)
                        lines.append(f"[{ts}] {snippet.text}")
                    else:
                        lines.append(snippet.text)
            else:
                # 이전 버전 호환
                for entry in transcript_data:
                    if self.include_timestamp:
                        ts = format_timestamp(entry["start"])
                        lines.append(f"[{ts}] {entry['text']}")
                    else:
                        lines.append(entry["text"])

            full_text = "\n".join(lines)

            return full_text, None

        except Exception as e:
            error_str = str(e).lower()
            if "disabled" in error_str:
                return "", "자막이 비활성화된 영상입니다"
            elif "unavailable" in error_str:
                return "", "영상을 찾을 수 없습니다"
            elif "no transcript" in error_str:
                return "", "사용 가능한 자막이 없습니다"
            else:
                return "", f"오류: {str(e)}"

    def _get_any_transcript(self, transcript_list):
        """사용 가능한 아무 자막이나 반환 (수동 우선)"""
        # 수동 생성 자막 우선
        if transcript_list._manually_created_transcripts:
            return next(iter(transcript_list._manually_created_transcripts.values()))
        # 자동 생성 자막
        if transcript_list._generated_transcripts:
            return next(iter(transcript_list._generated_transcripts.values()))
        return None

    def _get_video_default_transcript(self, transcript_list):
        """영상 기본 언어 자막 반환 (자동 생성 포함)"""
        # 자동 생성 자막이 있으면 기본 언어로 간주
        if transcript_list._generated_transcripts:
            return next(iter(transcript_list._generated_transcripts.values()))
        # 자동 생성이 없으면 수동 자막 중 첫 번째 사용
        if transcript_list._manually_created_transcripts:
            return next(iter(transcript_list._manually_created_transcripts.values()))
        return None

    def _try_translate(self, transcript_list, target_lang: str):
        """번역 가능한 자막을 찾아 번역 시도"""
        # 자동 생성 자막은 보통 번역 가능
        for transcript in transcript_list:
            if transcript.is_translatable:
                try:
                    return transcript.translate(target_lang)
                except Exception:
                    continue
        return None


if __name__ == "__main__":
    # 테스트
    fetcher = SubtitleFetcher("ko")
    text, error = fetcher.fetch("dQw4w9WgXcQ")
    if error:
        print(f"Error: {error}")
    else:
        print(f"자막 길이: {len(text)} 글자")
        print(text[:500])
