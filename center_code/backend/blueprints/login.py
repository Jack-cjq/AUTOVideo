"""
登录相关API（二维码等）
"""
from flask import Blueprint, request
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Account
from db import get_db

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
    获取登录二维码接口（占位接口，功能待实现）
    
    请求方法: GET
    路径: /api/login/qrcode
    认证: 需要登录
    
    查询参数:
        account_id (int): 账号ID
    
    返回数据:
        失败 (501):
        {
            "code": 501,
            "message": "QR code generation not implemented yet. Please use login helper page.",
            "data": null
        }
    
    说明:
        - 此接口为占位接口，功能待实现
        - 建议使用登录助手页面（/login-helper）完成账号登录
        - 未来实现时，将使用 Playwright 获取平台登录二维码
    """
    try:
        account_id = request.args.get('account_id', type=int)
        
        # 注意：这里需要实现Playwright获取二维码的逻辑
        # 由于需要异步和浏览器环境，这里只返回占位响应
        # 实际实现需要参考原app.py中的逻辑
        
        return response_error('QR code generation not implemented yet. Please use login helper page.', 501)
    except Exception as e:
        return response_error(str(e), 500)

