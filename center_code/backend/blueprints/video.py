"""
视频上传API
"""
import json
from flask import Blueprint, request, send_from_directory
from datetime import datetime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required, has_valid_token
from models import VideoTask, Account
from db import get_db

video_bp = Blueprint('video', __name__, url_prefix='/api/video')


@video_bp.route('/upload', methods=['POST'])
@login_required
def create_video_task():
    """
    创建视频上传任务接口
    
    请求方法: POST
    路径: /api/video/upload
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int,          # 必填，账号ID
            "video_url": "string",       # 必填，视频URL
            "video_title": "string",     # 可选，视频标题
            "video_tags": "array",      # 可选，视频标签数组
            "publish_date": "string",    # 可选，发布时间（ISO 格式）
            "thumbnail_url": "string"   # 可选，缩略图URL
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Video task created",
            "data": {
                "id": int,
                "account_id": int,
                "device_id": int,
                "video_url": "string",
                "video_title": "string",
                "status": "string",
                "created_at": "string"
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 创建的视频任务初始状态为 pending（待处理）
        - 如果账号不存在，返回 404 错误
        - 任务会由客户端通过任务队列处理
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        video_url = data.get('video_url')
        video_title = data.get('video_title')
        video_tags = data.get('video_tags')
        publish_date = data.get('publish_date')
        thumbnail_url = data.get('thumbnail_url')
        
        if not account_id or not video_url:
            return response_error('account_id and video_url are required', 400)
        
        with get_db() as db:
            # 检查账号是否存在，并获取关联的device_id
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
            video_tags_json = json.dumps(video_tags) if video_tags else None
            publish_date_obj = datetime.fromisoformat(publish_date) if publish_date else None
            
            task = VideoTask(
                account_id=account_id,
                device_id=account.device_id,
                video_url=video_url,
                video_title=video_title,
                video_tags=video_tags_json,
                publish_date=publish_date_obj,
                thumbnail_url=thumbnail_url,
                status='pending'
            )
            db.add(task)
            db.flush()
            db.commit()
            
            return response_success({
                'id': task.id,
                'account_id': task.account_id,
                'device_id': task.device_id,
                'video_url': task.video_url,
                'video_title': task.video_title,
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None
            }, 'Video task created', 201)
    except Exception as e:
        return response_error(str(e), 500)


@video_bp.route('/tasks', methods=['GET'])
def get_video_tasks():
    """
    获取视频任务列表接口
    
    请求方法: GET
    路径: /api/video/tasks
    认证: 
        - 如果只查询account_id和status，不需要登录（设备端调用）
        - 其他情况需要登录（管理端调用）
    
    查询参数:
        account_id (int, 可选): 账号ID，筛选指定账号的任务
        status (string, 可选): 状态筛选（pending/uploading/completed/failed）
        limit (int, 可选): 每页数量，默认不限制
        offset (int, 可选): 偏移量，默认 0
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "tasks": [
                    {
                        "id": int,
                        "account_id": int,
                        "device_id": int,
                        "video_url": "string",
                        "video_title": "string",
                        "video_tags": "string",
                        "status": "string",
                        "progress": int,
                        "error_message": "string",
                        "created_at": "string",
                        "started_at": "string",
                        "completed_at": "string"
                    }
                ],
                "total": int
            }
        }
    
    说明:
        - 结果按创建时间倒序排列
        - 支持按账号和状态筛选
        - 支持分页查询
    """
    try:
        account_id = request.args.get('account_id', type=int)
        status = request.args.get('status')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', type=int, default=0)
        
        # 如果只提供了account_id和status参数，允许设备端调用（不需要登录）
        # 否则需要登录认证（管理端调用）
        if account_id is None and status is None:
            # 管理端调用，需要登录
            if not has_valid_token():
                return response_error('请先登录', 401)
        # 设备端调用（提供了account_id和status），不需要登录
        
        with get_db() as db:
            from models import PlanVideo
            
            query = db.query(VideoTask)
            
            if account_id:
                query = query.filter(VideoTask.account_id == account_id)
            
            if status:
                query = query.filter(VideoTask.status == status)
            
            # 排除发布计划中的任务：只显示立即发布的任务（video_url 不在 PlanVideo 中）
            # 获取所有发布计划中的 video_url，排除这些任务
            plan_video_urls = db.query(PlanVideo.video_url).distinct()
            query = query.filter(~VideoTask.video_url.in_(plan_video_urls))
            
            # 获取总数（在应用排序和分页之前）
            total = query.count()
            
            # 先应用排序，再应用分页（SQLAlchemy 要求 order_by 在 limit/offset 之前）
            query = query.order_by(VideoTask.created_at.desc())
            
            # 应用分页
            if limit:
                query = query.limit(limit).offset(offset)
            
            tasks = query.all()
            
            # 关联账号信息
            tasks_list = []
            for task in tasks:
                account_name = None
                platform = None
                if task.account_id:
                    account = db.query(Account).filter(Account.id == task.account_id).first()
                    if account:
                        account_name = account.account_name
                        platform = account.platform
                
                tasks_list.append({
                    'id': task.id,
                    'account_id': task.account_id,
                    'device_id': task.device_id,
                    'video_url': task.video_url,
                    'video_title': task.video_title,
                    'video_tags': task.video_tags,
                    'status': task.status,
                    'progress': task.progress,
                    'error_message': task.error_message,
                    'account_name': account_name,
                    'platform': platform,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                })
        
        return response_success({
            'tasks': tasks_list,
            'total': total
        })
    except Exception as e:
        return response_error(str(e), 500)


@video_bp.route('/tasks/<int:task_id>', methods=['GET', 'DELETE'])
@login_required
def video_task_detail(task_id):
    """
    获取或删除视频任务接口
    
    请求方法: GET / DELETE
    路径: /api/video/tasks/{task_id}
    认证: 需要登录
    
    路径参数:
        task_id (int): 视频任务ID
    
    GET 请求:
        返回数据:
            成功 (200):
            {
                "code": 200,
                "message": "success",
                "data": {
                    "id": int,
                    "account_id": int,
                    "device_id": int,
                    "video_url": "string",
                    "video_title": "string",
                    "video_tags": "string",
                    "status": "string",
                    "progress": int,
                    "error_message": "string",
                    "created_at": "string",
                    "started_at": "string",
                    "completed_at": "string"
                }
            }
    
    DELETE 请求:
        返回数据:
            成功 (200):
            {
                "code": 200,
                "message": "Task deleted successfully",
                "data": {
                    "task_id": int,
                    "video_title": "string",
                    "status": "string"
                }
            }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - GET: 获取任务详情
        - DELETE: 删除任务
        - 如果任务不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
            
            if not task:
                return response_error('Task not found', 404)
            
            if request.method == 'GET':
                return response_success({
                    'id': task.id,
                    'account_id': task.account_id,
                    'device_id': task.device_id,
                    'video_url': task.video_url,
                    'video_title': task.video_title,
                    'video_tags': task.video_tags,
                    'status': task.status,
                    'progress': task.progress,
                    'error_message': task.error_message,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                })
            
            elif request.method == 'DELETE':
                task_dict = {
                    'task_id': task.id,
                    'video_title': task.video_title,
                    'status': task.status
                }
                db.delete(task)
                db.commit()
                
                return response_success(task_dict, 'Task deleted successfully')
    except Exception as e:
        return response_error(str(e), 500)


