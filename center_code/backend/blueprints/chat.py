"""
对话功能API
"""
from flask import Blueprint, request
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import ChatTask, Account
from db import get_db

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


@chat_bp.route('/send', methods=['POST'])
@login_required
def create_chat_task():
    """
    创建对话发送任务接口
    
    请求方法: POST
    路径: /api/chat/send
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int,        # 必填，账号ID
            "target_user": "string",   # 必填，目标用户（用户名或ID）
            "message": "string"        # 必填，要发送的消息内容
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Chat task created",
            "data": {
                "id": int,
                "account_id": int,
                "target_user": "string",
                "message": "string",
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
        - 创建的任务初始状态为 pending（待处理）
        - 如果账号不存在，返回 404 错误
        - 任务会由客户端通过任务队列处理
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        target_user = data.get('target_user')
        message = data.get('message')
        
        if not account_id or not target_user or not message:
            return response_error('account_id, target_user and message are required', 400)
        
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
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
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None
            }, 'Chat task created', 201)
    except Exception as e:
        return response_error(str(e), 500)


@chat_bp.route('/tasks', methods=['GET'])
@login_required
def get_chat_tasks():
    """
    获取对话任务列表接口
    
    请求方法: GET
    路径: /api/chat/tasks
    认证: 需要登录
    
    查询参数:
        account_id (int, 可选): 账号ID，筛选指定账号的任务
        status (string, 可选): 状态筛选（pending/completed/failed）
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": int,
                    "account_id": int,
                    "target_user": "string",
                    "message": "string",
                    "status": "string",
                    "error_message": "string",
                    "created_at": "string",
                    "started_at": "string",
                    "completed_at": "string"
                }
            ]
        }
    
    说明:
        - 结果按创建时间倒序排列
        - 支持按账号和状态筛选
    """
    try:
        account_id = request.args.get('account_id', type=int)
        status = request.args.get('status')
        
        with get_db() as db:
            query = db.query(ChatTask)
            
            if account_id:
                query = query.filter(ChatTask.account_id == account_id)
            
            if status:
                query = query.filter(ChatTask.status == status)
            
            tasks = query.order_by(ChatTask.created_at.desc()).all()
            
            tasks_list = []
            for task in tasks:
                tasks_list.append({
                    'id': task.id,
                    'account_id': task.account_id,
                    'target_user': task.target_user,
                    'message': task.message,
                    'status': task.status,
                    'error_message': task.error_message,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                })
        
        return response_success(tasks_list)
    except Exception as e:
        return response_error(str(e), 500)


@chat_bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_chat_task(task_id):
    """
    获取对话任务详情接口
    
    请求方法: GET
    路径: /api/chat/tasks/{task_id}
    认证: 需要登录
    
    路径参数:
        task_id (int): 对话任务ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
                "account_id": int,
                "target_user": "string",
                "message": "string",
                "status": "string",
                "error_message": "string",
                "created_at": "string",
                "started_at": "string",
                "completed_at": "string"
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果任务不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            task = db.query(ChatTask).filter(ChatTask.id == task_id).first()
            
            if not task:
                return response_error('Task not found', 404)
            
            return response_success({
                'id': task.id,
                'account_id': task.account_id,
                'target_user': task.target_user,
                'message': task.message,
                'status': task.status,
                'error_message': task.error_message,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            })
    except Exception as e:
        return response_error(str(e), 500)


@chat_bp.route('/callback', methods=['POST'])
def chat_callback():
    """
    对话任务回调接口（设备端调用）
    
    请求方法: POST
    路径: /api/chat/callback
    认证: 不需要（设备端调用）
    
    请求体 (JSON):
        {
            "task_id": int,              # 必填，任务ID
            "status": "string",          # 必填，任务状态（pending/sending/completed/failed）
            "error_message": "string"   # 可选，错误信息
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
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
        - 设备端完成对话发送后调用此接口上报任务状态
        - 如果状态为 completed 或 failed，会自动设置 completed_at 时间
        - 如果状态为 sending 且任务未开始，会自动设置 started_at 时间
        - 如果任务不存在，返回 404 错误
    """
    try:
        data = request.json
        task_id = data.get('task_id')
        status = data.get('status')
        error_message = data.get('error_message')
        
        if not task_id or not status:
            return response_error('task_id and status are required', 400)
        
        with get_db() as db:
            task = db.query(ChatTask).filter(ChatTask.id == task_id).first()
            
            if not task:
                return response_error('Task not found', 404)
            
            task.status = status
            task.error_message = error_message
            
            if status in ['completed', 'failed']:
                task.completed_at = datetime.now()
            else:
                if not task.started_at:
                    task.started_at = datetime.now()
            
            db.commit()
            
            return response_success({
                'id': task.id,
                'status': task.status
            })
    except Exception as e:
        return response_error(str(e), 500)

