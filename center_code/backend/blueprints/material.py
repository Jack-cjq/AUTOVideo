"""
素材管理API（视频/音频素材）
提供素材上传、查询、删除等功能
"""
import os
import sys
import uuid
import glob
from flask import Blueprint, request, send_from_directory
from datetime import datetime
from werkzeug.utils import secure_filename

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Material
from db import get_db

material_bp = Blueprint('material', __name__, url_prefix='/api')

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_ROOT = os.path.join(BASE_DIR, 'uploads')
MATERIAL_VIDEO_DIR = os.path.join(UPLOAD_ROOT, 'materials', 'videos')
MATERIAL_AUDIO_DIR = os.path.join(UPLOAD_ROOT, 'materials', 'audios')
MATERIAL_IMAGE_DIR = os.path.join(UPLOAD_ROOT, 'materials', 'images')

# 允许的文件扩展名
ALLOWED_VIDEO_EXT = ('.mp4', '.avi', '.mov')
ALLOWED_AUDIO_EXT = ('.mp3', '.wav', '.flac')
ALLOWED_IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

# 自动创建目录
for dir_path in [UPLOAD_ROOT, MATERIAL_VIDEO_DIR, MATERIAL_AUDIO_DIR, MATERIAL_IMAGE_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def allowed_file(filename, file_type='video'):
    """校验文件扩展名是否允许"""
    ext = os.path.splitext(filename)[-1].lower()
    if file_type == 'video':
        return ext in ALLOWED_VIDEO_EXT
    elif file_type == 'audio':
        return ext in ALLOWED_AUDIO_EXT
    elif file_type == 'image':
        return ext in ALLOWED_IMAGE_EXT
    return False


@material_bp.route('/material/upload', methods=['POST'])
@login_required
def upload_material():
    """
    上传素材接口（视频/音频）
    
    请求方法: POST
    路径: /api/material/upload
    认证: 需要登录
    
    请求体 (multipart/form-data):
        file (file): 必填，视频或音频文件
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "上传成功",
            "data": {
                "material_id": int,
                "name": "string",
                "target_name": "string",
                "path": "string",
                "type": "string"
            }
        }
    """
    try:
        if 'file' not in request.files:
            return response_error('未选择文件', 400)
        
        file = request.files['file']
        if file.filename.strip() == '':
            return response_error('文件名不能为空', 400)
        
        # 校验文件类型并确定存储目录
        filename = file.filename
        file_type = None
        save_dir = None
        
        # 提取文件扩展名用于调试
        ext = os.path.splitext(filename)[-1].lower()
        
        if allowed_file(filename, 'video'):
            file_type = 'video'
            save_dir = MATERIAL_VIDEO_DIR
        elif allowed_file(filename, 'audio'):
            file_type = 'audio'
            save_dir = MATERIAL_AUDIO_DIR
        elif allowed_file(filename, 'image'):
            file_type = 'image'
            save_dir = MATERIAL_IMAGE_DIR
        else:
            return response_error(
                f'不支持的文件类型（扩展名: {ext}），仅支持视频(mp4/avi/mov)、音频(mp3/wav/flac)、图片(jpg/jpeg/png/gif/webp)',
                400
            )
        
        # 调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'上传文件: {filename}, 扩展名: {ext}, 类型: {file_type}, 目录: {save_dir}')
        
        # 生成唯一文件名
        ext = os.path.splitext(filename)[-1].lower()
        unique_filename = str(uuid.uuid4()) + ext
        save_path = os.path.join(save_dir, unique_filename)
        
        # 保存文件
        file.save(save_path)
        
        # 提取元数据（可选，需要 ffmpeg-python）
        duration = None
        width = None
        height = None
        size = None
        
        try:
            size = os.path.getsize(save_path)
        except Exception:
            pass
        
        # TODO: 使用 ffmpeg 提取视频/音频元数据
        # 这里暂时跳过，后续可以添加
        
        # 写入数据库（存储相对路径）
        relative_path = os.path.relpath(save_path, BASE_DIR).replace(os.sep, '/')
        
        # 检查路径是否已存在（应用层唯一性检查）
        with get_db() as db:
            existing = db.query(Material).filter(Material.path == relative_path).first()
            if existing:
                # 如果已存在，删除刚保存的文件
                try:
                    os.remove(save_path)
                except Exception:
                    pass
                return response_error('该文件路径已存在', 409)
            
            material = Material(
                name=filename,
                path=relative_path,
                type=file_type,
                duration=duration,
                width=width,
                height=height,
                size=size
            )
            db.add(material)
            db.flush()
            db.commit()
            
            return response_success({
                'material_id': material.id,
                'name': filename,
                'target_name': unique_filename,
                'path': relative_path,
                'type': file_type
            }, '上传成功')
    
    except Exception as e:
        return response_error(str(e), 500)


@material_bp.route('/materials', methods=['GET'])
@login_required
def get_materials():
    """
    获取素材列表接口
    
    请求方法: GET
    路径: /api/materials
    认证: 需要登录
    
    查询参数:
        type (string, 可选): 素材类型（video/audio）
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "获取素材列表成功",
            "data": [
                {
                    "id": int,
                    "name": "string",
                    "path": "string",
                    "type": "string",
                    "duration": int,
                    "width": int,
                    "height": int,
                    "size": int,
                    "create_time": "string"
                }
            ]
        }
    """
    try:
        material_type = request.args.get('type')
        
        with get_db() as db:
            query = db.query(Material)
            
            if material_type:
                query = query.filter(Material.type == material_type)
            
            materials = query.order_by(Material.created_at.desc()).all()
            
            materials_list = []
            for mat in materials:
                # 确保 type 字段是小写，统一格式
                material_type = (mat.type or '').lower() if mat.type else None
                materials_list.append({
                    'id': mat.id,
                    'name': mat.name,
                    'path': mat.path,
                    'type': material_type,  # 统一转换为小写
                    'duration': mat.duration,
                    'width': mat.width,
                    'height': mat.height,
                    'size': mat.size,
                    'created_at': mat.created_at.isoformat() if mat.created_at else None,
                    'create_time': mat.created_at.isoformat() if mat.created_at else None  # 兼容字段
                })
        
        return response_success(materials_list, '获取素材列表成功')
    
    except Exception as e:
        return response_error(str(e), 500)


@material_bp.route('/materials/clear', methods=['POST'])
@login_required
def clear_materials():
    """
    清空素材库接口
    
    请求方法: POST
    路径: /api/materials/clear
    认证: 需要登录
    
    请求体 (JSON):
        {
            "confirm": true  # 必填，确认清空操作
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "清空完成",
            "data": {
                "deleted_files": int,
                "deleted_db_rows": int
            }
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        if data.get('confirm') is not True:
            return response_error('请传入 confirm=true 以确认清空操作', 400)
        
        deleted_files = 0
        delete_errors = []
        
        # 删除文件
        for dir_path in [MATERIAL_VIDEO_DIR, MATERIAL_AUDIO_DIR, MATERIAL_IMAGE_DIR]:
            try:
                if not os.path.isdir(dir_path):
                    continue
                for path in glob.glob(os.path.join(dir_path, '*')):
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                            deleted_files += 1
                    except Exception as e:
                        delete_errors.append(f"{path}: {e}")
            except Exception as e:
                delete_errors.append(f"{dir_path}: {e}")
        
        # 删除数据库记录
        deleted_rows = 0
        with get_db() as db:
            deleted_rows = db.query(Material).delete()
            db.commit()
        
        return response_success({
            'deleted_files': deleted_files,
            'deleted_db_rows': deleted_rows,
            'delete_errors': delete_errors
        }, '清空完成')
    
    except Exception as e:
        return response_error(str(e), 500)


@material_bp.route('/delete-material', methods=['POST'])
@login_required
def delete_material():
    """
    删除素材接口
    
    请求方法: POST
    路径: /api/delete-material
    认证: 需要登录
    
    请求体 (JSON):
        {
            "material_id": int,      # 必填，素材ID
            "file_path": "string",   # 必填，文件路径
            "force": false           # 可选，是否强制删除（即使被任务引用）
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
        def _task_references_material(task, mid: int) -> bool:
            try:
                if getattr(task, 'voice_id', None) == mid:
                    return True
                if getattr(task, 'bgm_id', None) == mid:
                    return True
            except Exception:
                pass

            raw = getattr(task, 'video_ids', None) or ''
            raw = str(raw).strip()
            if not raw:
                return False

            if raw.startswith('{') or raw.startswith('['):
                try:
                    import json as _json
                    payload = _json.loads(raw)
                    clips = payload.get('clips') if isinstance(payload, dict) else payload
                    if isinstance(clips, list):
                        for c in clips:
                            if not isinstance(c, dict):
                                continue
                            try:
                                if int(c.get('materialId')) == mid:
                                    return True
                            except Exception:
                                continue
                except Exception:
                    pass

            try:
                for part in raw.split(','):
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        if int(part) == mid:
                            return True
                    except Exception:
                        continue
            except Exception:
                pass

            return False
        data = request.get_json(silent=True) or {}
        material_id = data.get('material_id')
        file_path = data.get('file_path', '')
        force = data.get('force', False)
        
        if material_id is None:
            return response_error('material_id 不能为空', 400)
        
        try:
            material_id = int(material_id)
        except Exception:
            return response_error('material_id 必须是整数', 400)
        
        with get_db() as db:
            material = db.query(Material).filter(Material.id == material_id).first()
            
            if not material:
                return response_error('素材不存在', 404)
            
            # 检查是否被任务引用（如果不强制删除）
            if not force:
                from models import VideoEditTask
                # 检查是否有任务引用此素材
                tasks = db.query(VideoEditTask).filter(
                    (VideoEditTask.video_ids.like(f'%{material_id}%')) |
                    (VideoEditTask.voice_id == material_id) |
                    (VideoEditTask.bgm_id == material_id)
                ).limit(200).all()
                tasks = [t for t in tasks if _task_references_material(t, material_id)]
                
                if tasks:
                    task_ids = [str(t.id) for t in tasks[:10]]
                    task_count = len(tasks)
                    return response_error(
                        f'该素材被 {task_count} 个任务引用，无法删除。如需强制删除，请设置 force=true（任务ID示例：{",".join(task_ids)}）',
                        409
                    )
            
            # 删除文件
            abs_path = os.path.join(BASE_DIR, material.path)
            try:
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
            except Exception as e:
                pass  # 文件删除失败不影响数据库删除
            
            # 删除数据库记录
            db.delete(material)
            db.commit()
            
            return response_success(None, '删除成功')
    
    except Exception as e:
        return response_error(str(e), 500)

