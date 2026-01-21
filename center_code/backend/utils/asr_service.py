"""
ASR service selector.

- Default provider: baidu (existing implementation).
- Optional provider: iflytek_lfasr (iFlytek 录音文件转写), which can return timestamps.

Return format:
    text: str
    timestamps: list[dict] | None
        [{"text": str, "start": float, "end": float, "duration": float}, ...]
"""

from __future__ import annotations

import os
from typing import Optional, Tuple, List, Dict


def recognize_text_and_timestamps(
    audio_file_path: str,
    *,
    provider: Optional[str] = None,
    timeout_sec: int = 15 * 60,
) -> Tuple[str, Optional[List[Dict]]]:
    provider = (provider or os.environ.get("ASR_PROVIDER") or "baidu").strip().lower()

    if provider in ("iflytek", "iflytek_lfasr", "xfyun", "xunfei", "讯飞"):
        from utils.iflytek_lfasr import transcribe_with_timestamps

        return transcribe_with_timestamps(audio_file_path, timeout_sec=timeout_sec)

    # Default: baidu (text-only)
    from utils.baidu_asr import recognize_speech

    text = recognize_speech(audio_file_path)
    return text, None

