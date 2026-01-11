"""
立即发布API
"""
import json
import os
from flask import Blueprint, request, send_from_directory
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import VideoTask, Account, VideoLibrary
from db import get_db

publish_bp = Blueprint('publish', __name__, url_prefix='/api/publish')


@publish_bp.route('/upload-video', methods=['POST'])
@login_required
def upload_video():
    """
    上传视频文件接口
    
    请求方法: POST
    路径: /api/publish/upload-video
    认证: 需要登录
    
    请求体 (multipart/form-data):
        file: 视频文件
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Upload successful",
            "data": {
                "url": "string",
                "filename": "string"
            }
        }
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return response_error('No file provided', 400)
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return response_error('No file selected', 400)
        
        # 检查文件类型
        allowed_extensions = {'.mp4', '.mov', '.avi', '.flv', '.wmv', '.webm', '.mkv'}
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return response_error(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}', 400)
        
        # 创建上传目录
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads', 'videos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(upload_dir, unique_filename)
        
        # 保存文件
        file.save(filepath)
        
        # 返回文件URL（相对于静态文件目录）
        file_url = f'/uploads/videos/{unique_filename}'
        
        return response_success({
            'url': file_url,
            'filename': unique_filename
        }, 'Upload successful')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return response_error(f'Upload failed: {str(e)}', 500)


@publish_bp.route('/upload-thumbnail', methods=['POST'])
@login_required
def upload_thumbnail():
    """
    上传封面图片接口
    
    请求方法: POST
    路径: /api/publish/upload-thumbnail
    认证: 需要登录
    
    请求体 (multipart/form-data):
        file: 图片文件
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Upload successful",
            "data": {
                "url": "string",
                "filename": "string"
            }
        }
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return response_error('No file provided', 400)
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return response_error('No file selected', 400)
        
        # 检查文件类型
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return response_error(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}', 400)
        
        # 检查文件大小（限制为5MB）
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 5 * 1024 * 1024:  # 5MB
            return response_error('File size exceeds 5MB limit', 400)
        
        # 创建上传目录
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads', 'thumbnails')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(upload_dir, unique_filename)
        
        # 保存文件
        file.save(filepath)
        
        # 返回文件URL（相对于静态文件目录）
        file_url = f'/uploads/thumbnails/{unique_filename}'
        
        return response_success({
            'url': file_url,
            'filename': unique_filename
        }, 'Upload successful')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return response_error(f'Upload failed: {str(e)}', 500)


