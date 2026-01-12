"""
AI 功能 API（文案生成、TTS、字幕生成）
"""
import os
import sys
import uuid
import logging

from flask import Blueprint, request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Material
from db import get_db

# 导入工具函数
from utils.ai import deepseek_generate_copies
from utils.baidu_tts import synthesize_speech
from utils.subtitles import generate_srt_items, new_srt_filename, render_srt

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TTS_DIR = os.path.join(BASE_DIR, 'uploads', 'tts')
SUBTITLE_DIR = os.path.join(BASE_DIR, 'uploads', 'subtitles')
MATERIAL_AUDIO_DIR = os.path.join(BASE_DIR, 'uploads', 'materials', 'audios')

# 自动创建目录
for dir_path in [TTS_DIR, SUBTITLE_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


@ai_bp.route('/copy/generate', methods=['POST'])
@login_required
def ai_copy_generate():
    """
    AI 文案生成接口
    
    请求方法: POST
    路径: /api/ai/copy/generate
    认证: 需要登录
    
    请求体 (JSON):
        {
            "theme": "string",        # 必填，主题
            "keywords": "string",     # 可选，关键词
            "reference": "string",    # 可选，参考文案
            "count": int,             # 可选，生成数量（1-10），默认 3
            "model": "string"         # 可选，模型名称
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "生成成功",
            "data": {
                "copies": [
                    {
                        "title": "string",
                        "lines": ["string"],
                        "tags": ["string"]
                    }
                ]
            }
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        theme = (data.get("theme") or "").strip()
        keywords = (data.get("keywords") or "").strip()
        reference = (data.get("reference") or data.get("ref") or "").strip()
        count = data.get("count", 3)
        model = (data.get("model") or "").strip() or None

        if not theme:
            return response_error("theme 不能为空", 400)

        try:
            count = int(count)
        except Exception:
            count = 3
        count = max(1, min(count, 10))

        result = deepseek_generate_copies(
            theme=theme,
            keywords=keywords,
            reference=reference,
            count=count,
            model=model,
        )
        return response_success(result, "生成成功")
    
    except Exception as e:
        logger.exception("AI copy generate failed")
        return response_error(f"生成失败：{e}", 500)


@ai_bp.route('/tts/voices', methods=['GET'])
@login_required
def ai_tts_voices():
    """
    获取 TTS 音色列表接口
    
    请求方法: GET
    路径: /api/ai/tts/voices
    认证: 需要登录
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "ok",
            "data": [
                {
                    "id": int,
                    "key": "string",
                    "name": "string"
                }
            ]
        }
    """
    voices = [
        {"id": 0, "key": "female", "name": "标准女声"},
        {"id": 1, "key": "male", "name": "标准男声"},
        {"id": 3, "key": "duyy", "name": "度逍遥（情感男声）"},
        {"id": 4, "key": "duya", "name": "度丫丫（童声）"},
    ]
    return response_success(voices, "ok")


@ai_bp.route('/tts/synthesize', methods=['POST'])
@login_required
def ai_tts_synthesize():
    """
    TTS 语音合成接口
    
    请求方法: POST
    路径: /api/ai/tts/synthesize
    认证: 需要登录
    
    请求体 (JSON):
        {
            "text": "string",         # 必填，要合成的文本
            "voice": int,             # 可选，音色ID，默认 0
            "speed": int,             # 可选，语速（0-15），默认 5
            "pitch": int,             # 可选，音调（0-15），默认 5
            "volume": int,            # 可选，音量（0-15），默认 5
            "persist": bool           # 可选，是否保存到素材库，默认 false
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "ok",
            "data": {
                "preview_url": "string",
                "path": "string",
                "material_id": int | null
            }
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        voice = data.get("voice", 0)
        speed = data.get("speed", 5)
        pitch = data.get("pitch", 5)
        volume = data.get("volume", 5)
        persist = data.get("persist") is True

        if not text:
            return response_error("text 不能为空", 400)

        # 兼容：前端传 key
        voice_map = {"female": 0, "male": 1, "duyy": 3, "kid": 4, "duya": 4}
        if isinstance(voice, str):
            voice = voice_map.get(voice.strip(), voice)

        audio_bytes = synthesize_speech(
            text=text,
            voice=voice,
            speed=speed,
            pitch=pitch,
            volume=volume,
            audio_format="mp3",
        )

        # 写入 uploads/tts，前端可直接预览
        tmp_name = f"tts_{uuid.uuid4().hex}.mp3"
        tmp_path = os.path.join(TTS_DIR, tmp_name)
        
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)

        rel_path = os.path.relpath(tmp_path, BASE_DIR).replace(os.sep, "/")
        uploads_rel = os.path.relpath(tmp_path, os.path.join(BASE_DIR, 'uploads')).replace(os.sep, '/')
        preview_url = f"/uploads/{uploads_rel}"

        material_id = None
        if persist:
            # 迁移到 materials/audios 并入库
            final_name = f"{uuid.uuid4().hex}.mp3"
            final_path = os.path.join(MATERIAL_AUDIO_DIR, final_name)
            
            try:
                os.replace(tmp_path, final_path)
                rel_path = os.path.relpath(final_path, BASE_DIR).replace(os.sep, "/")
                uploads_rel = os.path.relpath(final_path, os.path.join(BASE_DIR, 'uploads')).replace(os.sep, '/')
                preview_url = f"/uploads/{uploads_rel}"
                
                size = None
                try:
                    size = os.path.getsize(final_path)
                except Exception:
                    pass
                
                with get_db() as db:
                    material = Material(
                        name=f"TTS_{final_name}",
                        path=rel_path,
                        type="audio",
                        duration=None,
                        width=None,
                        height=None,
                        size=size
                    )
                    db.add(material)
                    db.flush()
                    db.commit()
                    material_id = material.id
            except Exception as e:
                logger.exception("Persist TTS failed")
                # 如果入库失败，尝试删除文件
                try:
                    if os.path.exists(final_path):
                        os.remove(final_path)
                except Exception:
                    pass
                return response_error(f"TTS 入库失败：{e}", 500)

        return response_success({
            "preview_url": preview_url,
            "path": rel_path,
            "material_id": material_id,
        }, "ok")
    
    except Exception as e:
        logger.exception("TTS synthesize failed")
        return response_error(f"TTS 合成失败：{e}", 500)


