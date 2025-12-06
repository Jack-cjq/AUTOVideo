"""
认证相关API
"""
from flask import Blueprint, request, session
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error
from models import User
from db import get_db

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录接口
    
    请求方法: POST
    路径: /api/auth/login
    认证: 不需要（登录接口本身）
    
    请求体 (JSON):
        {
            "username": "string",  # 必填，用户名
            "password": "string"   # 必填，密码
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "登录成功",
            "data": {
                "username": "string"  # 登录的用户名
            }
        }
        
        失败 (400/401/500):
        {
            "code": 400/401/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 登录成功后会设置 session，session 有效期为 24 小时
        - 密码验证使用数据库存储的加密密码
    """
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return response_error('用户名和密码不能为空', 400)
        
        with get_db() as db:
            # 从数据库查询用户
            user = db.query(User).filter(User.username == username).first()
            
            if not user:
                return response_error('用户名或密码错误', 401)
            
            # 验证密码
            if not user.check_password(password):
                return response_error('用户名或密码错误', 401)
            
            # 登录成功，设置session
            session.permanent = True  # 设置 session 为永久（使用 PERMANENT_SESSION_LIFETIME）
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user.id
            
            return response_success({'username': username}, '登录成功', 200)
    except Exception as e:
        return response_error(str(e), 500)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    用户登出接口
    
    请求方法: POST
    路径: /api/auth/logout
    认证: 不需要（登出接口本身）
    
    请求体: 无
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "登出成功",
            "data": null
        }
        
        失败 (500):
        {
            "code": 500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 清除所有 session 数据
        - 登出后需要重新登录才能访问需要认证的接口
    """
    try:
        session.clear()
        return response_success(None, '登出成功')
    except Exception as e:
        return response_error(str(e), 500)


@auth_bp.route('/check', methods=['GET'])
def check():
    """
    检查登录状态接口
    
    请求方法: GET
    路径: /api/auth/check
    认证: 不需要（检查接口本身）
    
    查询参数: 无
    
    返回数据:
        已登录 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "logged_in": true,
                "username": "string"  # 当前登录的用户名
            }
        }
        
        未登录 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "logged_in": false
            }
        }
        
        失败 (500):
        {
            "code": 500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 通过检查 session 判断用户是否已登录
        - 前端页面刷新时会调用此接口检查登录状态
    """
    try:
        if session.get('logged_in'):
            return response_success({
                'logged_in': True,
                'username': session.get('username')
            })
        else:
            return response_success({
                'logged_in': False
            })
    except Exception as e:
        return response_error(str(e), 500)