@publish_bp.route('/submit', methods=['POST'])
@login_required
def submit_publish():
    """
    提交发布任务接口
    
    请求方法: POST
    路径: /api/publish/submit
    认证: 需要登录
    
    请求体 (JSON):
        {
            "video_id": int,                # 可选，视频库中的视频ID
            "video_url": "string",           # 可选，视频URL
            "video_title": "string",         # 必填，视频标题
            "video_description": "string",   # 可选，视频描述
            "video_tags": ["string"],        # 可选，视频标签数组
            "thumbnail_url": "string",       # 可选，缩略图URL
            "account_ids": [int],            # 必填，账号ID数组
            "publish_date": "string",        # 可选，发布时间（ISO 格式）
            "publish_type": "string",        # 可选，发布类型（immediate/scheduled/interval）
            "publish_interval": int,         # 可选，发布间隔（分钟）
            "priority": "string",            # 可选，优先级（high/normal/low）
            "after_publish_actions": ["string"],  # 可选，发布后操作
            "retry_on_failure": bool,        # 可选，失败重试
            "retry_count": int               # 可选，重试次数
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Publish tasks created",
            "data": {
                "task_ids": [int],
                "total_accounts": int,
                "total_tasks": int
            }
        }
    """
    try:
        data = request.json
        video_id = data.get('video_id')
        video_url = data.get('video_url')
        video_title = data.get('video_title')
        video_description = data.get('video_description')
        video_tags = data.get('video_tags', [])
        thumbnail_url = data.get('thumbnail_url')
        account_ids = data.get('account_ids', [])
        publish_date = data.get('publish_date')
        publish_type = data.get('publish_type', 'immediate')
        publish_interval = data.get('publish_interval', 30)  # 默认30分钟
        priority = data.get('priority', 'normal')
        
        # 验证必填字段
        if not video_title:
            return response_error('video_title is required', 400)
        
        if not account_ids or len(account_ids) == 0:
            return response_error('account_ids is required', 400)
        
        if not video_id and not video_url:
            return response_error('video_id or video_url is required', 400)
        
        with get_db() as db:
            # 1. 获取视频URL（如果提供了video_id，从视频库获取）
            final_video_url = video_url
            final_thumbnail_url = thumbnail_url
            
            if video_id:
                video_lib = db.query(VideoLibrary).filter(VideoLibrary.id == video_id).first()
                if not video_lib:
                    return response_error(f'Video library item {video_id} not found', 404)
                final_video_url = video_lib.video_url
                if not final_thumbnail_url and video_lib.thumbnail_url:
                    final_thumbnail_url = video_lib.thumbnail_url
                # 如果视频库中有标签，可以合并
                if video_lib.tags and not video_tags:
                    try:
                        video_tags = [tag.strip() for tag in video_lib.tags.split(',') if tag.strip()]
                    except:
                        pass
            
            # 2. 验证所有账号是否存在，并获取账号信息
            accounts = []
            for account_id in account_ids:
                account = db.query(Account).filter(Account.id == account_id).first()
                if not account:
                    return response_error(f'Account {account_id} not found', 404)
                # 检查账号是否有cookies（已登录）
                if not account.cookies:
                    return response_error(f'Account {account_id} ({account.account_name}) has no cookies. Please login first.', 400)
                accounts.append(account)
            
            # 3. 根据发布类型创建任务
            task_ids = []
            base_publish_date = None
            
            if publish_date:
                try:
                    base_publish_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
                except:
                    try:
                        base_publish_date = datetime.fromisoformat(publish_date)
                    except:
                        return response_error('Invalid publish_date format. Use ISO format.', 400)
            
            # 处理视频标签
            video_tags_json = None
            if video_tags:
                if isinstance(video_tags, list):
                    video_tags_json = json.dumps(video_tags, ensure_ascii=False)
                elif isinstance(video_tags, str):
                    video_tags_json = video_tags
            
            # 为每个账号创建任务
            for idx, account in enumerate(accounts):
                # 计算发布时间（如果是间隔发布）
                task_publish_date = None
                if publish_type == 'scheduled' and base_publish_date:
                    task_publish_date = base_publish_date
                elif publish_type == 'interval' and base_publish_date:
                    # 间隔发布：每个账号间隔指定分钟数
                    interval_minutes = publish_interval * idx
                    task_publish_date = base_publish_date + timedelta(minutes=interval_minutes)
                elif publish_type == 'immediate':
                    # 立即发布：不设置发布时间
                    task_publish_date = None
                
                # 创建视频任务
                task = VideoTask(
                    account_id=account.id,
                    device_id=account.device_id,
                    video_url=final_video_url,
                    video_title=video_title,
                    video_tags=video_tags_json,
                    publish_date=task_publish_date,
                    thumbnail_url=final_thumbnail_url,
                    status='pending'
                )
                db.add(task)
                db.flush()
                task_ids.append(task.id)
            
            db.commit()
            
            return response_success({
                'task_ids': task_ids,
                'total_accounts': len(accounts),
                'total_tasks': len(task_ids)
            }, f'Publish tasks created successfully for {len(accounts)} account(s)')
            
    except Exception as e:
        return response_error(str(e), 500)


@publish_bp.route('/history', methods=['POST'])
@login_required
def get_publish_history():
    """
    获取发布历史接口
    
    请求方法: POST
    路径: /api/publish/history
    认证: 需要登录
    
    请求体 (JSON):
        {
            "page": int,    # 可选，页码，默认 1
            "size": int,    # 可选，每页数量，默认 10
            "account_id": int,  # 可选，筛选账号ID
            "status": "string"  # 可选，筛选状态
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "list": [
                    {
                        "id": int,
                        "video_title": "string",
                        "account_name": "string",
                        "platform": "string",
                        "status": "string",
                        "progress": int,
                        "created_at": "string",
                        "completed_at": "string"
                    }
                ],
                "total": int,
                "page": int,
                "size": int
            }
        }
    """
    try:
        data = request.json or {}
        page = data.get('page', 1)
        size = data.get('size', 10)
        account_id = data.get('account_id')
        status = data.get('status')
        
        with get_db() as db:
            # 查询视频任务，关联账号信息
            query = db.query(VideoTask, Account).join(Account, VideoTask.account_id == Account.id)
            
            if account_id:
                query = query.filter(VideoTask.account_id == account_id)
            
            if status:
                query = query.filter(VideoTask.status == status)
            
            # 获取总数
            total = query.count()
            
            # 分页查询
            offset = (page - 1) * size
            results = query.order_by(VideoTask.created_at.desc()).limit(size).offset(offset).all()
            
            # 构建返回数据
            task_list = []
            for task, account in results:
                task_list.append({
                    'id': task.id,
                    'video_title': task.video_title,
                    'account_name': account.account_name,
                    'platform': account.platform,
                    'status': task.status,
                    'progress': task.progress,
                    'error_message': task.error_message,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                })
            
            return response_success({
                'list': task_list,
                'total': total,
                'page': page,
                'size': size
            })
            
    except Exception as e:
        return response_error(str(e), 500)

