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
from utils.baidu_asr import recognize_speech
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


@ai_bp.route('/tts/delete-temp', methods=['POST'])
@login_required
def ai_tts_delete_temp():
    """
    删除临时TTS文件接口
    
    请求方法: POST
    路径: /api/ai/tts/delete-temp
    认证: 需要登录
    
    请求体 (JSON):
        {
            "preview_url": "string"  # 临时文件的预览URL，如 "/uploads/tts/tts_xxx.mp3"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "ok"
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        preview_url = (data.get("preview_url") or "").strip()
        
        if not preview_url:
            return response_error("preview_url 不能为空", 400)
        
        # 从预览URL中提取文件路径
        # preview_url 格式: "/uploads/tts/tts_xxx.mp3"
        if not preview_url.startswith("/uploads/tts/"):
            return response_error("只能删除临时TTS文件（路径必须包含 /tts/）", 400)
        
        # 提取文件名
        filename = preview_url.replace("/uploads/tts/", "").lstrip("/")
        if not filename.startswith("tts_") or not filename.endswith(".mp3"):
            return response_error("无效的临时TTS文件名", 400)
        
        # 构建完整文件路径
        file_path = os.path.join(TTS_DIR, filename)
        
        # 安全检查：确保文件在 TTS_DIR 目录内
        file_path_abs = os.path.abspath(file_path)
        tts_dir_abs = os.path.abspath(TTS_DIR)
        if not file_path_abs.startswith(tts_dir_abs):
            return response_error("无效的文件路径", 400)
        
        # 删除文件
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已删除临时TTS文件: {file_path}")
                return response_success(None, "临时文件已删除")
            except Exception as e:
                logger.exception(f"删除临时TTS文件失败: {file_path}")
                return response_error(f"删除文件失败：{e}", 500)
        else:
            # 文件不存在，也返回成功（可能已经被删除）
            return response_success(None, "文件不存在或已删除")
    
    except Exception as e:
        logger.exception("删除临时TTS文件失败")
        return response_error(f"删除失败：{e}", 500)


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
            "text": "string",             # 可选，文案文本（如果为空且auto_recognize=true，则从音频识别）
            "audio_material_id": int,      # 必填，音频素材ID（用于获取时长和识别文字）
            "auto_recognize": bool        # 可选，是否自动从音频识别文字（默认false）
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
        logger.info(f"收到字幕生成请求: {data}")
        
        text = (data.get("text") or "").strip()
        audio_material_id = data.get("audio_material_id")
        auto_recognize = data.get("auto_recognize", False)  # 是否自动从音频识别文字
        
        logger.info(f"解析参数: text长度={len(text)}, audio_material_id={audio_material_id}, auto_recognize={auto_recognize}")

        if audio_material_id is None:
            logger.error("audio_material_id 为空")
            return response_error("audio_material_id 不能为空（用于取配音时长）", 400)

        try:
            audio_material_id = int(audio_material_id)
        except Exception:
            return response_error("audio_material_id 必须是整数", 400)

        # 查询音频素材
        with get_db() as db:
            mat = db.query(Material).filter(Material.id == audio_material_id).first()
            if not mat or mat.type != "audio":
                logger.error(f"音频素材不存在或类型错误: audio_material_id={audio_material_id}, mat={mat}")
                return response_error("audio_material_id 不存在或类型不是 audio", 400)

            # 标准化路径（处理Windows路径问题）
            abs_audio = os.path.normpath(os.path.join(BASE_DIR, mat.path))
            logger.info(f"查找音频文件: 相对路径={mat.path}, 绝对路径={abs_audio}")
            
            if not os.path.isfile(abs_audio):
                logger.error(f"音频文件不存在: {abs_audio}")
                return response_error(f"音频文件不存在：{mat.path}（绝对路径：{abs_audio}）", 400)
            
            logger.info(f"音频文件验证成功: {abs_audio}")

        # 如果文案为空且启用了自动识别，从音频中识别文字
        recognized_text = None
        if not text and auto_recognize:
            try:
                logger.info("开始从音频识别文字...")
                # 检测音频格式（recognize_speech会自动处理格式转换）
                text = recognize_speech(abs_audio)
                recognized_text = text
                logger.info(f"语音识别成功，识别出 {len(text)} 个字符: {text[:100]}...")
                
                if not text:
                    return response_error("语音识别结果为空，请手动输入文案", 400)
            except Exception as asr_error:
                logger.exception(f"语音识别失败: {asr_error}")
                return response_error(f"从音频识别文字失败：{str(asr_error)}，请手动输入文案", 500)
        
        # 如果仍然没有文案，返回错误
        if not text:
            logger.error("文案为空且未启用自动识别")
            return response_error("text 不能为空，或者启用 auto_recognize 参数从音频自动识别", 400)

        # 获取音频时长（需要 ffmpeg-python）
        try:
            import ffmpeg
            logger.info(f"开始获取音频时长: {abs_audio}")
            probe = ffmpeg.probe(abs_audio)
            fmt = probe.get("format") or {}
            duration = float(fmt.get("duration") or 0.0)
            logger.info(f"音频时长获取成功: {duration} 秒")
        except ImportError:
            logger.error("缺少 ffmpeg-python 库")
            return response_error("缺少 ffmpeg-python，无法获取音频时长", 500)
        except Exception as e:
            logger.exception(f"获取音频时长失败: {e}")
            return response_error(f"获取音频时长失败：{str(e)}", 500)

        if duration <= 0:
            logger.error(f"音频时长无效: {duration}")
            return response_error("音频时长无效，无法生成字幕", 500)

        # 生成字幕
        try:
            logger.info(f"开始生成字幕: 文案长度={len(text)}, 时长={duration}秒")
            items = generate_srt_items(text=text, total_duration_sec=duration)
            srt_text = render_srt(items)
            logger.info(f"字幕生成成功: {len(items)} 条字幕项")
        except Exception as e:
            logger.exception(f"生成字幕失败: {e}")
            return response_error(f"生成字幕失败：{str(e)}", 500)

        # 确保字幕目录存在
        try:
            os.makedirs(SUBTITLE_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"创建字幕目录失败: {e}")
            return response_error(f"创建字幕目录失败：{str(e)}", 500)

        # 保存字幕文件
        try:
            name = new_srt_filename("tts")
            abs_path = os.path.join(SUBTITLE_DIR, name)
            logger.info(f"保存字幕文件: {abs_path}")
            
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(srt_text)
            
            logger.info(f"字幕文件保存成功: {abs_path}, 大小={os.path.getsize(abs_path)} 字节")
        except Exception as e:
            logger.exception(f"保存字幕文件失败: {e}")
            return response_error(f"保存字幕文件失败：{str(e)}", 500)

        rel_path = os.path.relpath(abs_path, BASE_DIR).replace(os.sep, "/")
        uploads_rel = os.path.relpath(abs_path, os.path.join(BASE_DIR, 'uploads')).replace(os.sep, '/')
        preview_url = f"/uploads/{uploads_rel}"

        result_data = {
            "path": rel_path,
            "preview_url": preview_url,
            "duration": duration,
        }
        
        # 如果是从音频识别的文字，也返回识别结果
        if recognized_text:
            result_data["recognized_text"] = recognized_text

        return response_success(result_data, "ok")
    
    except Exception as e:
        logger.exception("Subtitle generation failed")
        return response_error(f"生成字幕失败：{e}", 500)

