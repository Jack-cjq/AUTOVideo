"""
监听功能API
"""
from flask import Blueprint, request
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import ListenTask, Account
from db import get_db

listen_bp = Blueprint('listen', __name__, url_prefix='/api/listen')


@listen_bp.route('/start', methods=['POST'])
@login_required
def create_listen_task():
    """
    创建监听任务接口
    
    请求方法: POST
    路径: /api/listen/start
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int,        # 必填，账号ID
            "action": "string"        # 必填，操作类型（start/stop）
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Listen task created",
            "data": {
                "id": int,
                "account_id": int,
                "device_id": int,
                "action": "string",
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
        - 任务会由后台任务处理器自动执行
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        action = data.get('action', 'start')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        if action not in ['start', 'stop']:
            return response_error('action must be "start" or "stop"', 400)
        
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
            task = ListenTask(
                account_id=account_id,
                device_id=account.device_id,
                action=action,
                status='pending'
            )
            db.add(task)
            db.flush()
            db.commit()
            
            return response_success({
                'id': task.id,
                'account_id': task.account_id,
                'device_id': task.device_id,
                'action': task.action,
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None
            }, 'Listen task created', 201)
    except Exception as e:
        return response_error(str(e), 500)


@listen_bp.route('/tasks', methods=['GET'])
@login_required
def get_listen_tasks():
    """
    获取监听任务列表接口
    
    请求方法: GET
    路径: /api/listen/tasks
    认证: 需要登录
    
    查询参数:
        account_id (int, 可选): 账号ID，筛选指定账号的任务
        status (string, 可选): 状态筛选（pending/running/completed/failed）
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": int,
                    "account_id": int,
                    "device_id": int,
                    "action": "string",        # start 或 stop
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
        - action 字段：start（启动监听）、stop（停止监听）
    """
    try:
        account_id = request.args.get('account_id', type=int)
        status = request.args.get('status')
        
        with get_db() as db:
            query = db.query(ListenTask)
            
            if account_id:
                query = query.filter(ListenTask.account_id == account_id)
            
            if status:
                query = query.filter(ListenTask.status == status)
            
            tasks = query.order_by(ListenTask.created_at.desc()).all()
            
            tasks_list = []
            for task in tasks:
                tasks_list.append({
                    'id': task.id,
                    'account_id': task.account_id,
                    'device_id': task.device_id,
                    'action': task.action,
                    'status': task.status,
                    'error_message': task.error_message,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                })
        
        return response_success(tasks_list)
    except Exception as e:
        return response_error(str(e), 500)


@listen_bp.route('/tasks/<int:task_id>', methods=['GET', 'DELETE'])
@login_required
def listen_task_detail(task_id):
    """
    获取或删除监听任务接口
    
    请求方法: GET / DELETE
    路径: /api/listen/tasks/{task_id}
    认证: 需要登录
    
    路径参数:
        task_id (int): 监听任务ID
    
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
                    "action": "string",
                    "status": "string",
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
            task = db.query(ListenTask).filter(ListenTask.id == task_id).first()
            
            if not task:
                return response_error('Task not found', 404)
            
            if request.method == 'GET':
                return response_success({
                    'id': task.id,
                    'account_id': task.account_id,
                    'device_id': task.device_id,
                    'action': task.action,
                    'status': task.status,
                    'error_message': task.error_message,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                })
            
            elif request.method == 'DELETE':
                task_dict = {
                    'task_id': task.id,
                    'status': task.status
                }
                db.delete(task)
                db.commit()
                
                return response_success(task_dict, 'Task deleted successfully')
    except Exception as e:
        return response_error(str(e), 500)


@listen_bp.route('/callback', methods=['POST'])
def listen_callback():
    """
    监听任务回调接口（设备端调用）
    
    请求方法: POST
    路径: /api/listen/callback
    认证: 不需要（设备端调用）
    
    请求体 (JSON):
        {
            "task_id": int,              # 必填，任务ID
            "status": "string",          # 必填，任务状态（pending/running/completed/failed）
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
        - 设备端完成监听任务后调用此接口上报任务状态
        - 如果状态为 completed 或 failed，会自动设置 completed_at 时间
        - 如果状态为 running 且任务未开始，会自动设置 started_at 时间
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
            task = db.query(ListenTask).filter(ListenTask.id == task_id).first()
            
            if not task:
                return response_error('Task not found', 404)
            
            task.status = status
            task.error_message = error_message
            
            if status in ['completed', 'failed', 'running']:
                if status == 'running' and not task.started_at:
                    task.started_at = datetime.now()
                elif status in ['completed', 'failed']:
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

