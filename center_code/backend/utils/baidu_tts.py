"""
百度 TTS 语音合成工具
"""
import json
import threading
import time
import uuid
from typing import Any

import requests

# 导入配置
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BAIDU_API_KEY, BAIDU_SECRET_KEY, BAIDU_CUID


_TOKEN_LOCK = threading.Lock()
_TOKEN_CACHE: dict[str, Any] = {"token": None, "expire_at": 0.0}


def _require_baidu_credentials():
    api_key = (BAIDU_API_KEY or "").strip()
    secret_key = (BAIDU_SECRET_KEY or "").strip()
    if not api_key or not secret_key:
        raise RuntimeError("缺少百度 TTS 配置：BAIDU_API_KEY / BAIDU_SECRET_KEY")
    return api_key, secret_key


def _get_access_token() -> str:
    api_key, secret_key = _require_baidu_credentials()

    now = time.time()
    with _TOKEN_LOCK:
        token = _TOKEN_CACHE.get("token")
        expire_at = float(_TOKEN_CACHE.get("expire_at") or 0)
        if token and now < expire_at - 30:
            return str(token)

        resp = requests.get(
            "https://aip.baidubce.com/oauth/2.0/token",
            params={
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"获取百度 access_token 失败：{data}")
        expires_in = int(data.get("expires_in") or 0)
        _TOKEN_CACHE["token"] = token
        _TOKEN_CACHE["expire_at"] = now + max(60, expires_in)
        return str(token)


def synthesize_speech(
    *,
    text: str,
    voice: str | int = 0,
    speed: int = 5,
    pitch: int = 5,
    volume: int = 5,
    audio_format: str = "mp3",
) -> bytes:
    """
    百度语音合成（TTS）：text -> audio bytes
    - voice: 百度 per（0/1/3/4...），也可传字符串（可在路由层映射）
    - speed/pitch/volume: 0~15
    - audio_format: mp3 / wav
    """
    text = (text or "").strip()
    if not text:
        raise RuntimeError("text 不能为空")
    if len(text) > 500:
        raise RuntimeError("text 过长（建议 <= 500 字）")

    tok = _get_access_token()
    cuid = (BAIDU_CUID or "").strip() or str(uuid.uuid4())

    speed = int(speed)
    pitch = int(pitch)
    volume = int(volume)
    speed = max(0, min(speed, 15))
    pitch = max(0, min(pitch, 15))
    volume = max(0, min(volume, 15))

    # aue: 3=mp3 6=wav
    aue = 3 if audio_format.lower() == "mp3" else 6

    per = int(voice) if str(voice).isdigit() else 0
    resp = requests.post(
        "https://tsn.baidu.com/text2audio",
        data={
            "tex": text,
            "tok": tok,
            "cuid": cuid,
            "ctp": 1,
            "lan": "zh",
            "per": per,
            "spd": speed,
            "pit": pitch,
            "vol": volume,
            "aue": aue,
        },
        timeout=30,
    )
    resp.raise_for_status()

    # 成功返回 audio bytes；失败通常是 JSON
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "audio" in ctype or ctype.startswith("application/octet-stream"):
        return resp.content

    try:
        err = resp.json()
    except Exception:
        err = resp.text[:500]
    raise RuntimeError(f"百度 TTS 合成失败：{err}")

