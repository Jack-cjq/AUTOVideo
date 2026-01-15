"""
登录相关API（二维码等）
"""
from flask import Blueprint, request
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Account
from db import get_db
from datetime import datetime
from services.login_service import (
    start_login_session_sync,
    check_login_status_sync,
    get_cookies_from_session_sync,
    cleanup_login_session_sync
)

login_bp = Blueprint('login', __name__, url_prefix='/api/login')


@login_bp.route('/start', methods=['POST'])
@login_required
def start_login():
    """
    启动账号登录流程接口
    
    请求方法: POST
    路径: /api/login/start
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int  # 必填，账号ID
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Login helper URL generated",
            "data": {
                "account_id": int,
                "login_url": "string"  # 登录助手页面URL
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 返回登录助手页面的URL，用户可以在该页面完成账号登录
        - 登录助手页面URL格式：/login-helper?account_id={account_id}
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 验证账号是否存在
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
        
        # 返回登录助手页面URL
        login_url = f'/login-helper?account_id={account_id}'
        return response_success({
            'account_id': account_id,
            'login_url': login_url
        }, 'Login helper URL generated', 200)
    except Exception as e:
        return response_error(str(e), 500)


@login_bp.route('/qrcode', methods=['GET'])
@login_required
def get_login_qrcode():
    """
    获取登录二维码接口
    
    请求方法: GET
    路径: /api/login/qrcode
    认证: 需要登录
    
    查询参数:
        account_id (int): 账号ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "二维码获取成功",
            "data": {
                "qrcode": "string",  # base64编码的二维码图片
                "account_id": int
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    """
    try:
        account_id = request.args.get('account_id', type=int)
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 验证账号是否存在
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
            platform = account.platform or 'douyin'
        
        # 启动登录会话并获取二维码
        result = start_login_session_sync(account_id, platform)
        
        if result['success']:
            return response_success({
                'qrcode': result['qrcode'],
                'account_id': account_id
            }, result['message'])
        else:
            return response_error(result['message'], 500)
            
    except Exception as e:
        return response_error(str(e), 500)


@login_bp.route('/status', methods=['GET'])
@login_required
def get_login_status():
    """
    检查登录状态接口
    
    请求方法: GET
    路径: /api/login/status
    认证: 需要登录
    
    查询参数:
        account_id (int): 账号ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "status": "string",  # waiting, scanning, logged_in, failed
                "cookies": object or null,  # 如果已登录，返回cookies
                "message": "string"
            }
        }
    """
    try:
        account_id = request.args.get('account_id', type=int)
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 检查登录状态
        result = check_login_status_sync(account_id)
        
        return response_success({
            'status': result['status'],
            'cookies': result['cookies'],
            'message': result['message']
        })
        
    except Exception as e:
        return response_error(str(e), 500)


@login_bp.route('/complete', methods=['POST'])
@login_required
def complete_login():
    """
    完成登录并保存cookies到数据库
    
    请求方法: POST
    路径: /api/login/complete
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int  # 必填，账号ID
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "登录完成，cookies已保存",
            "data": {
                "account_id": int,
                "login_status": "string"
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 获取cookies
        cookies = get_cookies_from_session_sync(account_id)
        
        if not cookies:
            return response_error('无法获取cookies，请确保已登录', 400)
        
        # 保存cookies到数据库
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
            # 将cookies转换为JSON字符串
            cookies_json = json.dumps(cookies, ensure_ascii=False)
            
            # 更新账号信息
            account.cookies = cookies_json
            account.login_status = 'logged_in'
            account.last_login_time = datetime.now()
            account.updated_at = datetime.now()
            db.commit()
        
        # 清理登录会话
        cleanup_login_session_sync(account_id)
        
        return response_success({
            'account_id': account_id,
            'login_status': 'logged_in'
        }, '登录完成，cookies已保存')
        
    except Exception as e:
        return response_error(str(e), 500)


@login_bp.route('/cancel', methods=['POST'])
@login_required
def cancel_login():
    """
    取消登录并清理会话
    
    请求方法: POST
    路径: /api/login/cancel
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int  # 必填，账号ID
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "登录已取消",
            "data": {
                "account_id": int
            }
        }
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 清理登录会话
        cleanup_login_session_sync(account_id)
        
        return response_success({
            'account_id': account_id
        }, '登录已取消')
        
    except Exception as e:
        return response_error(str(e), 500)

