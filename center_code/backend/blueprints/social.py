"""
社交平台相关API
"""
import json
import os
import urllib.parse
from flask import Blueprint, request
from datetime import datetime
from werkzeug.utils import secure_filename
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import VideoTask, ListenTask, Account, Message
from db import get_db

social_bp = Blueprint('social', __name__, url_prefix='/api/social')


@social_bp.route('/upload', methods=['POST'])
@login_required
def social_upload_video():
    """
    上传视频接口（使用任务队列模式）
    
    请求方法: POST
    路径: /api/social/upload
    认证: 需要登录
    
    请求体 (multipart/form-data):
        video (file, 必填): 视频文件
        account_id (int, 必填): 账号ID
        title (string, 可选): 视频标题
        tags (string, 可选): 视频标签（逗号分隔）
        publish_date (string, 可选): 发布时间（ISO 格式）
        thumbnail (file, 可选): 缩略图文件
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Task created",
            "data": {
                "task_id": int,
                "account_id": int,
                "title": "string",
                "status": "string",
                "message": "string"
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 上传的视频文件会保存到服务器的 uploads 目录
        - 创建视频任务，任务状态为 pending
        - 任务会由客户端通过任务队列处理
        - 如果账号不存在，返回 404 错误
    """
    try:
        if 'video' not in request.files:
            return response_error('No video file provided', 400)
        
        file = request.files['video']
        account_id = request.form.get('account_id', type=int)
        title = request.form.get('title', '').strip()
        tags = request.form.get('tags', '').strip()
        publish_date = request.form.get('publish_date')
        thumbnail = request.files.get('thumbnail')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 创建临时目录保存上传的文件
        upload_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存视频文件
        filename = secure_filename(file.filename)
        video_path = os.path.join(upload_dir, f"{account_id}_{int(datetime.now().timestamp())}_{filename}")
        file.save(video_path)
        
        # 保存缩略图（如果有）
        thumbnail_path = None
        if thumbnail and thumbnail.filename:
            thumbnail_filename = secure_filename(thumbnail.filename)
            thumbnail_path = os.path.join(upload_dir, f"{account_id}_{int(datetime.now().timestamp())}_{thumbnail_filename}")
            thumbnail.save(thumbnail_path)
        
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
            # 创建HTTP URL
            filename_only = os.path.basename(video_path)
            filename_encoded = urllib.parse.quote(filename_only)
            scheme = request.scheme
            host = request.host
            video_url = f"{scheme}://{host}/api/video/download/{filename_encoded}"
            
            thumbnail_url_http = None
            if thumbnail_path:
                thumbnail_filename_only = os.path.basename(thumbnail_path)
                thumbnail_filename_encoded = urllib.parse.quote(thumbnail_filename_only)
                thumbnail_url_http = f"{scheme}://{host}/api/video/download/{thumbnail_filename_encoded}"
            
            video_tags_json = json.dumps(tags.split(',') if tags else []) if tags else None
            publish_date_obj = datetime.fromisoformat(publish_date) if publish_date else None
            
            task = VideoTask(
                account_id=account_id,
                device_id=account.device_id,
                video_url=video_url,
                video_title=title,
                video_tags=video_tags_json,
                publish_date=publish_date_obj,
                thumbnail_url=thumbnail_url_http,
                status='pending'
            )
            db.add(task)
            db.flush()
            db.commit()
        
        return response_success({
            'task_id': task.id,
            'account_id': account_id,
            'title': title,
            'status': 'pending',
            'message': 'Task created. Client will process it via task queue.'
        }, 'Task created', 201)
    except Exception as e:
        return response_error(str(e), 500)


