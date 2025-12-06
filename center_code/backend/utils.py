"""
工具函数
"""
from flask import jsonify, session
from functools import wraps


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


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return response_error('请先登录', 401)
        return f(*args, **kwargs)
    return decorated_function


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

