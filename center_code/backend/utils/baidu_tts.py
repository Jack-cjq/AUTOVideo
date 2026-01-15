"""
百度 TTS 语音合成工具
"""
import json
import threading
import time
import uuid
from typing import Any, Union, Dict, List, Tuple
import io

import requests
import ffmpeg

# 导入配置
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BAIDU_API_KEY, BAIDU_SECRET_KEY, BAIDU_CUID


_TOKEN_LOCK = threading.Lock()
_TOKEN_CACHE: Dict[str, Any] = {"token": None, "expire_at": 0.0}


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
    voice: Union[str, int] = 0,
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


def get_audio_duration(audio_bytes: bytes) -> float:
    """
    获取音频时长（秒）
    :param audio_bytes: 音频字节数据
    :return: 时长（秒）
    """
    try:
        # 将音频字节写入临时文件
        import tempfile
        import shutil
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        try:
            # 检查并配置 FFmpeg 路径
            try:
                from config import FFMPEG_PATH as config_ffmpeg_path
                ffmpeg_path = os.environ.get('FFMPEG_PATH') or config_ffmpeg_path
            except ImportError:
                ffmpeg_path = os.environ.get('FFMPEG_PATH')
            
            if ffmpeg_path and os.path.exists(ffmpeg_path):
                # 设置 ffmpeg-python 使用指定的路径
                ffmpeg_path = os.path.abspath(ffmpeg_path)
                ffmpeg_dir = os.path.dirname(ffmpeg_path)
                if ffmpeg_dir not in os.environ.get('PATH', ''):
                    os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
            else:
                # 尝试从系统 PATH 中查找
                ffmpeg_path = shutil.which('ffmpeg')
                if not ffmpeg_path:
                    # 尝试常见路径
                    common_paths = [
                        r'D:\ffmpeg\bin\ffmpeg.exe',
                        r'C:\ffmpeg\bin\ffmpeg.exe',
                        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
                        r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
                    ]
                    for path in common_paths:
                        if os.path.exists(path):
                            ffmpeg_path = path
                            ffmpeg_dir = os.path.dirname(ffmpeg_path)
                            if ffmpeg_dir not in os.environ.get('PATH', ''):
                                os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
                            break
            
            # 使用 ffmpeg 获取时长
            probe = ffmpeg.probe(tmp_path)
            fmt = probe.get("format") or {}
            duration = float(fmt.get("duration") or 0.0)
            return duration
        finally:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as e:
        # 如果获取时长失败，返回估算值（按字符数估算，大约每秒3-4个字）
        print(f"[TTS] 警告：获取音频时长失败，使用估算值：{e}")
        return max(1.0, len(audio_bytes) / 1000.0)


def synthesize_speech_with_timestamps(
    *,
    text: str,
    voice: Union[str, int] = 0,
    speed: int = 5,
    pitch: int = 5,
    volume: int = 5,
    audio_format: str = "mp3",
) -> Tuple[bytes, List[Dict[str, Any]]]:
    """
    按句切割文案，每句单独生成TTS，返回合并后的音频和每句的时间戳信息
    
    :param text: 完整文案
    :param voice: 音色ID
    :param speed: 语速
    :param pitch: 音调
    :param volume: 音量
    :param audio_format: 音频格式
    :return: (合并后的音频字节, 时间戳列表)
        时间戳列表格式: [{"text": "句子", "start": 0.0, "end": 2.5, "duration": 2.5}, ...]
    """
    # 导入句子分割函数
    from utils.subtitles import split_into_sentences
    
    # 按句切割
    sentences = split_into_sentences(text)
    if not sentences:
        raise RuntimeError("文案为空或无法分割")
    
    # 兼容：前端传 key
    voice_map = {"female": 0, "male": 1, "duyy": 3, "kid": 4, "duya": 4}
    if isinstance(voice, str):
        voice = voice_map.get(voice.strip(), voice)
    voice = int(voice) if str(voice).isdigit() else 0
    
    # 每句单独生成TTS
    audio_segments = []
    timestamps = []
    current_time = 0.0
    
    for sentence in sentences:
        if not sentence.strip():
            continue
        
        try:
            # 生成单句TTS
            audio_bytes = synthesize_speech(
                text=sentence,
                voice=voice,
                speed=speed,
                pitch=pitch,
                volume=volume,
                audio_format=audio_format,
            )
            
            # 获取实际时长
            duration = get_audio_duration(audio_bytes)
            
            # 记录时间戳
            timestamps.append({
                "text": sentence.strip(),
                "start": current_time,
                "end": current_time + duration,
                "duration": duration
            })
            
            audio_segments.append(audio_bytes)
            current_time += duration
            
        except Exception as e:
            # 如果某句生成失败，跳过并记录警告
            print(f"[TTS] 警告：句子生成失败，跳过：{sentence[:50]}... 错误：{e}")
            continue
    
    if not audio_segments:
        raise RuntimeError("所有句子TTS生成失败")
    
    # 合并音频
    try:
        merged_audio = merge_audio_segments(audio_segments, audio_format)
    except Exception as e:
        # 如果合并失败，返回第一段音频（至少能工作）
        print(f"[TTS] 警告：音频合并失败，使用第一段：{e}")
        merged_audio = audio_segments[0]
    
    return merged_audio, timestamps


def merge_audio_segments(audio_segments: List[bytes], audio_format: str = "mp3") -> bytes:
    """
    合并多个音频段
    :param audio_segments: 音频字节列表
    :param audio_format: 音频格式
    :return: 合并后的音频字节
    """
    if len(audio_segments) == 1:
        return audio_segments[0]
    
    try:
        import tempfile
        import shutil
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        input_files = []
        
        try:
            # 将每段音频写入临时文件
            for i, audio_bytes in enumerate(audio_segments):
                tmp_file = os.path.join(temp_dir, f"segment_{i}.{audio_format}")
                with open(tmp_file, "wb") as f:
                    f.write(audio_bytes)
                input_files.append(tmp_file)
            
            # 使用 ffmpeg 合并音频
            output_file = os.path.join(temp_dir, "merged.mp3")
            
            # 构建 concat 文件
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w", encoding="utf-8") as f:
                for input_file in input_files:
                    # 转义路径中的单引号
                    escaped_path = input_file.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            
            # 执行合并
            ffmpeg.input(concat_file, format="concat", safe=0).output(
                output_file,
                acodec="copy"  # 直接复制音频流，不重新编码
            ).overwrite_output().run(quiet=True)
            
            # 读取合并后的音频
            with open(output_file, "rb") as f:
                merged_audio = f.read()
            
            return merged_audio
            
        finally:
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
                
    except Exception as e:
        # 如果合并失败，尝试简单拼接（可能不工作，但至少不会崩溃）
        print(f"[TTS] 警告：FFmpeg合并失败，尝试简单拼接：{e}")
        return b"".join(audio_segments)

