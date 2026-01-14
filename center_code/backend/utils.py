"""
工具函数
"""
from flask import jsonify, request
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from db import get_db
from models import User


def response_success(data=None, message='success', code=200):
    """统一成功响应格式"""
    return jsonify({
        'code': code,
        'message': message,
        'data': data
    }), code


def response_error(message='error', code=400, data=None):
    """统一错误响应格式"""
    return jsonify({
        'code': code,
        'message': message,
        'data': data
    }), code


def create_access_token(user_id, username, email):
    """创建JWT访问令牌"""
    secret = os.getenv('JWT_SECRET', 'change-me-in-production')
    payload = {
        'sub': str(user_id),
        'username': username,
        'email': email,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, secret, algorithm='HS256')


def decode_access_token(token):
    """解码JWT令牌"""
    secret = os.getenv('JWT_SECRET', 'change-me-in-production')
    return jwt.decode(token, secret, algorithms=['HS256'])


def login_required(f):
    """JWT登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return response_error('缺少访问令牌', 401)

        token = auth_header.split(' ', 1)[1].strip()
        try:
            payload = decode_access_token(token)
        except Exception:
            return response_error('令牌无效或已过期', 401)

        user_id = payload.get('sub')
        if not user_id:
            return response_error('令牌格式错误', 401)
        try:
            user_id = int(user_id)
        except ValueError:
            return response_error('令牌格式错误', 401)

        try:
            with get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return response_error('用户不存在', 401)
        except Exception:
            return response_error('数据库查询失败', 401)

        return f(*args, **kwargs)
    return decorated_function


def has_valid_token():
    """Return True when the request carries a valid JWT."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False

    token = auth_header.split(' ', 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        return False

    user_id = payload.get('sub')
    if not user_id:
        return False
    try:
        user_id = int(user_id)
    except ValueError:
        return False

    try:
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            return user is not None
    except Exception:
        return False


def model_to_dict(model):
    """将SQLAlchemy模型转换为字典"""
    if model is None:
        return None
    
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, __import__('datetime').datetime):
            result[column.name] = value.isoformat() if value else None
        else:
            result[column.name] = value
    return result


def models_to_list(models):
    """将SQLAlchemy模型列表转换为字典列表"""
    return [model_to_dict(model) for model in models]