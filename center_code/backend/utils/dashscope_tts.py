"""
DashScope CosyVoice TTS adapter.

This module provides a TTS implementation backed by DashScope `audio.tts_v2`.

Env/config:
- DASHSCOPE_API_KEY (required)
- COSYVOICE_MODEL (optional, default: cosyvoice-v3-flash)
- TTS_VOICES_JSON (optional JSON array), e.g.
  [
    {"id": 0, "key": "female", "name": "女声", "voice": "longanhuan"},
    {"id": 1, "key": "male", "name": "男声", "voice": "longanyang"}
  ]
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

try:
    from config import FFMPEG_PATH, DASHSCOPE_API_KEY, COSYVOICE_MODEL, TTS_VOICES_JSON
except Exception:
    FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "")
    DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
    COSYVOICE_MODEL = os.environ.get("COSYVOICE_MODEL", "cosyvoice-v3-flash")
    TTS_VOICES_JSON = os.environ.get("TTS_VOICES_JSON", "")


def _require_dashscope_key() -> str:
    api_key = (DASHSCOPE_API_KEY or os.environ.get("DASHSCOPE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("Missing DashScope API key: set DASHSCOPE_API_KEY")
    dashscope.api_key = api_key
    return api_key


def _read_tts_voices_file(path_value: str) -> str:
    p = (path_value or "").strip()
    if not p:
        return ""

    path = Path(p)
    if not path.is_absolute():
        backend_dir = Path(__file__).resolve().parent.parent
        path = backend_dir / path

    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _load_voice_catalog() -> List[Dict[str, Any]]:
    file_raw = _read_tts_voices_file(os.environ.get("TTS_VOICES_FILE") or "")
    if file_raw:
        try:
            data = json.loads(file_raw)
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
        except Exception:
            pass

    raw = (TTS_VOICES_JSON or os.environ.get("TTS_VOICES_JSON") or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except Exception:
        return []
    return []


def list_voices_for_frontend() -> List[Dict[str, Any]]:
    catalog = _load_voice_catalog()
    if not catalog:
        return [{"id": 0, "key": "default", "name": "默认音色（请配置 TTS_VOICES_JSON 或 TTS_VOICES_FILE）"}]

    out: List[Dict[str, Any]] = []
    for x in catalog:
        try:
            out.append(
                {
                    "id": int(x.get("id", 0)),
                    "key": (x.get("key") or str(x.get("id", 0))),
                    "name": (x.get("name") or (x.get("key") or f"voice-{x.get('id')}")),
                }
            )
        except Exception:
            continue
    return out


def resolve_voice(voice: Union[str, int]) -> str:
    catalog = _load_voice_catalog()

    if isinstance(voice, int) or (isinstance(voice, str) and voice.strip().isdigit()):
        vid = int(voice)
        for item in catalog:
            if int(item.get("id", -1)) == vid:
                resolved = (item.get("voice") or "").strip()
                if resolved:
                    return resolved
                raise RuntimeError(f"TTS voice id={vid} is configured but empty; check TTS_VOICES_JSON")
        raise RuntimeError(f"Unknown TTS voice id={vid}; configure TTS_VOICES_JSON")

    v = (voice or "").strip()
    if not v:
        raise RuntimeError("voice is required")
    for item in catalog:
        if (item.get("key") or "").strip() == v:
            resolved = (item.get("voice") or "").strip()
            if resolved:
                return resolved
            raise RuntimeError(f"TTS voice key={v} is configured but empty; check TTS_VOICES_JSON")

    return v


def _resolve_ffmpeg_exe() -> str:
    ff = (os.environ.get("FFMPEG_PATH") or FFMPEG_PATH or "").strip()
    if ff and os.path.exists(ff):
        return os.path.abspath(ff)
    which = shutil.which("ffmpeg")
    if which:
        return which
    raise RuntimeError("ffmpeg not found; install ffmpeg or set FFMPEG_PATH")


def _resolve_ffprobe_exe(ffmpeg_exe: str) -> str:
    which = shutil.which("ffprobe")
    if which:
        return which
    sibling = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe.exe")
    if os.path.exists(sibling):
        return sibling
    raise RuntimeError("ffprobe not found; install ffmpeg/ffprobe or ensure it is on PATH")


def _maybe_convert_wav_to_mp3(wav_bytes: bytes) -> bytes:
    ffmpeg = _resolve_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as td:
        in_path = os.path.join(td, "in.wav")
        out_path = os.path.join(td, "out.mp3")
        with open(in_path, "wb") as f:
            f.write(wav_bytes)
        cmd = [ffmpeg, "-y", "-i", in_path, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", out_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(out_path, "rb") as f:
            return f.read()


def _split_into_sentences(text: str) -> List[str]:
    try:
        from utils.subtitles import split_into_sentences  # type: ignore

        sents = split_into_sentences(text)
        if isinstance(sents, list) and sents:
            return [str(s).strip() for s in sents if str(s).strip()]
    except Exception:
        pass
    parts = re.split(r"[，。\.!！\?？；;\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def _probe_duration_seconds(audio_bytes: bytes, suffix: str) -> float:
    ffmpeg = _resolve_ffmpeg_exe()
    try:
        ffprobe = _resolve_ffprobe_exe(ffmpeg)
    except Exception:
        return max(1.0, len(audio_bytes) / 10000.0)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        cmd = [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            tmp_path,
        ]
        p = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float((p.stdout or "").strip() or "0") or 0.0
    except Exception:
        return max(1.0, len(audio_bytes) / 10000.0)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _dashscope_synthesize_wav_bytes(*, text: str, voice: str, speech_rate: float, volume: int) -> bytes:
    _require_dashscope_key()
    model = (COSYVOICE_MODEL or os.environ.get("COSYVOICE_MODEL") or "cosyvoice-v3-flash").strip()
    synthesizer = SpeechSynthesizer(model=model, voice=voice, speech_rate=speech_rate, volume=volume)
    audio_data = synthesizer.call(text)
    if not audio_data:
        raise RuntimeError("DashScope TTS returned empty audio")
    return audio_data


def synthesize_speech(
    *,
    text: str,
    voice: Union[str, int] = 0,
    speed: int = 5,
    pitch: int = 5,
    volume: int = 5,
    audio_format: str = "mp3",
) -> bytes:
    text = (text or "").strip()
    if not text:
        raise RuntimeError("text cannot be empty")
    if len(text) > 500:
        raise RuntimeError("text too long (建议 <= 500 字)")

    resolved_voice = resolve_voice(voice)

    try:
        s = int(speed)
    except Exception:
        s = 5
    s = max(0, min(s, 15))
    speech_rate = 0.6 + (s / 15.0) * 1.0

    try:
        v = int(volume)
    except Exception:
        v = 5
    v = max(0, min(v, 15))
    mapped_volume = int(20 + (v / 15.0) * 80)

    wav_bytes = _dashscope_synthesize_wav_bytes(text=text, voice=resolved_voice, speech_rate=speech_rate, volume=mapped_volume)

    fmt = (audio_format or "mp3").lower()
    if fmt == "wav":
        return wav_bytes
    if fmt == "mp3":
        return _maybe_convert_wav_to_mp3(wav_bytes)
    raise RuntimeError(f"Unsupported audio_format={audio_format}; use mp3 or wav")


def synthesize_speech_with_timestamps(
    *,
    text: str,
    voice: Union[str, int] = 0,
    speed: int = 5,
    pitch: int = 5,
    volume: int = 5,
    audio_format: str = "mp3",
) -> Tuple[bytes, List[Dict[str, Any]]]:
    sentences = _split_into_sentences(text)
    if not sentences:
        raise RuntimeError("text is empty or cannot be split")

    audio_segments: List[bytes] = []
    timestamps: List[Dict[str, Any]] = []
    current = 0.0

    ext = (audio_format or "mp3").lower()
    for s in sentences:
        seg = synthesize_speech(text=s, voice=voice, speed=speed, pitch=pitch, volume=volume, audio_format=ext)
        audio_segments.append(seg)
        dur = _probe_duration_seconds(seg, suffix="." + ext)
        timestamps.append({"text": s, "start": current, "end": current + dur, "duration": dur})
        current += dur

    if len(audio_segments) == 1:
        return audio_segments[0], timestamps

    ffmpeg = _resolve_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as td:
        files: List[str] = []
        for i, b in enumerate(audio_segments):
            p = os.path.join(td, f"seg_{i}.{ext}")
            with open(p, "wb") as f:
                f.write(b)
            files.append(p)

        list_path = os.path.join(td, "list.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for p in files:
                escaped_path = p.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        out_path = os.path.join(td, f"merged_{uuid.uuid4().hex}.{ext}")
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", out_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(out_path, "rb") as f:
            merged = f.read()

    return merged, timestamps
