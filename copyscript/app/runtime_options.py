from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeOptions:
    start_hidden: bool = False