@video_bp.route('/callback', methods=['POST'])
def video_callback():
    """
    视频上传回调接口（设备端调用）
    
    请求方法: POST
    路径: /api/video/callback
    认证: 不需要（设备端调用）
    
    请求体 (JSON):
        {
            "task_id": int,              # 必填，任务ID
            "status": "string",          # 必填，任务状态（pending/uploading/completed/failed）
            "progress": int,             # 可选，上传进度（0-100），默认 0
            "error_message": "string"   # 可选，错误信息
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
                "status": "string",
                "progress": int
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 设备端完成视频上传后调用此接口上报任务状态
        - 如果状态为 completed 或 failed，会自动设置 completed_at 时间
        - 如果状态为 uploading 且任务未开始，会自动设置 started_at 时间
        - 如果任务不存在，返回 404 错误
    """
    try:
        data = request.json
        task_id = data.get('task_id')
        status = data.get('status')
        progress = data.get('progress', 0)
        error_message = data.get('error_message')
        
        if not task_id or not status:
            return response_error('task_id and status are required', 400)
        
        with get_db() as db:
            task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
            
            if not task:
                return response_error('Task not found', 404)
            
            task.status = status
            task.progress = progress
            task.error_message = error_message
            
            if status in ['completed', 'failed']:
                task.completed_at = datetime.now()
            else:
                if not task.started_at:
                    task.started_at = datetime.now()
            
            db.commit()
            
            return response_success({
                'id': task.id,
                'status': task.status,
                'progress': task.progress
            })
    except Exception as e:
        return response_error(str(e), 500)


@video_bp.route('/download/<filename>', methods=['GET'])
def download_video_file(filename):
    """下载视频文件"""
    try:
        upload_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
        file_path = os.path.join(upload_dir, filename)
        
        if not os.path.abspath(file_path).startswith(os.path.abspath(upload_dir)):
            return response_error('Invalid file path', 403)
        
        if not os.path.exists(file_path):
            return response_error('File not found', 404)
        
        return send_from_directory(upload_dir, filename, as_attachment=False)
    except Exception as e:
        return response_error(str(e), 500)

