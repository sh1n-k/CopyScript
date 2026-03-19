from __future__ import annotations

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


def build_language_maps() -> tuple[list[str], dict[str, str], dict[str, str]]:
    labels = [f"{name} ({code})" for name, code in SUPPORTED_LANGUAGES]
    label_to_code = {label: code for label, (_, code) in zip(labels, SUPPORTED_LANGUAGES)}
    code_to_label = {code: label for label, (_, code) in zip(labels, SUPPORTED_LANGUAGES)}
    return labels, label_to_code, code_to_label
