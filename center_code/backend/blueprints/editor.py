"""
视频剪辑 API（同步/异步剪辑、任务管理、成品管理）
"""
import os
import sys
import threading
import time
import datetime
import logging

from flask import Blueprint, request, send_from_directory

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Material, VideoEditTask
from db import get_db
from utils.video_editor import video_editor, get_abs_path

logger = logging.getLogger(__name__)

editor_bp = Blueprint('editor', __name__, url_prefix='/api')

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_VIDEO_DIR = os.path.join(BASE_DIR, 'uploads', 'videos')

# 自动创建目录
if not os.path.exists(OUTPUT_VIDEO_DIR):
    os.makedirs(OUTPUT_VIDEO_DIR)

# 异步任务管理
_TASK_THREADS = {}
_TASK_LOCK = threading.Lock()


def _run_edit_task(
    task_id: int,
    video_paths: list,
    voice_path: str | None,
    bgm_path: str | None,
    speed: float,
    subtitle_path: str | None = None,
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
        output_path = video_editor.edit(video_paths, voice_path, bgm_path, speed, subtitle_path)
        
        with get_db() as db:
            task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
            if not task:
                return
            
            task.progress = 90
            task.updated_at = datetime.datetime.now()
            
            if output_path and os.path.exists(output_path):
                output_filename = os.path.basename(output_path)
                relative_output_path = os.path.relpath(output_path, BASE_DIR).replace(os.sep, "/")
                uploads_rel = os.path.relpath(output_path, os.path.join(BASE_DIR, 'uploads')).replace(os.sep, '/')
                preview_url = f"/uploads/{uploads_rel}"
                
                task.status = "success"
                task.output_path = relative_output_path
                task.output_filename = output_filename
                task.preview_url = preview_url
                task.progress = 100
                task.error_message = None
            else:
                task.status = "fail"
                task.progress = 100
                task.error_message = "未生成输出文件"
            
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
        video_ids = data.get("video_ids", [])
        voice_id = data.get("voice_id")
        bgm_id = data.get("bgm_id")
        speed = data.get("speed", 1.0)
        subtitle_path = (data.get("subtitle_path") or "").strip() or None

        # 参数校验
        if not video_ids or not isinstance(video_ids, list) or len(video_ids) == 0:
            return response_error("视频ID列表不能为空", 400)
        
        try:
            speed = float(speed)
        except Exception:
            return response_error("播放速度必须是数字", 400)
        
        if speed < 0.5 or speed > 2.0:
            return response_error("播放速度超出范围（0.5~2.0）", 400)

        # 查询视频素材的绝对路径
        video_paths = []
        with get_db() as db:
            for vid in video_ids:
                mat = db.query(Material).filter(Material.id == vid).first()
                if not mat or mat.type != "video":
                    return response_error(f"视频素材ID {vid} 不存在或类型错误", 400)
                abs_path = get_abs_path(mat.path)
                if not os.path.exists(abs_path):
                    return response_error(f"视频文件不存在：{mat.path}", 400)
                video_paths.append(abs_path)

            # 查询配音素材的绝对路径（可选）
            voice_path = None
            if voice_id is not None:
                voice_mat = db.query(Material).filter(Material.id == voice_id).first()
                if not voice_mat or voice_mat.type != "audio":
                    return response_error(f"配音素材ID {voice_id} 不存在或类型错误", 400)
                voice_path = get_abs_path(voice_mat.path)
                if not os.path.exists(voice_path):
                    return response_error(f"配音文件不存在：{voice_mat.path}", 400)

            bgm_path = None
            if bgm_id is not None:
                bgm_mat = db.query(Material).filter(Material.id == bgm_id).first()
                if not bgm_mat or bgm_mat.type != "audio":
                    return response_error(f"BGM素材ID {bgm_id} 不存在或类型错误", 400)
                bgm_path = get_abs_path(bgm_mat.path)
                if not os.path.exists(bgm_path):
                    return response_error(f"BGM文件不存在：{bgm_mat.path}", 400)

            abs_sub_path = None
            if subtitle_path:
                abs_sub_path = get_abs_path(subtitle_path)
                if not os.path.isfile(abs_sub_path):
                    return response_error(f"字幕文件不存在：{subtitle_path}", 400)

            # 创建任务记录
            video_ids_str = ",".join(map(str, video_ids))
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
            # 调用剪辑逻辑
            output_path = video_editor.edit(video_paths, voice_path, bgm_path, speed, abs_sub_path)

            with get_db() as db:
                task = db.query(VideoEditTask).filter(VideoEditTask.id == task_id).first()
                if not task:
                    return response_error("任务不存在", 404)

                if output_path and os.path.exists(output_path):
                    # 剪辑成功：更新任务状态和输出路径
                    output_filename = os.path.basename(output_path)
                    relative_output_path = os.path.relpath(output_path, BASE_DIR).replace(os.sep, "/")
                    uploads_rel = os.path.relpath(output_path, os.path.join(BASE_DIR, 'uploads')).replace(os.sep, '/')
                    preview_url = f"/uploads/{uploads_rel}"
                    
                    task.status = "success"
                    task.output_path = relative_output_path
                    task.output_filename = output_filename
                    task.preview_url = preview_url
                    task.progress = 100
                    task.error_message = None
                    task.updated_at = datetime.datetime.now()
                    db.commit()
                    
                    return response_success({
                        "task_id": task_id,
                        "output_filename": output_filename,
                        "preview_url": preview_url
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
            "subtitle_path": "string" # 可选，字幕文件路径（相对路径）
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
        video_ids = data.get("video_ids", [])
        voice_id = data.get("voice_id")
        bgm_id = data.get("bgm_id")
        speed = data.get("speed", 1.0)
        subtitle_path = (data.get("subtitle_path") or "").strip() or None

        if not video_ids or not isinstance(video_ids, list) or len(video_ids) == 0:
            return response_error("视频ID列表不能为空", 400)
        
        try:
            speed = float(speed)
        except Exception:
            return response_error("播放速度必须是数字", 400)
        
        if speed < 0.5 or speed > 2.0:
            return response_error("播放速度超出范围（0.5~2.0）", 400)

        # 查询视频素材的绝对路径
        video_paths = []
        with get_db() as db:
            for vid in video_ids:
                mat = db.query(Material).filter(Material.id == vid).first()
                if not mat or mat.type != "video":
                    return response_error(f"视频素材ID {vid} 不存在或类型错误", 400)
                abs_path = get_abs_path(mat.path)
                if not os.path.exists(abs_path):
                    return response_error(f"视频文件不存在：{mat.path}", 400)
                video_paths.append(abs_path)

            bgm_path = None
            voice_path = None
            
            if voice_id is not None:
                voice_mat = db.query(Material).filter(Material.id == voice_id).first()
                if not voice_mat or voice_mat.type != "audio":
                    return response_error(f"配音素材ID {voice_id} 不存在或类型错误", 400)
                voice_path = get_abs_path(voice_mat.path)
                if not os.path.exists(voice_path):
                    return response_error(f"配音文件不存在：{voice_mat.path}", 400)

            if bgm_id is not None:
                bgm_mat = db.query(Material).filter(Material.id == bgm_id).first()
                if not bgm_mat or bgm_mat.type != "audio":
                    return response_error(f"BGM素材ID {bgm_id} 不存在或类型错误", 400)
                bgm_path = get_abs_path(bgm_mat.path)
                if not os.path.exists(bgm_path):
                    return response_error(f"BGM文件不存在：{bgm_mat.path}", 400)

            abs_sub_path = None
            if subtitle_path:
                abs_sub_path = get_abs_path(subtitle_path)
                if not os.path.isfile(abs_sub_path):
                    return response_error(f"字幕文件不存在：{subtitle_path}", 400)

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
            args=(task_id, video_paths, voice_path, bgm_path, speed, abs_sub_path),
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
    获取成品列表接口
    
    请求方法: GET
    路径: /api/outputs
    认证: 需要登录
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "获取成品列表成功",
            "data": [
                {
                    "filename": "string",
                    "size": int,
                    "update_time": "string",
                    "preview_url": "string",
                    "download_url": "string",
                    "task_id": int
                }
            ]
        }
    """
    try:
        items = []

        # 优先：从任务表读取成功成品
        with get_db() as db:
            tasks = db.query(VideoEditTask).filter(
                VideoEditTask.status == "success",
                VideoEditTask.output_filename.isnot(None),
                VideoEditTask.output_filename != ""
            ).order_by(VideoEditTask.updated_at.desc()).limit(200).all()

        seen = set()
        for task in tasks:
            filename = task.output_filename
            if not filename or filename in seen:
                continue
            abs_path = os.path.join(OUTPUT_VIDEO_DIR, filename)
            if not os.path.isfile(abs_path):
                continue
            stat = os.stat(abs_path)
            seen.add(filename)
            items.append({
                "filename": filename,
                "size": stat.st_size,
                "update_time": (task.updated_at or datetime.datetime.fromtimestamp(stat.st_mtime)).strftime("%Y-%m-%d %H:%M:%S"),
                "preview_url": task.preview_url or f"/uploads/videos/{filename}",
                "download_url": f"/api/download/video/{filename}",
                "task_id": task.id,
            })

        # 兜底：扫目录补齐未入库成品
        if os.path.isdir(OUTPUT_VIDEO_DIR):
            for name in os.listdir(OUTPUT_VIDEO_DIR):
                if name in seen:
                    continue
                abs_path = os.path.join(OUTPUT_VIDEO_DIR, name)
                if not os.path.isfile(abs_path):
                    continue
                stat = os.stat(abs_path)
                items.append({
                    "filename": name,
                    "size": stat.st_size,
                    "update_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "preview_url": f"/uploads/videos/{name}",
                    "download_url": f"/api/download/video/{name}",
                })

        # 按更新时间排序
        items.sort(key=lambda x: x.get("update_time") or "", reverse=True)
        
        return response_success(items, "获取成品列表成功")
    
    except Exception as e:
        logger.exception("List outputs failed")
        return response_error(f"获取成品列表失败：{str(e)}", 500)


@editor_bp.route('/output/delete', methods=['POST'])
@login_required
def delete_output():
    """
    删除成品视频接口
    
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
        
        if not filename:
            return response_error("文件名不能为空", 400)
        
        if os.path.basename(filename) != filename or ".." in filename or "/" in filename or "\\" in filename:
            return response_error("非法文件名", 400)

        abs_path = os.path.normpath(os.path.join(OUTPUT_VIDEO_DIR, filename))
        
        try:
            if os.path.commonpath([os.path.normcase(abs_path), os.path.normcase(OUTPUT_VIDEO_DIR)]) != os.path.normcase(OUTPUT_VIDEO_DIR):
                return response_error("非法路径", 400)
        except Exception:
            return response_error("非法路径", 400)

        try:
            if not os.path.isfile(abs_path):
                return response_error("文件不存在", 404)
            os.remove(abs_path)
            return response_success(None, "删除成功")
        except Exception as e:
            return response_error(f"删除失败：{str(e)}", 500)

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
        output_path = os.path.join(OUTPUT_VIDEO_DIR, filename)
        if not os.path.exists(output_path):
            return response_error("视频文件不存在", 404)

        # 通过send_from_directory返回文件
        return send_from_directory(OUTPUT_VIDEO_DIR, filename, as_attachment=True)
    
    except Exception as e:
        logger.exception("Download video failed")
        return response_error(f"下载失败：{str(e)}", 500)

