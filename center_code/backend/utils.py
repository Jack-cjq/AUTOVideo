"""
工具函数
"""
from flask import jsonify, session
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


def login_required(f):
    """登录验证装饰器
    
    验证用户是否已登录，并检查：
    1. session 中是否存在 logged_in 标志
    2. session 中是否存在 user_id
    3. 数据库中用户是否仍然存在（防止用户被删除后仍能访问）
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查 session 中的登录状态
        if not session.get('logged_in'):
            return response_error('请先登录', 401)
        
        # 检查 session 中是否有 user_id
        user_id = session.get('user_id')
        if not user_id:
            # 如果 session 中有 logged_in 但没有 user_id，说明 session 可能被篡改
            session.clear()  # 清除无效的 session
            return response_error('登录状态无效，请重新登录', 401)
        
        # 验证用户是否仍然存在于数据库中（防止用户被删除后仍能访问）
        try:
            with get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    # 用户不存在，清除 session
                    session.clear()
                    return response_error('用户不存在，请重新登录', 401)
        except Exception as e:
            # 数据库查询失败，但不应该阻止访问（可能是临时数据库问题）
            # 记录错误但继续执行（可以根据需要调整策略）
            pass
        
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

