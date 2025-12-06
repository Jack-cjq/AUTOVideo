"""
消息管理API
"""
from flask import Blueprint, request
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Message, Account
from db import get_db

messages_bp = Blueprint('messages', __name__, url_prefix='/api/messages')


@messages_bp.route('', methods=['GET', 'POST'])
@login_required
def messages():
    """
    获取或创建消息接口
    
    请求方法: GET / POST
    路径: /api/messages
    认证: 需要登录
    
    GET 请求: 获取消息列表
    POST 请求: 创建消息
    
    详见 get_messages() 和 create_message() 函数的注释
    """
    if request.method == 'GET':
        return get_messages()
    elif request.method == 'POST':
        return create_message()


def get_messages():
    """
    获取消息列表
    
    查询参数:
        account_id (int, 可选): 账号ID，筛选指定账号的消息
        user_name (string, 可选): 用户名，筛选指定用户的消息
        limit (int, 可选): 每页数量，默认 100
        offset (int, 可选): 偏移量，默认 0
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "messages": [
                    {
                        "id": int,
                        "account_id": int,
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
    
    说明:
        - 支持按账号和用户名筛选
        - 结果按时间戳和创建时间倒序排列
        - 支持分页
    """
    try:
        account_id = request.args.get('account_id', type=int)
        user_name = request.args.get('user_name')
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        
        with get_db() as db:
            query = db.query(Message)
            
            if account_id:
                query = query.filter(Message.account_id == account_id)
            
            if user_name:
                query = query.filter(Message.user_name == user_name)
            
            total = query.count()
            
            messages = query.order_by(
                Message.timestamp.desc(), 
                Message.created_at.desc()
            ).limit(limit).offset(offset).all()
            
            messages_list = []
            for msg in messages:
                messages_list.append({
                    'id': msg.id,
                    'account_id': msg.account_id,
                    'user_name': msg.user_name,
                    'text': msg.text,
                    'is_me': bool(msg.is_me),
                    'time': msg.message_time,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                    'created_at': msg.created_at.isoformat() if msg.created_at else None
                })
        
        return response_success({
            'messages': messages_list,
            'count': len(messages_list),
            'total': total
        })
    except Exception as e:
        return response_error(str(e), 500)


def create_message():
    """
    创建消息
    
    请求体 (JSON):
        {
            "account_id": int,        # 必填，账号ID
            "user_name": "string",    # 必填，用户名
            "text": "string",         # 必填，消息内容
            "is_me": bool,            # 可选，是否为自己发送的消息，默认 false
            "message_time": "string"  # 可选，消息时间
        }
    
    返回数据:
        成功 (200/201):
        {
            "code": 200/201,
            "message": "Message created" 或 "Message already exists",
            "data": {
                "id": int,
                "account_id": int,
                "user_name": "string",
                "text": "string"
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果消息已存在（相同账号、用户名、内容和时间），返回 200 和现有消息信息
        - 否则创建新消息，返回 201
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        user_name = data.get('user_name')
        text = data.get('text')
        is_me = data.get('is_me', False)
        message_time = data.get('message_time', '')
        
        if not account_id or not user_name or not text:
            return response_error('account_id, user_name and text are required', 400)
        
        with get_db() as db:
            # 检查是否已存在相同的消息（避免重复）
            existing = db.query(Message).filter(
                Message.account_id == account_id,
                Message.user_name == user_name,
                Message.text == text,
                Message.message_time == message_time
            ).first()
            
            if existing:
                return response_success({
                    'id': existing.id,
                    'message': 'Message already exists'
                }, 'Message already exists', 200)
            
            message = Message(
                account_id=account_id,
                user_name=user_name,
                text=text,
                is_me=1 if is_me else 0,
                message_time=message_time
            )
            db.add(message)
            db.flush()
            db.commit()
            
            return response_success({
                'id': message.id,
                'account_id': message.account_id,
                'user_name': message.user_name,
                'text': message.text
            }, 'Message created', 201)
    except Exception as e:
        return response_error(str(e), 500)


@messages_bp.route('/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """
    删除消息接口
    
    请求方法: DELETE
    路径: /api/messages/{message_id}
    认证: 需要登录
    
    路径参数:
        message_id (int): 消息ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Message deleted successfully",
            "data": {
                "message_id": int
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果消息不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            message = db.query(Message).filter(Message.id == message_id).first()
            
            if not message:
                return response_error('Message not found', 404)
            
            db.delete(message)
            db.commit()
            
            return response_success({'message_id': message_id}, 'Message deleted successfully')
    except Exception as e:
        return response_error(str(e), 500)


@messages_bp.route('/clear', methods=['POST'])
@login_required
def clear_messages():
    """
    清空消息接口
    
    请求方法: POST
    路径: /api/messages/clear
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int  # 必填，账号ID
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "{count} messages cleared",
            "data": {
                "account_id": int,
                "deleted_count": int  # 删除的消息数量
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 删除指定账号的所有消息
        - account_id 为必填参数，如果未提供返回 400 错误
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
            
            count = db.query(Message).filter(Message.account_id == account_id).delete()
            db.commit()
            
            return response_success({
                'account_id': account_id,
                'deleted_count': count
            }, f'{count} messages cleared')
    except Exception as e:
        return response_error(str(e), 500)

