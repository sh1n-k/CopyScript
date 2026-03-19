from __future__ import annotations

import importlib
from typing import Any

from copyscript.config.languages import SUPPORTED_LANGUAGES
from copyscript.config.models import ProcessingOptions

try:
    transcript_module = importlib.import_module("youtube_transcript_api")
    YouTubeTranscriptApi = transcript_module.YouTubeTranscriptApi
except Exception:
    YouTubeTranscriptApi = None  # type: ignore[assignment]


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class SubtitleFetcher:
    def __init__(self, preferred_lang: str = "ko", include_timestamp: bool = False, api: Any = None):
        self.preferred_lang = preferred_lang
        self.include_timestamp = include_timestamp
        if api is not None:
            self.api = api
        elif YouTubeTranscriptApi is not None:
            self.api = YouTubeTranscriptApi()
        else:
            self.api = None

    def set_language(self, lang_code: str) -> None:
        self.preferred_lang = lang_code

    def set_timestamp(self, include: bool) -> None:
        self.include_timestamp = include

    def set_options(self, options: ProcessingOptions) -> None:
        self.preferred_lang = options.lang_code
        self.include_timestamp = options.include_timestamp

    def get_options(self) -> ProcessingOptions:
        return ProcessingOptions(self.preferred_lang, self.include_timestamp)

    def fetch(self, video_id: str, options: ProcessingOptions | None = None) -> tuple[str, str | None]:
        if self.api is None:
            return "", "자막 API를 사용할 수 없습니다"
        effective = options or self.get_options()
        try:
            transcript_list = self.api.list(video_id)
            transcript = None
            if effective.lang_code == "video-default":
                transcript = self._get_video_default_transcript(transcript_list)
            elif effective.lang_code == "auto":
                transcript = self._get_any_transcript(transcript_list)
            else:
                try:
                    transcript = transcript_list.find_transcript([effective.lang_code])
                except Exception:
                    transcript = None
                if transcript is None:
                    transcript = self._try_translate(transcript_list, effective.lang_code)
                if transcript is None:
                    transcript = self._get_any_transcript(transcript_list)
            if transcript is None:
                return "", "자막을 찾을 수 없습니다"
            transcript_data = transcript.fetch()
            lines: list[str] = []
            if hasattr(transcript_data, "snippets"):
                for snippet in transcript_data.snippets:
                    if effective.include_timestamp:
                        lines.append(f"[{format_timestamp(snippet.start)}] {snippet.text}")
                    else:
                        lines.append(snippet.text)
            else:
                for entry in transcript_data:
                    if effective.include_timestamp:
                        lines.append(f"[{format_timestamp(entry['start'])}] {entry['text']}")
                    else:
                        lines.append(entry["text"])
            return "\n".join(lines), None
        except Exception as error:
            error_text = str(error).lower()
            if "disabled" in error_text:
                return "", "자막이 비활성화된 영상입니다"
            if "unavailable" in error_text:
                return "", "영상을 찾을 수 없습니다"
            if "no transcript" in error_text:
                return "", "사용 가능한 자막이 없습니다"
            return "", f"오류: {str(error)}"

    def _get_any_transcript(self, transcript_list):
        if transcript_list._manually_created_transcripts:
            return next(iter(transcript_list._manually_created_transcripts.values()))
        if transcript_list._generated_transcripts:
            return next(iter(transcript_list._generated_transcripts.values()))
        return None

    def _get_video_default_transcript(self, transcript_list):
        if transcript_list._generated_transcripts:
            return next(iter(transcript_list._generated_transcripts.values()))
        if transcript_list._manually_created_transcripts:
            return next(iter(transcript_list._manually_created_transcripts.values()))
        return None

    def _try_translate(self, transcript_list, target_lang: str):
        for transcript in transcript_list:
            if transcript.is_translatable:
                try:
                    return transcript.translate(target_lang)
                except Exception:
                    continue
        return None
