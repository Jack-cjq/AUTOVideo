"""
百度语音识别（ASR）模块
用于将音频文件转换为文字
"""
import os
import sys
import uuid
import requests
import base64
from typing import Optional

try:
    from config import BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY, BAIDU_CUID
except ImportError:
    BAIDU_APP_ID = os.environ.get("BAIDU_APP_ID", "")
    BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "")
    BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")
    BAIDU_CUID = os.environ.get("BAIDU_CUID", "")

# 缓存 access_token
_token_cache = {"token": None, "expires_at": 0}


def _get_access_token() -> str:
    """
    获取百度语音识别 access_token
    """
    import time
    
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]
    
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY,
    }
    
    try:
        resp = requests.post(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if "error" in data:
            raise RuntimeError(f"获取 access_token 失败：{data.get('error_description', data.get('error'))}")
        
        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 2592000))  # 默认30天
        
        _token_cache["token"] = token
        _token_cache["expires_at"] = now + max(60, expires_in)
        return str(token)
    except Exception as e:
        raise RuntimeError(f"获取 access_token 失败：{e}")


def recognize_speech(
    audio_file_path: str,
    format: Optional[str] = None,
    rate: int = 16000,
    dev_pid: int = 1537,  # 1537=普通话(支持简单的英文识别)
) -> str:
    """
    百度语音识别（ASR）：audio file -> text
    
    Args:
        audio_file_path: 音频文件路径
        format: 音频格式（自动检测，支持mp3, wav, amr, m4a等）
        rate: 采样率（16000, 8000等）
        dev_pid: 语言模型（1537=普通话, 1737=英语, 1637=粤语等）
    
    Returns:
        识别出的文字内容
    """
    if not os.path.isfile(audio_file_path):
        raise RuntimeError(f"音频文件不存在：{audio_file_path}")
    
    # 自动检测音频格式
    original_audio_path = audio_file_path
    converted_audio_path = None
    if not format:
        ext = os.path.splitext(audio_file_path)[1].lower().lstrip('.')
        # 百度ASR支持的格式：pcm, wav, amr, m4a
        # mp3需要转换为wav
        if ext == 'mp3':
            format = 'wav'
            # 需要转换为wav格式
            try:
                converted_audio_path = _convert_mp3_to_wav(audio_file_path)
                audio_file_path = converted_audio_path
            except Exception as convert_error:
                # 如果转换失败，尝试直接使用mp3（某些情况下百度API可能支持）
                print(f"[ASR] 音频转换失败，尝试直接使用原始格式: {convert_error}")
                format = 'mp3'
        elif ext in ['wav', 'amr', 'm4a']:
            format = ext
        else:
            # 默认尝试wav格式
            format = 'wav'
            try:
                converted_audio_path = _convert_to_wav(audio_file_path)
                audio_file_path = converted_audio_path
            except Exception as convert_error:
                print(f"[ASR] 音频转换失败，尝试直接使用原始格式: {convert_error}")
                format = ext or 'mp3'
    
    # 读取音频文件
    try:
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
    except Exception as read_error:
        # 清理临时转换文件
        if converted_audio_path and os.path.exists(converted_audio_path):
            try:
                os.remove(converted_audio_path)
            except Exception:
                pass
        raise RuntimeError(f"读取音频文件失败：{read_error}")
    
    # 检查文件大小（百度ASR限制：base64编码后不超过4MB）
    # base64编码会增加约33%的大小
    if len(audio_data) > 3 * 1024 * 1024:  # 约3MB原始数据
        # 清理临时转换文件
        if converted_audio_path and os.path.exists(converted_audio_path):
            try:
                os.remove(converted_audio_path)
            except Exception:
                pass
        raise RuntimeError(f"音频文件过大（{len(audio_data) / 1024 / 1024:.2f}MB），请使用较短的音频或分段识别")
    
    # 转换为base64
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")
    
    # 获取 access_token
    token = _get_access_token()
    cuid = (BAIDU_CUID or "").strip() or str(uuid.uuid4())
    
    # 调用百度语音识别API
    url = "https://vop.baidu.com/server_api"
    headers = {"Content-Type": "application/json"}
    
    data = {
        "format": format,
        "rate": rate,
        "channel": 1,  # 单声道
        "cuid": cuid,
        "len": len(audio_data),
        "speech": audio_base64,
        "dev_pid": dev_pid,
        "token": token,
    }
    
    try:
        resp = requests.post(url, json=data, headers=headers, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        
        if result.get("err_no") != 0:
            error_msg = result.get("err_msg", "未知错误")
            error_code = result.get("err_no")
            # 清理临时转换文件
            if converted_audio_path and os.path.exists(converted_audio_path):
                try:
                    os.remove(converted_audio_path)
                except Exception:
                    pass
            raise RuntimeError(f"百度语音识别失败：{error_msg} (错误码: {error_code})")
        
        # 提取识别结果
        results = result.get("result", [])
        if not results:
            # 清理临时转换文件
            if converted_audio_path and os.path.exists(converted_audio_path):
                try:
                    os.remove(converted_audio_path)
                except Exception:
                    pass
            raise RuntimeError("语音识别结果为空")
        
        # 合并所有识别结果
        text = "".join(results)
        
        # 清理临时转换文件
        if converted_audio_path and os.path.exists(converted_audio_path):
            try:
                os.remove(converted_audio_path)
            except Exception:
                pass  # 忽略清理错误
        
        return text.strip()
        
    except requests.RequestException as e:
        # 清理临时转换文件
        if converted_audio_path and os.path.exists(converted_audio_path):
            try:
                os.remove(converted_audio_path)
            except Exception:
                pass
        raise RuntimeError(f"请求百度语音识别API失败：{e}")
    except Exception as e:
        # 清理临时转换文件
        if converted_audio_path and os.path.exists(converted_audio_path):
            try:
                os.remove(converted_audio_path)
            except Exception:
                pass
        raise RuntimeError(f"语音识别失败：{e}")


def _convert_mp3_to_wav(mp3_path: str) -> str:
    """
    将MP3文件转换为WAV格式（百度ASR需要）
    
    Returns:
        转换后的WAV文件路径
    """
    try:
        import ffmpeg
        import tempfile
        import shutil
        
        # 确保FFmpeg路径正确
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
            # 尝试查找系统PATH中的ffmpeg
            ffmpeg_path = shutil.which('ffmpeg')
            if not ffmpeg_path:
                # 尝试常见路径
                common_paths = [
                    r'D:\ffmpeg\bin\ffmpeg.exe',
                    r'C:\ffmpeg\bin\ffmpeg.exe',
                    r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        ffmpeg_path = path
                        ffmpeg_dir = os.path.dirname(ffmpeg_path)
                        if ffmpeg_dir not in os.environ.get('PATH', ''):
                            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
                        break
        
        if not ffmpeg_path or not os.path.exists(ffmpeg_path):
            raise RuntimeError(
                "未找到 FFmpeg 可执行文件，无法转换音频格式。\n"
                "解决方案：\n"
                "1. 安装 FFmpeg 并添加到系统 PATH\n"
                "2. 或设置环境变量 FFMPEG_PATH 指向 ffmpeg.exe 的完整路径\n"
                "3. 或在 config.py 中设置 FFMPEG_PATH"
            )
        
        # 创建临时WAV文件（使用uploads目录，避免权限问题）
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(BASE_DIR, 'uploads', 'tts')
        os.makedirs(temp_dir, exist_ok=True)
        
        wav_filename = f"asr_temp_{uuid.uuid4().hex}.wav"
        wav_path = os.path.join(temp_dir, wav_filename)
        
        try:
            # 使用ffmpeg转换：mp3 -> wav, 16kHz, 单声道
            stream = ffmpeg.input(mp3_path)
            stream = ffmpeg.output(
                stream,
                wav_path,
                acodec='pcm_s16le',  # PCM 16位
                ac=1,  # 单声道
                ar=16000  # 16kHz采样率
            )
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            if not os.path.exists(wav_path):
                raise RuntimeError(f"转换后的WAV文件不存在：{wav_path}")
            
            return wav_path
        except Exception as convert_error:
            # 如果转换失败，清理可能创建的文件
            if os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
            raise RuntimeError(f"FFmpeg转换失败：{convert_error}")
    except ImportError:
        raise RuntimeError("需要安装 ffmpeg-python 库来转换音频格式")
    except Exception as e:
        raise RuntimeError(f"音频格式转换失败：{e}")


def _convert_to_wav(audio_path: str) -> str:
    """
    将任意音频文件转换为WAV格式
    """
    return _convert_mp3_to_wav(audio_path)  # 复用转换函数