@ai_bp.route('/subtitle/srt', methods=['POST'])
@login_required
def ai_subtitle_srt():
    """
    生成字幕文件接口
    
    请求方法: POST
    路径: /api/ai/subtitle/srt
    认证: 需要登录
    
    请求体 (JSON):
        {
            "text": "string",             # 必填，文案文本
            "audio_material_id": int      # 必填，音频素材ID（用于获取时长）
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "ok",
            "data": {
                "path": "string",
                "preview_url": "string",
                "duration": float
            }
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        audio_material_id = data.get("audio_material_id")

        if not text:
            return response_error("text 不能为空", 400)
        if audio_material_id is None:
            return response_error("audio_material_id 不能为空（用于取配音时长）", 400)

        try:
            audio_material_id = int(audio_material_id)
        except Exception:
            return response_error("audio_material_id 必须是整数", 400)

        # 查询音频素材
        with get_db() as db:
            mat = db.query(Material).filter(Material.id == audio_material_id).first()
            if not mat or mat.type != "audio":
                return response_error("audio_material_id 不存在或类型不是 audio", 400)

            abs_audio = os.path.join(BASE_DIR, mat.path)
            if not os.path.isfile(abs_audio):
                return response_error(f"音频文件不存在：{mat.path}", 400)

        # 获取音频时长（需要 ffmpeg-python）
        try:
            import ffmpeg
            probe = ffmpeg.probe(abs_audio)
            fmt = probe.get("format") or {}
            duration = float(fmt.get("duration") or 0.0)
        except ImportError:
            return response_error("缺少 ffmpeg-python，无法获取音频时长", 500)
        except Exception as e:
            return response_error(f"获取音频时长失败：{e}", 500)

        if duration <= 0:
            return response_error("音频时长无效，无法生成字幕", 500)

        # 生成字幕
        try:
            items = generate_srt_items(text=text, total_duration_sec=duration)
            srt_text = render_srt(items)
        except Exception as e:
            return response_error(f"生成字幕失败：{e}", 500)

        # 保存字幕文件
        name = new_srt_filename("tts")
        abs_path = os.path.join(SUBTITLE_DIR, name)
        
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(srt_text)

        rel_path = os.path.relpath(abs_path, BASE_DIR).replace(os.sep, "/")
        uploads_rel = os.path.relpath(abs_path, os.path.join(BASE_DIR, 'uploads')).replace(os.sep, '/')
        preview_url = f"/uploads/{uploads_rel}"

        return response_success({
            "path": rel_path,
            "preview_url": preview_url,
            "duration": duration,
        }, "ok")
    
    except Exception as e:
        logger.exception("Subtitle generation failed")
        return response_error(f"生成字幕失败：{e}", 500)