@social_bp.route('/listen/start', methods=['POST'])
@login_required
def social_start_listen():
    """
    启动消息监听接口
    
    请求方法: POST
    路径: /api/social/listen/start
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int  # 必填，账号ID
        }
    
    返回数据:
        成功 (200/201):
        {
            "code": 200/201,
            "message": "Listen task created. Client will process it via task queue.",
            "data": {
                "id": int,
                "account_id": int,
                "action": "start",
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
        - 如果账号已有 running 状态的监听任务，返回现有任务信息（200）
        - 如果账号有 pending 状态的监听任务，会重新激活该任务
        - 否则创建新的监听任务，状态为 pending
        - 任务会由客户端通过任务队列处理
        - 如果账号不存在，返回 404 错误
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
            # 检查是否有running状态的start任务
            running_task = db.query(ListenTask).filter(
                ListenTask.account_id == account_id,
                ListenTask.action == 'start',
                ListenTask.status == 'running'
            ).order_by(ListenTask.created_at.desc()).first()
            
            if running_task:
                return response_success({
                    'id': running_task.id,
                    'account_id': running_task.account_id,
                    'action': running_task.action,
                    'status': running_task.status
                }, 'Listen task is already running.', 200)
            
            # 检查是否有pending状态的start任务
            pending_task = db.query(ListenTask).filter(
                ListenTask.account_id == account_id,
                ListenTask.action == 'start',
                ListenTask.status == 'pending'
            ).order_by(ListenTask.created_at.desc()).first()
            
            if pending_task:
                pending_task.created_at = datetime.now()
                pending_task.status = 'pending'
                pending_task.error_message = None
                db.commit()
                task = pending_task
            else:
                # 创建新的监听任务
                task = ListenTask(
                    account_id=account_id,
                    device_id=account.device_id,
                    action='start',
                    status='pending'
                )
                db.add(task)
                db.flush()
                db.commit()
        
        return response_success({
            'id': task.id,
            'account_id': task.account_id,
            'action': task.action,
            'status': task.status,
            'created_at': task.created_at.isoformat() if task.created_at else None
        }, 'Listen task created. Client will process it via task queue.', 201)
    except Exception as e:
        return response_error(str(e), 500)


@social_bp.route('/listen/stop', methods=['POST'])
@login_required
def social_stop_listen():
    """
    停止消息监听接口
    
    请求方法: POST
    路径: /api/social/listen/stop
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int  # 必填，账号ID
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Stop listen task created",
            "data": {
                "id": int,
                "account_id": int,
                "action": "stop",
                "status": "string"
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 创建停止监听任务，状态为 pending
        - 任务会由客户端通过任务队列处理
        - 如果账号不存在，返回 404 错误
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
            # 创建停止监听任务
            task = ListenTask(
                account_id=account_id,
                device_id=account.device_id,
                action='stop',
                status='pending'
            )
            db.add(task)
            db.flush()
            db.commit()
        
        return response_success({
            'id': task.id,
            'account_id': task.account_id,
            'action': task.action,
            'status': task.status
        }, 'Stop listen task created', 201)
    except Exception as e:
        return response_error(str(e), 500)


@social_bp.route('/listen/messages', methods=['GET'])
@login_required
def social_get_messages():
    """
    获取监听到的消息接口
    
    请求方法: GET
    路径: /api/social/listen/messages
    认证: 需要登录
    
    查询参数:
        account_id (int, 必填): 账号ID
        limit (int, 可选): 每页数量，默认 100
        offset (int, 可选): 偏移量，默认 0
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "account_id": int,
                "messages": [
                    {
                        "id": int,
                        "user_name": "string",
                        "text": "string",
                        "is_me": bool,
                        "time": "string",
                        "timestamp": "string",
                        "created_at": "string"
                    }
                ],
                "count": int,
                "total": int
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - account_id 为必填参数，如果未提供返回 400 错误
        - 返回指定账号的所有消息，按时间倒序排列
        - 支持分页
    """
    try:
        account_id = request.args.get('account_id', type=int)
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        with get_db() as db:
            total = db.query(Message).filter(Message.account_id == account_id).count()
            
            messages = db.query(Message).filter(
                Message.account_id == account_id
            ).order_by(Message.timestamp.desc(), Message.created_at.desc()).limit(limit).offset(offset).all()
            
            messages_list = []
            for msg in messages:
                messages_list.append({
                    'id': msg.id,
                    'user_name': msg.user_name,
                    'text': msg.text,
                    'is_me': bool(msg.is_me),
                    'time': msg.message_time,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                    'created_at': msg.created_at.isoformat() if msg.created_at else None
                })
        
        return response_success({
            'account_id': account_id,
            'messages': messages_list,
            'count': len(messages_list),
            'total': total
        })
    except Exception as e:
        return response_error(str(e), 500)


@social_bp.route('/chat/reply', methods=['POST'])
@login_required
def social_reply_message():
    """
    回复消息接口
    
    请求方法: POST
    路径: /api/social/chat/reply
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int,        # 必填，账号ID
            "target_user": "string", # 必填，目标用户（用户名或ID）
            "message": "string"      # 必填，回复消息内容
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Reply task created",
            "data": {
                "id": int,
                "account_id": int,
                "target_user": "string",
                "message": "string",
                "status": "string"
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 创建对话任务，任务状态为 pending
        - 任务会由客户端通过任务队列处理
        - 如果账号不存在，返回 404 错误
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        target_user = data.get('target_user')
        message = data.get('message')
        
        if not account_id or not target_user or not message:
            return response_error('account_id, target_user and message are required', 400)
        
        # 创建对话任务
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
            from models import ChatTask
            task = ChatTask(
                account_id=account_id,
                device_id=account.device_id,
                target_user=target_user,
                message=message,
                status='pending'
            )
            db.add(task)
            db.flush()
            db.commit()
            
            return response_success({
                'id': task.id,
                'account_id': task.account_id,
                'target_user': task.target_user,
                'message': task.message,
                'status': task.status
            }, 'Reply task created', 201)
    except Exception as e:
        return response_error(str(e), 500)

