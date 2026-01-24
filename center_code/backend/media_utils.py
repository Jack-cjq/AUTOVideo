import json
import os
import shutil
import subprocess
from typing import Any, Dict, Optional, Tuple


def resolve_ffmpeg_exe() -> str:
    try:
        from config import FFMPEG_PATH as config_ffmpeg_path

        ff = os.environ.get("FFMPEG_PATH") or config_ffmpeg_path
    except Exception:
        ff = os.environ.get("FFMPEG_PATH")

    ff = (ff or "").strip()
    if ff and os.path.exists(ff):
        return os.path.abspath(ff)

    which = shutil.which("ffmpeg")
    if which:
        return which

    common_paths = [
        r"D:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    raise RuntimeError("未找到 FFmpeg，可在 PATH 安装或设置 FFMPEG_PATH")


def resolve_ffprobe_exe() -> str:
    ffprobe_env = (os.environ.get("FFPROBE_PATH") or "").strip()
    if ffprobe_env and os.path.exists(ffprobe_env):
        return os.path.abspath(ffprobe_env)

    # If FFMPEG_PATH is configured, try sibling ffprobe.
    try:
        ffmpeg_exe = resolve_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        candidate = os.path.join(ffmpeg_dir, "ffprobe.exe" if os.name == "nt" else "ffprobe")
        if os.path.exists(candidate):
            return candidate
    except Exception:
        pass

    which = shutil.which("ffprobe")
    if which:
        return which

    common_paths = [
        r"D:\ffmpeg\bin\ffprobe.exe",
        r"C:\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    raise RuntimeError("未找到 ffprobe，可在 PATH 安装或设置 FFPROBE_PATH/FFMPEG_PATH")


def ffprobe(path: str) -> Dict[str, Any]:
    exe = resolve_ffprobe_exe()
    cmd = [
        exe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        stderr = (p.stderr or "").strip()
        raise RuntimeError(f"ffprobe 失败: {stderr or 'unknown error'}")
    try:
        return json.loads(p.stdout or "{}")
    except Exception as e:
        raise RuntimeError(f"ffprobe 输出解析失败: {e}")


def _first_stream(probe_data: Dict[str, Any], codec_type: str) -> Optional[Dict[str, Any]]:
    for s in probe_data.get("streams") or []:
        try:
            if (s.get("codec_type") or "").lower() == codec_type:
                return s
        except Exception:
            continue
    return None


def summarize_probe(probe_data: Dict[str, Any]) -> Dict[str, Any]:
    fmt = probe_data.get("format") or {}
    v = _first_stream(probe_data, "video") or {}
    a = _first_stream(probe_data, "audio") or {}

    def _f(k, default=None):
        return fmt.get(k, default)

    def _s(st, k, default=None):
        return (st or {}).get(k, default)

    return {
        "format": {
            "format_name": _f("format_name"),
            "duration": _f("duration"),
            "size": _f("size"),
            "bit_rate": _f("bit_rate"),
        },
        "video": {
            "codec_name": _s(v, "codec_name"),
            "pix_fmt": _s(v, "pix_fmt"),
            "profile": _s(v, "profile"),
            "width": _s(v, "width"),
            "height": _s(v, "height"),
            "r_frame_rate": _s(v, "r_frame_rate"),
            "avg_frame_rate": _s(v, "avg_frame_rate"),
            "bits_per_raw_sample": _s(v, "bits_per_raw_sample"),
        }
        if v
        else None,
        "audio": {
            "codec_name": _s(a, "codec_name"),
            "sample_rate": _s(a, "sample_rate"),
            "channels": _s(a, "channels"),
            "channel_layout": _s(a, "channel_layout"),
        }
        if a
        else None,
    }


def _coerce_int(v) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def _coerce_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def decide_transcode(kind: str, probe_data: Dict[str, Any]) -> Tuple[bool, str]:
    kind = (kind or "").lower().strip()
    if kind == "video":
        v = _first_stream(probe_data, "video") or {}
        codec = (v.get("codec_name") or "").lower()
        pix_fmt = (v.get("pix_fmt") or "").lower()
        bits_raw = _coerce_int(v.get("bits_per_raw_sample"))

        safe_codec = codec == "h264"
        safe_pix = pix_fmt == "yuv420p" if pix_fmt else False
        safe_bits = (bits_raw is None) or (bits_raw <= 8)

        if safe_codec and safe_pix and safe_bits:
            return (False, "h264+yuv420p+8bit")
        return (True, f"codec={codec or 'unknown'},pix_fmt={pix_fmt or 'unknown'},bits={bits_raw or 'unknown'}")

    if kind == "audio":
        a = _first_stream(probe_data, "audio") or {}
        codec = (a.get("codec_name") or "").lower()
        if codec == "mp3":
            return (False, "mp3")
        return (True, f"codec={codec or 'unknown'}")

    return (False, "n/a")


def get_duration_seconds(probe_data: Dict[str, Any]) -> float:
    fmt = probe_data.get("format") or {}
    d = _coerce_float(fmt.get("duration"))
    return float(d or 0.0)

