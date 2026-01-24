"""
视频剪辑 API（同步/异步剪辑、任务管理、成品管理）
"""
import os
import sys
import threading
import time
import datetime
import logging
import json
import shutil
import uuid
from typing import Optional

from flask import Blueprint, request, send_from_directory

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Material, VideoEditTask, VideoLibrary
from db import get_db
from utils.video_editor import video_editor, get_abs_path
from utils.cos_service import list_objects_from_cos

# 检查COS是否可用
try:
    from utils.cos_service import upload_file_to_cos, generate_cos_key, delete_file_from_cos
    COS_AVAILABLE = True
except ImportError:
    COS_AVAILABLE = False
    print("警告：腾讯云COS SDK未安装，成品将使用本地存储")

logger = logging.getLogger(__name__)

editor_bp = Blueprint('editor', __name__, url_prefix='/api')

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_VIDEO_DIR = os.path.join(BASE_DIR, 'uploads', 'videos')
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
SUBTITLE_DIR = os.path.join(UPLOADS_DIR, 'subtitles')

# 自动创建目录
if not os.path.exists(OUTPUT_VIDEO_DIR):
    os.makedirs(OUTPUT_VIDEO_DIR)

# 片段缓存目录（用于图片转视频片段等）
SEGMENTS_DIR = os.path.join(OUTPUT_VIDEO_DIR, 'segments')
os.makedirs(SEGMENTS_DIR, exist_ok=True)

# 资源与并发限制（可用环境变量覆盖）
MAX_CLIPS = int(os.environ.get("MAX_EDIT_CLIPS", "100"))
MAX_TOTAL_SECONDS = float(os.environ.get("MAX_EDIT_TOTAL_SECONDS", "1800"))
MAX_CONCURRENT_EDIT_THREADS = int(os.environ.get("MAX_EDIT_THREADS", "2"))
SEGMENT_DIR_TTL_SECONDS = int(os.environ.get("SEGMENT_DIR_TTL_SECONDS", "86400"))


def _ensure_within_dir(path: str, base_dir: str) -> str:
    path = os.path.normpath(path)
    base_dir = os.path.normpath(base_dir)
    try:
        if os.path.commonpath([os.path.normcase(path), os.path.normcase(base_dir)]) != os.path.normcase(base_dir):
            raise ValueError("path outside allowed directory")
    except Exception:
        raise ValueError("path outside allowed directory")
    return path


def _cleanup_old_segment_dirs():
    try:
        now_ts = time.time()
        if not os.path.isdir(SEGMENTS_DIR):
            return
        for name in os.listdir(SEGMENTS_DIR):
            if not name.startswith("task_"):
                continue
            p = os.path.join(SEGMENTS_DIR, name)
            try:
                if os.path.isdir(p):
                    mtime = os.path.getmtime(p)
                    if now_ts - mtime > SEGMENT_DIR_TTL_SECONDS:
                        shutil.rmtree(p, ignore_errors=True)
            except Exception:
                continue
    except Exception:
        pass

# 异步任务管理
_TASK_THREADS = {}
_TASK_LOCK = threading.Lock()


def _probe_duration_seconds(path: str) -> float:
    try:
        import ffmpeg  # type: ignore

        probe = ffmpeg.probe(path)
        fmt = probe.get("format") or {}
        return float(fmt.get("duration") or 0) or 0.0
    except Exception:
        return 0.0


def _resolve_ffmpeg_exe() -> str:
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
        r"D:\\ffmpeg\\bin\\ffmpeg.exe",
        r"C:\\ffmpeg\\bin\\ffmpeg.exe",
        r"C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
        r"C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    raise RuntimeError("未找到 FFmpeg，可在系统 PATH 安装或设置 FFMPEG_PATH")


def _make_image_segment(
    *,
    image_path: str,
    duration: float,
    out_path: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> None:
    import subprocess

    ffmpeg_exe = _resolve_ffmpeg_exe()
    d = float(duration or 0)
    if d <= 0:
        raise RuntimeError("图片片段 duration 必须 > 0")

    vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p,setsar=1"
    cmd = [
        ffmpeg_exe,
        "-y",
        "-loop",
        "1",
        "-t",
        f"{d:.3f}",
        "-i",
        image_path,
        "-vf",
        vf,
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        out_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _coerce_clip_type(v) -> str:
    t = str(v or "video").lower().strip()
    return t


def _coerce_image_duration_seconds(value) -> float:
    try:
        return float(value)
    except Exception:
        raise ValueError("image.duration 必须是数字（秒）")


def _validate_image_duration_seconds(duration: float) -> float:
    # 前端建议限制 0.5–30，后端强校验兜底
    import math

    if not math.isfinite(duration):
        raise ValueError("image.duration must be a finite number")
    if duration < 0.5 or duration > 30:
        raise ValueError("image.duration 超出范围（0.5–30 秒）")
    return float(duration)


def _build_segments_from_request(data: dict) -> tuple[list, list, list, list, Optional[str]]:
    """
    Returns: (segment_paths, legacy_video_ids, normalized_clips, temp_files)
    """
    clips = data.get("clips")
    video_ids = data.get("video_ids") if clips is None else None

    normalized: list[dict] = []
    if clips is not None:
        if not isinstance(clips, list) or not clips:
            raise ValueError("clips 不能为空")
        if len(clips) > MAX_CLIPS:
            raise ValueError(f"clips 数量超出限制（{MAX_CLIPS}）")
        for i, c in enumerate(clips):
            if not isinstance(c, dict):
                raise ValueError(f"clips[{i}] 必须是对象")
            clip_type = _coerce_clip_type(c.get("type") or "video")
            if clip_type not in ("video", "image"):
                raise ValueError(f"Unsupported clip.type: {clip_type}")
            material_id = c.get("materialId")
            if material_id is None:
                raise ValueError(f"clips[{i}].materialId 不能为空")
            try:
                material_id = int(material_id)
            except Exception:
                raise ValueError(f"clips[{i}].materialId 必须是整数")

            item = {"type": clip_type, "materialId": material_id}
            if clip_type == "image":
                if "duration" not in c:
                    raise ValueError(f"clips[{i}].duration is required")
                try:
                    item["duration"] = _validate_image_duration_seconds(_coerce_image_duration_seconds(c.get("duration")))
                except Exception as e:
                    raise ValueError(f"clips[{i}].duration invalid: {e}")
                if item["duration"] <= 0:
                    raise ValueError(f"clips[{i}].duration 必须 > 0")
            normalized.append(item)
    else:
        if not isinstance(video_ids, list) or not video_ids:
            raise ValueError("video_ids 不能为空")
        if len(video_ids) > MAX_CLIPS:
            raise ValueError(f"video_ids 数量超出限制（{MAX_CLIPS}）")
        for i, vid in enumerate(video_ids):
            try:
                vid = int(vid)
            except Exception:
                raise ValueError(f"video_ids[{i}] 必须是整数")
            normalized.append({"type": "video", "materialId": vid})

    segment_paths: list[str] = []
    temp_files: list[str] = []
    legacy_video_ids: list[int] = []
    temp_dir: Optional[str] = None
    total_seconds = 0.0

    with get_db() as db:
        for c in normalized:
            mat = db.query(Material).filter(Material.id == c["materialId"]).first()
            if not mat:
                raise ValueError(f"素材ID {c['materialId']} 不存在")

            clip_type = c["type"]
            if clip_type == "video":
                if mat.type != "video":
                    raise ValueError(f"素材ID {c['materialId']} 类型错误，期望 video，实际 {mat.type}")
                abs_path = get_abs_path(mat.path)
                if not os.path.exists(abs_path):
                    raise ValueError(f"视频文件不存在：{mat.path}")
                duration = float(mat.duration or 0.0) if mat.duration is not None else 0.0
                if duration <= 0:
                    duration = _probe_duration_seconds(abs_path)
                if duration <= 0:
                    raise ValueError(f"无法确定素材时长：{mat.path}")
                total_seconds += duration
                segment_paths.append(abs_path)
                legacy_video_ids.append(int(c["materialId"]))
            elif clip_type == "image":
                if mat.type != "image":
                    raise ValueError(f"素材ID {c['materialId']} 类型错误，期望 image，实际 {mat.type}")
                abs_path = get_abs_path(mat.path)
                if not os.path.exists(abs_path):
                    raise ValueError(f"图片文件不存在：{mat.path}")
                if temp_dir is None:
                    temp_dir = os.path.join(SEGMENTS_DIR, f"task_{uuid.uuid4().hex}")
                    os.makedirs(temp_dir, exist_ok=True)
                out_path = os.path.join(temp_dir, f"img_{uuid.uuid4().hex}.mp4")
                total_seconds += float(c.get("duration") or 0.0)
                _make_image_segment(image_path=abs_path, duration=float(c["duration"]), out_path=out_path)
                segment_paths.append(out_path)
                temp_files.append(out_path)
            else:
                raise ValueError(f"不支持的 clip.type: {clip_type}")

    if total_seconds > MAX_TOTAL_SECONDS:
        raise ValueError(f"素材总时长超出限制（{MAX_TOTAL_SECONDS} 秒）")

    return segment_paths, legacy_video_ids, normalized, temp_files, temp_dir


def _repeat_last_image_segment_to_cover_voice(
    *,
    segment_paths: list[str],
    normalized_clips: list[dict],
    voice_path: Optional[str],
    speed: float,
) -> list[str]:
    """
    If voice exists and total duration is still short:
    - If clips contains image: repeat image segments in order (alternating) until long enough
    - Else: keep original (VideoEditor will loop videos as before)
    """
    if not voice_path or not os.path.exists(voice_path):
        return segment_paths

    voice_duration = _probe_duration_seconds(voice_path)
    if voice_duration <= 0:
        return segment_paths

    image_segments: list[str] = []
    for idx, c in enumerate(normalized_clips or []):
        if c.get("type") == "image" and idx < len(segment_paths):
            image_segments.append(segment_paths[idx])

    if not image_segments:
        return segment_paths

    try:
        speed_f = float(speed)
    except Exception:
        speed_f = 1.0
    if speed_f <= 0:
        speed_f = 1.0

    # Compare pre-speed durations to avoid drift: output_duration ~= total_pre_speed / speed_f
    total_pre_speed = 0.0
    for p in segment_paths:
        total_pre_speed += _probe_duration_seconds(p)

    need_pre_speed = voice_duration * speed_f
    if total_pre_speed + 1e-3 >= need_pre_speed:
        return segment_paths

    # Cycle through image segments in order until the total duration covers the voice
    out = list(segment_paths)
    guard = 0
    while total_pre_speed + 1e-3 < need_pre_speed:
        seg = image_segments[guard % len(image_segments)]
        d = _probe_duration_seconds(seg)
        if d <= 0:
            # If we can't probe, avoid infinite loop
            break
        out.append(seg)
        total_pre_speed += d
        guard += 1
        if guard > 2000:
            break

    return out


def _run_edit_task(
    task_id: int,
    video_paths: list,
    voice_path: Optional[str],
    bgm_path: Optional[str],
    speed: float,
    subtitle_path: Optional[str] = None,
    bgm_volume: float = 0.25,
    voice_volume: float = 1.0,
    output_name: Optional[str] = None,
    temp_files: Optional[list] = None,
    temp_dir: Optional[str] = None,
    is_mixed_clips: bool = False,
):
    """在后台线程中执行剪辑任务"""
    try:
        with get_db() as db:
            task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
            if not task:
                return
            
            # 更新任务状态为运行中
            task.status = "running"
            task.progress = 10
            task.error_message = None
            task.updated_at = datetime.datetime.now()
            db.commit()
        
        time.sleep(0.05)
        
        with get_db() as db:
            task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
            if task:
                task.progress = 25
                task.updated_at = datetime.datetime.now()
                db.commit()
        
        # 执行剪辑
        logger.info(f"Task {task_id}: Starting video edit with {len(video_paths)} videos")
        logger.info(f"Task {task_id}: voice_path={voice_path}, bgm_path={bgm_path}, speed={speed}, subtitle_path={subtitle_path}, bgm_volume={bgm_volume}, voice_volume={voice_volume}")
        
        output_path = None
        edit_error = None
        try:
            if is_mixed_clips:
                output_path = video_editor.edit_mixed_concat_filter(
                    video_paths,
                    voice_path,
                    bgm_path,
                    speed,
                    subtitle_path,
                    bgm_volume,
                    voice_volume,
                    output_name,
                )
            else:
                output_path = video_editor.edit(
                    video_paths,
                    voice_path,
                    bgm_path,
                    speed,
                    subtitle_path,
                    bgm_volume,
                    voice_volume,
                    output_name,
                )
        except Exception as edit_ex:
            edit_error = str(edit_ex)
            logger.exception(f"Task {task_id}: Video edit failed with exception")
        
        with get_db() as db:
            task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
            if not task:
                return
            
            task.progress = 90
            task.updated_at = datetime.datetime.now()
            
            if edit_error:
                # 剪辑过程中出现异常
                task.status = "fail"
                task.progress = 100
                task.error_message = f"剪辑失败：{edit_error}"
                logger.error(f"Task {task_id}: Edit failed with error: {edit_error}")
            elif output_path and os.path.exists(output_path):
                # 剪辑成功：上传到COS并保存到VideoLibrary
                output_filename = os.path.basename(output_path)
                relative_output_path = os.path.relpath(output_path, BASE_DIR).replace(os.sep, "/")
                uploads_rel = os.path.relpath(output_path, os.path.join(BASE_DIR, 'uploads')).replace(os.sep, '/')
                preview_url = f"/uploads/{uploads_rel}"
                
                # 上传到COS
                cos_url = None
                try:
                    if COS_AVAILABLE:
                        cos_key = generate_cos_key('video', output_filename)
                        upload_result = upload_file_to_cos(output_path, cos_key)
                        if upload_result['success']:
                            # 对于私有存储桶，生成预签名URL用于访问
                            from utils.cos_service import get_file_url
                            cos_url = get_file_url(cos_key, use_presigned=True, expires_in=86400 * 7)  # 7天有效期
                            logger.info(f"Task {task_id}: 视频已上传到COS: {upload_result['url']}")
                            logger.info(f"Task {task_id}: 预签名URL已生成（7天有效期）")
                        else:
                            logger.warning(f"Task {task_id}: 上传到COS失败: {upload_result['message']}")
                    else:
                        logger.warning(f"Task {task_id}: COS不可用，使用本地存储")
                except Exception as cos_error:
                    logger.exception(f"Task {task_id}: COS上传异常: {cos_error}")
                
                # 保存到VideoLibrary表
                video_library_id = None
                try:
                    video_name = output_filename.replace('.mp4', '').replace('output_', 'AI剪辑_')
                    video_library = VideoLibrary(
                        video_name=video_name,
                        video_url=cos_url or preview_url,  # 优先使用COS URL
                        video_size=os.path.getsize(output_path),
                        platform='output',  # 标记为成品
                        description=f'AI剪辑生成，任务ID: {task_id}'
                    )
                    db.add(video_library)
                    db.flush()
                    video_library_id = video_library.id
                    logger.info(f"Task {task_id}: 已保存到视频库，ID: {video_library_id}")
                except Exception as lib_error:
                    logger.exception(f"Task {task_id}: 保存到视频库失败: {lib_error}")
                
                # 更新任务状态
                task.status = "success"
                task.output_path = relative_output_path
                task.output_filename = output_filename
                task.preview_url = cos_url or preview_url  # 优先使用COS URL
                task.progress = 100
                task.error_message = None
                task.updated_at = datetime.datetime.now()
                
                logger.info(f"Task {task_id}: Edit succeeded, output: {output_path}")
                logger.info(f"Task {task_id}: output_filename={output_filename}, preview_url={task.preview_url}")
                logger.info(f"Task {task_id}: 文件大小={os.path.getsize(output_path)} 字节")
                logger.info(f"Task {task_id}: COS URL={cos_url}, VideoLibrary ID={video_library_id}")
                
                db.commit()
                logger.info(f"Task {task_id}: 任务状态已更新为 success，已提交到数据库")
            else:
                # 未生成输出文件
                task.status = "fail"
                task.progress = 100
                error_msg = "未生成输出文件"
                if output_path:
                    error_msg += f"（预期路径：{output_path}）"
                task.error_message = error_msg
                logger.error(f"Task {task_id}: No output file generated. Expected: {output_path}")
            
            task.updated_at = datetime.datetime.now()
            db.commit()
    except Exception as e:
        logger.exception(f"Task {task_id} failed")
        try:
            with get_db() as db:
                task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
                if task:
                    task.status = "fail"
                    task.progress = 100
                    task.error_message = str(e)
                    task.updated_at = datetime.datetime.now()
                    db.commit()
        except Exception as db_error:
            logger.exception(f"Failed to update task {task_id} status: {db_error}")
    finally:
        try:
            for p in (temp_files or []):
                try:
                    if p and os.path.isfile(p):
                        os.remove(p)
                except Exception:
                    pass
            if temp_dir and os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        with _TASK_LOCK:
            _TASK_THREADS.pop(task_id, None)


@editor_bp.route('/editor/edit', methods=['POST'])
@login_required
def edit_video():
    """
    同步视频剪辑接口
    
    请求方法: POST
    路径: /api/editor/edit
    认证: 需要登录
    
    请求体 (JSON):
        {
            "video_ids": [int],      # 必填，视频素材ID列表
            "voice_id": int,          # 可选，配音音频ID
            "bgm_id": int,            # 可选，BGM音频ID
            "speed": float,           # 可选，播放速度（0.5-2.0），默认 1.0
            "subtitle_path": "string" # 可选，字幕文件路径（相对路径）
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "剪辑成功",
            "data": {
                "task_id": int,
                "output_filename": "string",
                "preview_url": "string"
            }
        }
    """
    try:
        data = request.get_json() or {}
        clips = data.get("clips")
        video_ids = data.get("video_ids", [])
        voice_id = data.get("voice_id")
        bgm_id = data.get("bgm_id")
        speed = data.get("speed", 1.0)
        subtitle_path = (data.get("subtitle_path") or "").strip() or None

        _cleanup_old_segment_dirs()

        # 参数校验：clips 优先
        if clips is None:
            if not video_ids or not isinstance(video_ids, list) or len(video_ids) == 0:
                return response_error("视频ID列表不能为空", 400)
        
        try:
            speed = float(speed)
        except Exception:
            return response_error("播放速度必须是数字", 400)
        
        if speed < 0.5 or speed > 2.0:
            return response_error("播放速度超出范围（0.5~2.0）", 400)

        # 查询视频素材的绝对路径，并收集素材名称用于生成文件名
        try:
            segment_paths, _legacy_video_ids, normalized_clips, temp_files, temp_dir = _build_segments_from_request(data)
        except Exception as ex:
            return response_error(str(ex), 400)

        video_names = []
        voice_name = None
        bgm_name = None
        
        with get_db() as db:
            for c in normalized_clips:
                mid = int(c["materialId"])
                mat = db.query(Material).filter(Material.id == mid).first()
                if not mat:
                    continue
                video_name = os.path.splitext(mat.name or os.path.basename(mat.path))[0]
                video_names.append(video_name)

            # 查询配音素材的绝对路径（可选）
            voice_path = None
            if voice_id is not None:
                voice_mat = db.query(Material).filter(Material.id == voice_id).first()
                if not voice_mat or voice_mat.type != "audio":
                    return response_error(f"配音素材ID {voice_id} 不存在或类型错误", 400)
                voice_path = get_abs_path(voice_mat.path)
                if not os.path.exists(voice_path):
                    return response_error(f"配音文件不存在：{voice_mat.path}", 400)
                voice_name = os.path.splitext(voice_mat.name or os.path.basename(voice_mat.path))[0]
                if voice_name.startswith("配音_"):
                    voice_name = voice_name[2:]
                elif voice_name.startswith("TTS_"):
                    voice_name = voice_name[4:]

            bgm_path = None
            if bgm_id is not None:
                bgm_mat = db.query(Material).filter(Material.id == bgm_id).first()
                if not bgm_mat or bgm_mat.type != "audio":
                    return response_error(f"BGM素材ID {bgm_id} 不存在或类型错误", 400)
                bgm_path = get_abs_path(bgm_mat.path)
                if not os.path.exists(bgm_path):
                    return response_error(f"BGM文件不存在：{bgm_mat.path}", 400)
                bgm_name = os.path.splitext(bgm_mat.name or os.path.basename(bgm_mat.path))[0]

            abs_sub_path = None
            if subtitle_path:
                # 如果subtitle_path是URL（以/开头），转换为文件路径
                if subtitle_path.startswith('/'):
                    # 去掉前导斜杠，转换为相对路径
                    subtitle_path = subtitle_path.lstrip('/')
                abs_sub_path = get_abs_path(subtitle_path)
                try:
                    abs_sub_path = _ensure_within_dir(abs_sub_path, SUBTITLE_DIR)
                except Exception:
                    return response_error("字幕路径非法", 400)
                if not os.path.isfile(abs_sub_path):
                    return response_error(f"字幕文件不存在：{subtitle_path}（绝对路径：{abs_sub_path}）", 400)

            # 生成输出文件名：切片名称+配音名称+bgm名称+时间
            import re
            import datetime
            
            def sanitize_filename(s):
                """清理文件名，移除非法字符"""
                if not s:
                    return ""
                s = re.sub(r'[<>:"/\\|?*]', '', s)
                s = re.sub(r'\s+', '_', s)
                s = s.strip('._')
                return s[:30]
            
            name_parts = []
            if video_names:
                clips_name = "_".join([sanitize_filename(name) for name in video_names[:3]])
                if len(video_names) > 3:
                    clips_name += f"_等{len(video_names)}个"
                if clips_name:
                    name_parts.append(clips_name)
            
            if voice_name:
                voice_clean = sanitize_filename(voice_name)
                if voice_clean:
                    name_parts.append(voice_clean)
            
            if bgm_name:
                bgm_clean = sanitize_filename(bgm_name)
                if bgm_clean:
                    name_parts.append(bgm_clean)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if name_parts:
                output_name = "_".join(name_parts) + "_" + timestamp + ".mp4"
            else:
                output_name = None

            # 创建任务记录
            video_ids_str = json.dumps({"clips": normalized_clips}, ensure_ascii=False) if clips is not None else ",".join(map(str, video_ids))
            task = VideoEditTask(
                video_ids=video_ids_str,
                voice_id=voice_id,
                bgm_id=bgm_id,
                speed=speed,
                subtitle_path=subtitle_path,
                status="running",
                progress=0
            )
            db.add(task)
            db.flush()
            task_id = task.id
            db.commit()

        try:
            # 调用剪辑逻辑（使用默认音量：bgm_volume=0.25, voice_volume=1.0）
            # 注意：同步接口暂不支持自定义音量，使用默认值
            segment_paths = _repeat_last_image_segment_to_cover_voice(
                segment_paths=segment_paths,
                normalized_clips=normalized_clips,
                voice_path=voice_path,
                speed=speed,
            )
            output_path = video_editor.edit(segment_paths, voice_path, bgm_path, speed, abs_sub_path, 0.25, 1.0, output_name)

            with get_db() as db:
                task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
                if not task:
                    return response_error("任务不存在", 404)

                if output_path and os.path.exists(output_path):
                    # 剪辑成功：上传到COS并保存到VideoLibrary
                    output_filename = os.path.basename(output_path)
                    relative_output_path = os.path.relpath(output_path, BASE_DIR).replace(os.sep, "/")
                    uploads_rel = os.path.relpath(output_path, os.path.join(BASE_DIR, 'uploads')).replace(os.sep, '/')
                    preview_url = f"/uploads/{uploads_rel}"
                    
                    # 上传到COS
                    cos_url = None
                    try:
                        if COS_AVAILABLE:
                            cos_key = generate_cos_key('video', output_filename)
                            upload_result = upload_file_to_cos(output_path, cos_key)
                            if upload_result['success']:
                                cos_url = upload_result['url']
                                print(f"[Editor] 视频已上传到COS: {cos_url}")
                            else:
                                print(f"[Editor] 上传到COS失败: {upload_result['message']}")
                    except Exception as cos_error:
                        print(f"[Editor] COS上传异常: {cos_error}")
                        import traceback
                        traceback.print_exc()
                    
                    # 保存到VideoLibrary表
                    video_library_id = None
                    try:
                        video_name = output_filename.replace('.mp4', '').replace('output_', 'AI剪辑_')
                        video_library = VideoLibrary(
                            video_name=video_name,
                            video_url=cos_url or preview_url,  # 优先使用COS URL
                            video_size=os.path.getsize(output_path),
                            platform='output',  # 标记为成品
                            description=f'AI剪辑生成，任务ID: {task_id}'
                        )
                        db.add(video_library)
                        db.flush()
                        video_library_id = video_library.id
                        print(f"[Editor] 已保存到视频库，ID: {video_library_id}")
                    except Exception as lib_error:
                        print(f"[Editor] 保存到视频库失败: {lib_error}")
                        import traceback
                        traceback.print_exc()
                    
                    # 更新任务状态
                    task.status = "success"
                    task.output_path = relative_output_path
                    task.output_filename = output_filename
                    task.preview_url = cos_url or preview_url  # 优先使用COS URL
                    task.progress = 100
                    task.error_message = None
                    task.updated_at = datetime.datetime.now()
                    db.commit()
                    
                    return response_success({
                        "task_id": task_id,
                        "output_filename": output_filename,
                        "preview_url": cos_url or preview_url,
                        "cos_url": cos_url,
                        "video_library_id": video_library_id
                    }, "剪辑成功")
                else:
                    # 剪辑失败
                    task.status = "fail"
                    task.progress = 100
                    task.error_message = "未生成输出文件"
                    task.updated_at = datetime.datetime.now()
                    db.commit()
                    return response_error("剪辑失败，未生成输出文件", 500)

        except Exception as e:
            with get_db() as db:
                task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
                if task:
                    task.status = "fail"
                    task.progress = 100
                    task.error_message = str(e)
                    task.updated_at = datetime.datetime.now()
                    db.commit()
            return response_error(f"剪辑过程出错：{str(e)}", 500)
        finally:
            try:
                for p in (temp_files or []):
                    try:
                        if p and os.path.isfile(p):
                            os.remove(p)
                    except Exception:
                        pass
                if temp_dir and os.path.isdir(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    except Exception as e:
        logger.exception("Edit video failed")
        return response_error(f"剪辑失败：{str(e)}", 500)


@editor_bp.route('/editor/edit_async', methods=['POST'])
@login_required
def edit_video_async():
    """
    异步视频剪辑接口
    
    请求方法: POST
    路径: /api/editor/edit_async
    认证: 需要登录
    
    请求体 (JSON):
        {
            "video_ids": [int],      # 必填，视频素材ID列表
            "voice_id": int,          # 可选，配音音频ID
            "bgm_id": int,            # 可选，BGM音频ID
            "speed": float,           # 可选，播放速度（0.5-2.0），默认 1.0
            "subtitle_path": "string", # 可选，字幕文件路径（相对路径）
            "bgm_volume": float,      # 可选，BGM音量（0.0-1.0），默认 0.25
            "voice_volume": float     # 可选，配音音量（0.0-1.0），默认 1.0
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "任务已创建",
            "data": {
                "task_id": int
            }
        }
    """
    try:
        data = request.get_json() or {}
        clips = data.get("clips")
        video_ids = data.get("video_ids", [])
        voice_id = data.get("voice_id")
        bgm_id = data.get("bgm_id")
        speed = data.get("speed", 1.0)
        subtitle_path = (data.get("subtitle_path") or "").strip() or None
        try:
            bgm_volume = float(data.get("bgm_volume", 0.25))
        except Exception:
            bgm_volume = 0.25
        try:
            voice_volume = float(data.get("voice_volume", 1.0))
        except Exception:
            voice_volume = 1.0

        _cleanup_old_segment_dirs()

        with _TASK_LOCK:
            if len(_TASK_THREADS) >= MAX_CONCURRENT_EDIT_THREADS:
                return response_error("并发剪辑任务过多，请稍后再试", 429)

        # Clamp volumes to a safe range
        bgm_volume = max(0.0, min(1.0, bgm_volume))
        voice_volume = max(0.0, min(1.0, voice_volume))

        if clips is None:
            if not video_ids or not isinstance(video_ids, list) or len(video_ids) == 0:
                return response_error("视频ID列表不能为空", 400)
            if len(video_ids) > MAX_CLIPS:
                return response_error(f"video_ids 数量超出限制（{MAX_CLIPS}）", 400)
        
        try:
            speed = float(speed)
        except Exception:
            return response_error("播放速度必须是数字", 400)
        
        if speed < 0.5 or speed > 2.0:
            return response_error("播放速度超出范围（0.5~2.0）", 400)

        # 查询视频素材的绝对路径，并收集素材名称用于生成文件名
        # 新协议：clips 优先（支持 video/image 混排）
        if clips is not None:
            try:
                segment_paths, legacy_video_ids, normalized_clips, temp_files, temp_dir = _build_segments_from_request(data)
            except Exception as ex:
                return response_error(str(ex), 400)

            video_names = []
            voice_name = None
            bgm_name = None

            with get_db() as db:
                for c in normalized_clips:
                    mid = int(c["materialId"])
                    mat = db.query(Material).filter(Material.id == mid).first()
                    if not mat:
                        continue
                    clip_name = os.path.splitext(mat.name or os.path.basename(mat.path))[0]
                    video_names.append(clip_name)

                bgm_path = None
                voice_path = None

                if voice_id is not None:
                    voice_mat = db.query(Material).filter(Material.id == voice_id).first()
                    if not voice_mat or voice_mat.type != "audio":
                        return response_error(f"配音素材ID {voice_id} 不存在或类型错误", 400)
                    voice_path = get_abs_path(voice_mat.path)
                    if not os.path.exists(voice_path):
                        return response_error(f"配音文件不存在：{voice_mat.path}", 400)
                    voice_name = os.path.splitext(voice_mat.name or os.path.basename(voice_mat.path))[0]

                if bgm_id is not None:
                    bgm_mat = db.query(Material).filter(Material.id == bgm_id).first()
                    if not bgm_mat or bgm_mat.type != "audio":
                        return response_error(f"BGM素材ID {bgm_id} 不存在或类型错误", 400)
                    bgm_path = get_abs_path(bgm_mat.path)
                    if not os.path.exists(bgm_path):
                        return response_error(f"BGM文件不存在：{bgm_mat.path}", 400)
                    bgm_name = os.path.splitext(bgm_mat.name or os.path.basename(bgm_mat.path))[0]

                abs_sub_path = None
                if subtitle_path:
                    if subtitle_path.startswith('/'):
                        subtitle_path = subtitle_path.lstrip('/')
                    abs_sub_path = get_abs_path(subtitle_path)
                    try:
                        abs_sub_path = _ensure_within_dir(abs_sub_path, SUBTITLE_DIR)
                    except Exception:
                        return response_error("字幕路径非法", 400)
                    if not os.path.isfile(abs_sub_path):
                        return response_error(f"字幕文件不存在：{subtitle_path}", 400)

                import re
                import datetime

                def sanitize_filename(s):
                    if not s:
                        return ""
                    s = re.sub(r'[<>:\"/\\\\|?*]', '', s)
                    s = re.sub(r'\\s+', '_', s)
                    s = s.strip('._')
                    return s[:30]

                name_parts = []
                if video_names:
                    clips_name = "_".join([sanitize_filename(name) for name in video_names[:3]])
                    if len(video_names) > 3:
                        clips_name += f"_等{len(video_names)}个"
                    if clips_name:
                        name_parts.append(clips_name)

                if voice_name:
                    vc = sanitize_filename(voice_name)
                    if vc:
                        name_parts.append(vc)

                if bgm_name:
                    bc = sanitize_filename(bgm_name)
                    if bc:
                        name_parts.append(bc)

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_name = "_".join(name_parts) + "_" + timestamp + ".mp4" if name_parts else None

                video_ids_str = json.dumps({"clips": normalized_clips}, ensure_ascii=False)
                task = VideoEditTask(
                    video_ids=video_ids_str,
                    voice_id=voice_id,
                    bgm_id=bgm_id,
                    speed=speed,
                    subtitle_path=subtitle_path,
                    status="pending",
                    progress=0,
                    error_message=None,
                )
                db.add(task)
                db.flush()
                task_id = task.id
                db.commit()

            segment_paths = _repeat_last_image_segment_to_cover_voice(
                segment_paths=segment_paths,
                normalized_clips=normalized_clips,
                voice_path=voice_path,
                speed=speed,
            )

            t = threading.Thread(
                target=_run_edit_task,
                args=(
                    task_id,
                    segment_paths,
                    voice_path,
                    bgm_path,
                    speed,
                    abs_sub_path,
                    bgm_volume,
                    voice_volume,
                    output_name,
                    temp_files,
                    temp_dir,
                    (any(c.get("type") == "image" for c in normalized_clips) and any(c.get("type") == "video" for c in normalized_clips)),
                ),
                daemon=True,
            )
            with _TASK_LOCK:
                _TASK_THREADS[task_id] = t
            t.start()

            return response_success({"task_id": task_id}, "任务已创建")

        video_paths = []
        video_names = []  # 用于生成文件名
        voice_name = None
        bgm_name = None
        total_seconds = 0.0
        
        with get_db() as db:
            for vid in video_ids:
                mat = db.query(Material).filter(Material.id == vid).first()
                if not mat or mat.type != "video":
                    return response_error(f"视频素材ID {vid} 不存在或类型错误", 400)
                abs_path = get_abs_path(mat.path)
                if not os.path.exists(abs_path):
                    return response_error(f"视频文件不存在：{mat.path}", 400)
                duration = float(mat.duration or 0.0) if mat.duration is not None else 0.0
                if duration <= 0:
                    duration = _probe_duration_seconds(abs_path)
                if duration <= 0:
                    return response_error(f"无法确定素材时长：{mat.path}", 400)
                total_seconds += duration
                video_paths.append(abs_path)
                # 收集视频名称（去掉扩展名）
                video_name = os.path.splitext(mat.name or os.path.basename(mat.path))[0]
                video_names.append(video_name)

            bgm_path = None
            voice_path = None
            
            if voice_id is not None:
                logger.info(f"查找配音素材，voice_id={voice_id}")
                voice_mat = db.query(Material).filter(Material.id == voice_id).first()
                if not voice_mat:
                    logger.error(f"配音素材ID {voice_id} 不存在")
                    return response_error(f"配音素材ID {voice_id} 不存在或类型错误", 400)
                if voice_mat.type != "audio":
                    logger.error(f"配音素材ID {voice_id} 类型错误，期望 audio，实际 {voice_mat.type}")
                    return response_error(f"配音素材ID {voice_id} 不存在或类型错误", 400)
                voice_path = get_abs_path(voice_mat.path)
                logger.info(f"配音文件路径：相对路径={voice_mat.path}，绝对路径={voice_path}")
                if not os.path.exists(voice_path):
                    logger.error(f"配音文件不存在：{voice_path}")
                    return response_error(f"配音文件不存在：{voice_mat.path}", 400)
                logger.info(f"配音文件验证成功：{voice_path}")
                # 获取配音名称（去掉扩展名和前缀）
                voice_name = voice_mat.name or os.path.basename(voice_mat.path)
                voice_name = os.path.splitext(voice_name)[0]
                # 去掉可能的"配音_"或"TTS_"前缀
                if voice_name.startswith("配音_"):
                    voice_name = voice_name[2:]
                elif voice_name.startswith("TTS_"):
                    voice_name = voice_name[4:]

            if bgm_id is not None:
                bgm_mat = db.query(Material).filter(Material.id == bgm_id).first()
                if not bgm_mat or bgm_mat.type != "audio":
                    return response_error(f"BGM素材ID {bgm_id} 不存在或类型错误", 400)
                bgm_path = get_abs_path(bgm_mat.path)
                if not os.path.exists(bgm_path):
                    return response_error(f"BGM文件不存在：{bgm_mat.path}", 400)
                # 获取BGM名称（去掉扩展名）
                bgm_name = os.path.splitext(bgm_mat.name or os.path.basename(bgm_mat.path))[0]

            abs_sub_path = None
            if subtitle_path:
                logger.info(f"处理字幕路径，原始路径={subtitle_path}")
                # 如果subtitle_path是URL（以/开头），转换为文件路径
                if subtitle_path.startswith('/'):
                    # 去掉前导斜杠，转换为相对路径
                    subtitle_path = subtitle_path.lstrip('/')
                    logger.info(f"去掉前导斜杠后，路径={subtitle_path}")
                abs_sub_path = get_abs_path(subtitle_path)
                try:
                    abs_sub_path = _ensure_within_dir(abs_sub_path, SUBTITLE_DIR)
                except Exception:
                    return response_error("字幕路径非法", 400)
                logger.info(f"字幕文件路径：相对路径={subtitle_path}，绝对路径={abs_sub_path}")
                if not os.path.isfile(abs_sub_path):
                    logger.error(f"字幕文件不存在：绝对路径={abs_sub_path}")
                    return response_error(f"字幕文件不存在：{subtitle_path}（绝对路径：{abs_sub_path}）", 400)
                logger.info(f"字幕文件验证成功：{abs_sub_path}")
            else:
                logger.info("未提供字幕路径")

            if total_seconds > MAX_TOTAL_SECONDS:
                return response_error(f"素材总时长超出限制（{MAX_TOTAL_SECONDS} 秒）", 400)

            # 生成输出文件名：切片名称+配音名称+bgm名称+时间
            import re
            import datetime
            
            def sanitize_filename(s):
                """清理文件名，移除非法字符"""
                if not s:
                    return ""
                # 移除或替换非法字符
                s = re.sub(r'[<>:"/\\|?*]', '', s)  # 移除Windows非法字符
                s = re.sub(r'\s+', '_', s)  # 空格替换为下划线
                s = s.strip('._')  # 移除首尾的点和下划线
                return s[:30]  # 限制每个部分的长度
            
            name_parts = []
            # 添加切片名称（如果有多个，用短横线连接）
            if video_names:
                clips_name = "_".join([sanitize_filename(name) for name in video_names[:3]])  # 最多取前3个
                if len(video_names) > 3:
                    clips_name += f"_等{len(video_names)}个"
                if clips_name:
                    name_parts.append(clips_name)
            
            # 添加配音名称
            if voice_name:
                voice_clean = sanitize_filename(voice_name)
                if voice_clean:
                    name_parts.append(voice_clean)
            
            # 添加BGM名称
            if bgm_name:
                bgm_clean = sanitize_filename(bgm_name)
                if bgm_clean:
                    name_parts.append(bgm_clean)
            
            # 添加时间戳
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if name_parts:
                output_name = "_".join(name_parts) + "_" + timestamp + ".mp4"
            else:
                # 如果没有素材名称，使用默认命名
                output_name = None
            
            logger.info(f"生成的输出文件名: {output_name}")

            # 创建任务记录
            video_ids_str = ",".join(map(str, video_ids))
            task = VideoEditTask(
                video_ids=video_ids_str,
                voice_id=voice_id,
                bgm_id=bgm_id,
                speed=speed,
                subtitle_path=subtitle_path,
                status="pending",
                progress=0,
                error_message=None
            )
            db.add(task)
            db.flush()
            task_id = task.id
            db.commit()

        # 启动后台任务
        t = threading.Thread(
            target=_run_edit_task,
            args=(task_id, video_paths, voice_path, bgm_path, speed, abs_sub_path, bgm_volume, voice_volume, output_name, None, None),
            daemon=True
        )
        with _TASK_LOCK:
            _TASK_THREADS[task_id] = t
        t.start()

        return response_success({
            "task_id": task_id
        }, "任务已创建")

    except Exception as e:
        logger.exception("Create async edit task failed")
        return response_error(f"创建任务失败：{str(e)}", 500)


@editor_bp.route('/tasks', methods=['GET'])
@login_required
def list_tasks():
    """
    获取任务列表接口
    
    请求方法: GET
    路径: /api/tasks
    认证: 需要登录
    
    查询参数:
        status (string, 可选): 任务状态筛选（pending/running/success/fail）
        limit (int, 可选): 每页数量，默认 50
        offset (int, 可选): 偏移量，默认 0
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "获取任务列表成功",
            "data": [
                {
                    "id": int,
                    "video_ids": "string",
                    "voice_id": int,
                    "bgm_id": int,
                    "speed": float,
                    "status": "string",
                    "progress": int,
                    "output_filename": "string",
                    "preview_url": "string",
                    "error_message": "string",
                    "create_time": "string",
                    "update_time": "string"
                }
            ]
        }
    """
    try:
        status = request.args.get("status")
        limit = int(request.args.get("limit", "50"))
        offset = int(request.args.get("offset", "0"))
        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        with get_db() as db:
            query = db.query(VideoEditTask)
            
            if status:
                query = query.filter(VideoEditTask.status == status)
            
            total = query.count()
            tasks = query.order_by(VideoEditTask.created_at.desc()).limit(limit).offset(offset).all()
            
            tasks_list = []
            for task in tasks:
                tasks_list.append({
                    'id': task.id,
                    'video_ids': task.video_ids,
                    'voice_id': task.voice_id,
                    'bgm_id': task.bgm_id,
                    'speed': task.speed,
                    'subtitle_path': task.subtitle_path,
                    'status': task.status,
                    'progress': task.progress,
                    'output_path': task.output_path,
                    'output_filename': task.output_filename,
                    'preview_url': task.preview_url,
                    'error_message': task.error_message,
                    'create_time': task.created_at.isoformat() if task.created_at else None,
                    'update_time': task.updated_at.isoformat() if task.updated_at else None
                })

        return response_success(tasks_list, "获取任务列表成功")
    
    except Exception as e:
        logger.exception("List tasks failed")
        return response_error(f"获取任务列表失败：{str(e)}", 500)


@editor_bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id: int):
    """
    获取任务详情接口
    
    请求方法: GET
    路径: /api/tasks/{task_id}
    认证: 需要登录
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "获取任务成功",
            "data": {
                "id": int,
                "video_ids": "string",
                "voice_id": int,
                "bgm_id": int,
                "speed": float,
                "status": "string",
                "progress": int,
                "output_filename": "string",
                "preview_url": "string",
                "error_message": "string",
                "create_time": "string",
                "update_time": "string"
            }
        }
    """
    try:
        with get_db() as db:
            task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
            
            if not task:
                return response_error("任务不存在", 404)
            
            return response_success({
                'id': task.id,
                'video_ids': task.video_ids,
                'voice_id': task.voice_id,
                'bgm_id': task.bgm_id,
                'speed': task.speed,
                'subtitle_path': task.subtitle_path,
                'status': task.status,
                'progress': task.progress,
                'output_path': task.output_path,
                'output_filename': task.output_filename,
                'preview_url': task.preview_url,
                'error_message': task.error_message,
                'create_time': task.created_at.isoformat() if task.created_at else None,
                'update_time': task.updated_at.isoformat() if task.updated_at else None
            }, "获取任务成功")
    
    except Exception as e:
        logger.exception("Get task failed")
        return response_error(f"获取任务失败：{str(e)}", 500)


@editor_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id: int):
    """
    删除任务接口
    
    请求方法: POST
    路径: /api/tasks/{task_id}/delete
    认证: 需要登录
    
    请求体 (JSON, 可选):
        {
            "delete_output": false  # 可选，是否同时删除输出文件
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "删除任务成功",
            "data": null
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        delete_output_file = data.get("delete_output", False) is True

        with get_db() as db:
            task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
            
            if not task:
                return response_error("任务不存在", 404)

            if delete_output_file:
                filename = task.output_filename
                if filename:
                    abs_path = os.path.normpath(os.path.join(OUTPUT_VIDEO_DIR, filename))
                    try:
                        if os.path.isfile(abs_path):
                            os.remove(abs_path)
                    except Exception as e:
                        return response_error(f"删除成品文件失败：{e}", 500)

            db.delete(task)
            db.commit()

            return response_success(None, "删除任务成功")
    
    except Exception as e:
        logger.exception("Delete task failed")
        return response_error(f"删除任务失败：{str(e)}", 500)


@editor_bp.route('/outputs', methods=['GET'])
@login_required
def list_outputs():
    """
    获取成品列表接口（直接从COS获取视频列表）
    
    请求方法: GET
    路径: /api/outputs
    认证: 需要登录
    
    查询参数:
        source (string, 可选): 数据源，'cos' 表示从COS获取，'db' 表示从数据库获取，默认 'cos'
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "获取成品列表成功",
            "data": [
                {
                    "id": int,  # 如果是数据库记录则为VideoLibrary ID，否则为索引
                    "filename": "string",
                    "video_name": "string",
                    "size": int,
                    "update_time": "string",
                    "preview_url": "string",  # COS URL
                    "video_url": "string",  # COS URL
                    "download_url": "string",
                    "task_id": int  # 如果有关联任务
                }
            ]
        }
    """
    try:
        source = request.args.get("source", "cos")  # 默认从COS获取
        
        if source == "cos":
            # 直接从COS获取视频列表
            logger.info("从COS获取成品视频列表")
            try:
                cos_result = list_objects_from_cos(prefix='video/', max_keys=1000)
                
                if not cos_result['success']:
                    logger.warning(f"从COS获取视频列表失败: {cos_result['message']}")
                    # 如果COS获取失败（可能是权限问题），自动回退到数据库
                    logger.info("自动回退到数据库获取成品列表")
                    return _list_outputs_from_db()
            except Exception as cos_ex:
                logger.exception(f"从COS获取视频列表时发生异常: {cos_ex}")
                # 发生异常时，自动回退到数据库
                logger.info("发生异常，自动回退到数据库获取成品列表")
                return _list_outputs_from_db()
            
            items = []
            for idx, obj in enumerate(cos_result['objects']):
                # 从COS key中提取文件名
                filename = obj['filename']
                # 从文件名生成视频名称（去掉扩展名，替换output_为AI剪辑_）
                video_name = filename.replace('.mp4', '').replace('output_', 'AI剪辑_')
                
                # 解析任务ID（如果description中有）
                task_id = None
                # 可以从文件名或路径中尝试解析任务ID，这里暂时留空
                
                items.append({
                    "id": idx + 1,  # 使用索引作为ID
                    "filename": filename,
                    "video_name": video_name,
                    "size": obj['size'],
                    "update_time": obj['last_modified'] if obj['last_modified'] else "",
                    "preview_url": obj['url'],
                    "video_url": obj['url'],
                    "download_url": obj['url'],
                    "task_id": task_id,
                    "cos_key": obj['key']  # 添加COS key，便于后续操作
                })
            
            # 按更新时间排序（最新的在前）
            try:
                items.sort(key=lambda x: x.get("update_time") or "", reverse=True)
            except Exception as sort_error:
                logger.warning(f"排序时出错：{sort_error}")
            
            logger.info(f"从COS获取到 {len(items)} 个成品视频")
            return response_success(items, "获取成品列表成功")
        else:
            # 从数据库获取
            return _list_outputs_from_db()
    
    except Exception as e:
        logger.exception("List outputs failed")
        return response_error(f"获取成品列表失败：{str(e)}", 500)


def _list_outputs_from_db():
    """从数据库获取成品列表（备用方案）"""
    try:
        items = []
        
        # 从VideoLibrary表读取成品（platform='output'）
        with get_db() as db:
            videos = db.query(VideoLibrary).filter(
                VideoLibrary.platform == 'output'
            ).order_by(VideoLibrary.created_at.desc()).limit(200).all()
            
            logger.info(f"从视频库查询到 {len(videos)} 个成品视频")
            
            for video in videos:
                try:
                    # 从video_url中提取文件名
                    video_url = video.video_url or ''
                    filename = os.path.basename(video_url) if video_url else video.video_name
                    
                    # 处理时间格式
                    update_time_str = ""
                    if video.created_at:
                        if isinstance(video.created_at, datetime.datetime):
                            update_time_str = video.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            update_time_str = str(video.created_at)
                    
                    # 从description中解析任务ID
                    task_id = None
                    if video.description:
                        import re
                        match = re.search(r'任务ID:\s*(\d+)', video.description)
                        if match:
                            task_id = int(match.group(1))
                    
                    items.append({
                        "id": video.id,
                        "filename": filename,
                        "video_name": video.video_name,
                        "size": video.video_size or 0,
                        "update_time": update_time_str,
                        "preview_url": video.video_url or '',
                        "video_url": video.video_url or '',
                        "download_url": video.video_url or f"/api/download/video/{filename}",
                        "task_id": task_id
                    })
                except Exception as e:
                    logger.warning(f"处理视频库记录 {video.id} 时出错：{e}")
                    continue
        
        # 按更新时间排序
        try:
            items.sort(key=lambda x: x.get("update_time") or "", reverse=True)
        except Exception as sort_error:
            logger.warning(f"排序时出错：{sort_error}")
        
        return response_success(items, "获取成品列表成功")
    
    except Exception as e:
        logger.exception("List outputs from DB failed")
        return response_error(f"从数据库获取成品列表失败：{str(e)}", 500)


@editor_bp.route('/output/delete', methods=['POST'])
@login_required
def delete_output():
    """
    删除成品视频接口（同时删除COS和本地文件）
    
    请求方法: POST
    路径: /api/output/delete
    认证: 需要登录
    
    请求体 (JSON):
        {
            "filename": "string"  # 必填，文件名
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "删除成功",
            "data": null
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        filename = (data.get("filename") or "").strip()
        cos_key = data.get("cos_key")  # 如果前端传递了COS key，直接使用
        
        if not filename:
            return response_error("文件名不能为空", 400)
        
        # 如果文件名包含路径分隔符，可能是COS key，需要特殊处理
        # 但为了安全，仍然需要验证路径
        if ".." in filename:
            return response_error("非法文件名", 400)

        # 1. 从VideoLibrary表中查找对应的记录（通过文件名匹配video_url）
        video_record_id = None
        video_url = None
        thumbnail_url = None
        with get_db() as db:
            # 查找platform='output'且video_url包含该文件名的记录
            videos = db.query(VideoLibrary).filter(
                VideoLibrary.platform == 'output'
            ).all()
            
            logger.info(f"查找删除记录，文件名: {filename}, 数据库记录数: {len(videos)}")
            
            for video in videos:
                v_url = video.video_url or ''
                # 从URL中提取文件名（处理各种URL格式）
                url_filename = None
                if v_url:
                    # 移除查询参数（预签名URL可能包含?）
                    clean_url = v_url.split('?')[0]
                    # 提取文件名
                    url_filename = os.path.basename(clean_url)
                    # 如果URL包含路径，也尝试从路径中提取
                    if '/' in clean_url:
                        url_filename = clean_url.split('/')[-1]
                
                # 检查文件名是否匹配（支持多种匹配方式）
                is_match = False
                if filename == url_filename:
                    is_match = True
                elif filename in v_url:
                    # 文件名在URL中（可能是完整路径）
                    is_match = True
                elif url_filename and filename in url_filename:
                    # 文件名是URL文件名的一部分
                    is_match = True
                
                if is_match:
                    video_record_id = video.id
                    video_url = v_url  # 在session内获取属性值
                    thumbnail_url = video.thumbnail_url  # 在session内获取属性值
                    logger.info(f"找到匹配记录: video_id={video_record_id}, video_url={video_url}")
                    break
            
            if not video_record_id:
                logger.warning(f"未找到匹配的数据库记录，文件名: {filename}")
        
        # 2. 删除COS中的文件（优先使用前端传递的cos_key，否则从数据库记录中获取）
        cos_key_to_delete = None
        if cos_key:
            # 如果前端传递了cos_key，直接使用
            cos_key_to_delete = cos_key
            logger.info(f"使用前端传递的COS key: {cos_key_to_delete}")
        elif video_record_id and video_url and COS_AVAILABLE:
            try:
                from config import COS_DOMAIN, COS_SCHEME, COS_BUCKET, COS_REGION
                from utils.cos_service import delete_file_from_cos
                
                # 从video_url中提取COS key
                if video_url and ('cos.' in video_url or (COS_DOMAIN and COS_DOMAIN in video_url)):
                    # 从URL中提取COS键
                    if COS_DOMAIN and COS_DOMAIN in video_url:
                        cos_key_to_delete = video_url.replace(COS_DOMAIN.rstrip('/') + '/', '').lstrip('/')
                    else:
                        prefix = f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/"
                        if video_url.startswith(prefix):
                            cos_key_to_delete = video_url.replace(prefix, '').lstrip('/')
                        else:
                            cos_key_to_delete = None
                
                # 如果缩略图URL是COS URL，也尝试删除
                if thumbnail_url and ('cos.' in thumbnail_url or (COS_DOMAIN and COS_DOMAIN in thumbnail_url)):
                    if COS_DOMAIN and COS_DOMAIN in thumbnail_url:
                        thumbnail_cos_key = thumbnail_url.replace(COS_DOMAIN.rstrip('/') + '/', '').lstrip('/')
                    else:
                        prefix = f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/"
                        if thumbnail_url.startswith(prefix):
                            thumbnail_cos_key = thumbnail_url.replace(prefix, '').lstrip('/')
                        else:
                            thumbnail_cos_key = None
                    
                    if thumbnail_cos_key:
                        delete_file_from_cos(thumbnail_cos_key)
            except Exception as e:
                logger.warning(f"从数据库记录提取COS key时出错: {e}")
        
        # 删除COS文件
        if cos_key_to_delete and COS_AVAILABLE:
            try:
                from utils.cos_service import delete_file_from_cos
                delete_result = delete_file_from_cos(cos_key_to_delete)
                if delete_result['success']:
                    logger.info(f"已删除COS文件: {cos_key_to_delete}")
                else:
                    logger.warning(f"删除COS文件失败: {delete_result['message']}")
            except Exception as e:
                logger.warning(f"删除COS文件时出错: {e}")
                # 继续删除本地文件和数据库记录
        
        # 3. 删除本地文件
        abs_path = os.path.normpath(os.path.join(OUTPUT_VIDEO_DIR, filename))
        
        try:
            if os.path.commonpath([os.path.normcase(abs_path), os.path.normcase(OUTPUT_VIDEO_DIR)]) != os.path.normcase(OUTPUT_VIDEO_DIR):
                return response_error("非法路径", 400)
        except Exception:
            return response_error("非法路径", 400)

        try:
            if os.path.isfile(abs_path):
                os.remove(abs_path)
                logger.info(f"已删除本地文件: {abs_path}")
        except Exception as e:
            logger.warning(f"删除本地文件失败: {e}")
            # 如果本地文件不存在，不报错（可能只存在COS中）
        
        # 4. 删除数据库记录
        if video_record_id:
            try:
                with get_db() as db:
                    video_record = db.query(VideoLibrary).filter(VideoLibrary.id == video_record_id).first()
                    if video_record:
                        db.delete(video_record)
                        db.commit()
                        logger.info(f"已删除数据库记录: video_id={video_record_id}")
                    else:
                        logger.warning(f"数据库记录不存在: video_id={video_record_id}")
            except Exception as e:
                logger.warning(f"删除数据库记录失败: {e}")
        else:
            logger.warning(f"未找到数据库记录，仅删除本地文件: {filename}")
        
        
        return response_success(None, "删除成功")

    except Exception as e:
        logger.exception("Delete output failed")
        return response_error(f"删除失败：{str(e)}", 500)


@editor_bp.route('/download/video/<filename>', methods=['GET'])
@login_required
def download_video(filename):
    """
    下载视频接口
    
    请求方法: GET
    路径: /api/download/video/{filename}
    认证: 需要登录
    
    返回: 视频文件（作为附件下载）
    """
    try:
        # 校验文件是否存在
        output_path = os.path.normpath(os.path.join(OUTPUT_VIDEO_DIR, filename))
        try:
            output_path = _ensure_within_dir(output_path, OUTPUT_VIDEO_DIR)
        except Exception:
            return response_error("非法路径", 400)
        if not os.path.exists(output_path):
            return response_error("视频文件不存在", 404)

        # 通过send_from_directory返回文件
        return send_from_directory(OUTPUT_VIDEO_DIR, filename, as_attachment=True)
    
    except Exception as e:
        logger.exception("Download video failed")
        return response_error(f"下载失败：{str(e)}", 500)

