"""
账号管理API
"""
from flask import Blueprint, request
from datetime import datetime
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required, has_valid_token
from models import Account, Device, Message, VideoTask, ChatTask, ListenTask
from db import get_db

accounts_bp = Blueprint('accounts', __name__, url_prefix='/api/accounts')


@accounts_bp.route('', methods=['POST'])
@login_required
def create_account():
    """
    创建账号绑定接口
    
    请求方法: POST
    路径: /api/accounts
    认证: 需要登录
    
    请求体 (JSON):
        {
            "device_id": "string",      # 必填，设备ID（字符串格式）
            "account_name": "string",   # 必填，账号名称
            "platform": "string"        # 可选，平台类型（douyin/kuaishou/xiaohongshu），默认 douyin
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Account created successfully",
            "data": {
                "id": int,              # 账号ID
                "device_id": int,        # 设备ID（数据库ID）
                "account_name": "string",
                "platform": "string"
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 一个设备可以授权多个账号
        - 账号名称必须唯一
        - 如果设备不存在，返回 404 错误
    """
    try:
        data = request.json
        device_id_str = data.get('device_id')
        account_name = data.get('account_name')
        platform = data.get('platform', 'douyin')
        
        if not device_id_str or not account_name:
            return response_error('device_id and account_name are required', 400)
        
        with get_db() as db:
            # 通过device_id（字符串）查找设备
            device = db.query(Device).filter(Device.device_id == device_id_str).first()
            if not device:
                return response_error('Device not found. Please register device first.', 404)
            
            # 检查账号名称是否已存在（账号名称必须全局唯一）
            existing_account = db.query(Account).filter(Account.account_name == account_name).first()
            if existing_account:
                return response_error('Account name already exists', 400)
            
            # 检查该设备是否已经有相同平台和账号名称的账号（可选：防止重复授权）
            # 注意：这里允许同一设备授权多个账号，只要账号名称不同即可
            
            account = Account(
                device_id=device.id,
                account_name=account_name,
                platform=platform
            )
            db.add(account)
            db.flush()
            db.commit()
            
            return response_success({
                'id': account.id,
                'device_id': account.device_id,
                'account_name': account.account_name,
                'platform': account.platform
            }, 'Account created successfully', 201)
    except Exception as e:
        return response_error(str(e), 500)


@accounts_bp.route('', methods=['GET'])
def get_accounts():
    """
    获取账号列表接口
    
    请求方法: GET
    路径: /api/accounts
    认证: 
        - 如果只查询device_id，不需要登录（设备端调用）
        - 其他情况需要登录（管理端调用）
    
    查询参数:
        device_id (string, 可选): 设备ID，筛选指定设备的账号（设备端使用，不需要登录）
        platform (string, 可选): 平台类型，筛选指定平台的账号（douyin/kuaishou/xiaohongshu）
        login_status (string, 可选): 登录状态，筛选指定状态的账号（logged_in/logged_out）
        search (string, 可选): 搜索关键词，模糊匹配账号名称
        limit (int, 可选): 每页数量，默认 50
        offset (int, 可选): 偏移量，默认 0
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "accounts": [
                    {
                        "id": int,
                        "device_id": int,
                        "account_name": "string",
                        "platform": "string",
                        "login_status": "string",
                        "last_login_time": "string",  # ISO 格式时间或 null
                        "created_at": "string"        # ISO 格式时间或 null
                    }
                ],
                "total": int,    # 总记录数
                "limit": int,    # 每页数量
                "offset": int    # 偏移量
            }
        }
        
        失败 (500):
        {
            "code": 500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果只提供device_id参数，允许设备端调用（不需要登录）
        - 其他情况需要登录认证
        - 支持多条件筛选和分页
        - 结果按创建时间倒序排列
    """
    try:
        device_id = request.args.get('device_id')
        platform = request.args.get('platform')
        login_status = request.args.get('login_status')
        search = request.args.get('search')
        limit = request.args.get('limit', type=int, default=50)
        offset = request.args.get('offset', type=int, default=0)
        
        # 如果只查询device_id，允许设备端调用（不需要登录）
        # 其他情况需要登录
        is_device_query = device_id and not platform and not login_status and not search
        if not is_device_query and not has_valid_token():
            return response_error('请先登录', 401)
        
        with get_db() as db:
            query = db.query(Account)
            
            if device_id:
                device = db.query(Device).filter(Device.device_id == device_id).first()
                if device:
                    query = query.filter(Account.device_id == device.id)
                else:
                    query = query.filter(Account.id == -1)  # 返回空结果
            
            if platform:
                query = query.filter(Account.platform == platform)
            
            if login_status:
                query = query.filter(Account.login_status == login_status)
            
            if search:
                query = query.filter(Account.account_name.like(f'%{search}%'))
            
            total = query.count()
            accounts = query.order_by(Account.created_at.desc()).limit(limit).offset(offset).all()
            
            accounts_list = []
            for account in accounts:
                accounts_list.append({
                    'id': account.id,
                    'device_id': account.device_id,
                    'account_name': account.account_name,
                    'platform': account.platform,
                    'login_status': account.login_status,
                    'last_login_time': account.last_login_time.isoformat() if account.last_login_time else None,
                    'created_at': account.created_at.isoformat() if account.created_at else None
                })
        
        return response_success({
            'accounts': accounts_list,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        return response_error(str(e), 500)


@accounts_bp.route('/<int:account_id>', methods=['GET'])
@login_required
def get_account(account_id):
    """
    获取账号详情接口
    
    请求方法: GET
    路径: /api/accounts/{account_id}
    认证: 需要登录
    
    路径参数:
        account_id (int): 账号ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
                "device_id": int,
                "account_name": "string",
                "platform": "string",
                "login_status": "string",
                "last_login_time": "string"  # ISO 格式时间或 null
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果账号不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return response_error('Account not found', 404)
            
            return response_success({
                'id': account.id,
                'device_id': account.device_id,
                'account_name': account.account_name,
                'platform': account.platform,
                'login_status': account.login_status,
                'last_login_time': account.last_login_time.isoformat() if account.last_login_time else None,
                'cookies': account.cookies  # 返回 cookies，供 service_code 使用
            })
    except Exception as e:
        return response_error(str(e), 500)


@accounts_bp.route('/<int:account_id>/status', methods=['PUT'])
@login_required
def update_account_status(account_id):
    """
    更新账号登录状态接口
    
    请求方法: PUT
    路径: /api/accounts/{account_id}/status
    认证: 需要登录
    
    路径参数:
        account_id (int): 账号ID
    
    请求体 (JSON):
        {
            "status": "string"  # 必填，登录状态（logged_in/logged_out）
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
                "login_status": "string",
                "last_login_time": "string"  # ISO 格式时间或 null
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果状态设置为 logged_in，会自动更新 last_login_time 为当前时间
        - 如果账号不存在，返回 404 错误
    """
    try:
        data = request.json
        login_status = data.get('status')
        
        if not login_status:
            return response_error('status is required', 400)
        
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return response_error('Account not found', 404)
            
            account.login_status = login_status
            if login_status == 'logged_in':
                account.last_login_time = datetime.now()
            account.updated_at = datetime.now()
            db.commit()
            
            return response_success({
                'id': account.id,
                'login_status': account.login_status,
                'last_login_time': account.last_login_time.isoformat() if account.last_login_time else None
            })
    except Exception as e:
        return response_error(str(e), 500)


@accounts_bp.route('/<int:account_id>', methods=['DELETE'])
@login_required
def delete_account(account_id):
    """
    删除账号接口
    
    请求方法: DELETE
    路径: /api/accounts/{account_id}
    认证: 需要登录
    
    路径参数:
        account_id (int): 账号ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Account deleted successfully",
            "data": {
                "account_id": int
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 删除账号时会级联删除相关数据：
          - 该账号的所有消息（Message）
          - 该账号的所有视频任务（VideoTask）
          - 该账号的所有对话任务（ChatTask）
          - 该账号的所有监听任务（ListenTask）
        - 如果账号不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return response_error('Account not found', 404)
            
            # 删除相关数据（级联删除）
            db.query(Message).filter(Message.account_id == account_id).delete()
            db.query(VideoTask).filter(VideoTask.account_id == account_id).delete()
            db.query(ChatTask).filter(ChatTask.account_id == account_id).delete()
            db.query(ListenTask).filter(ListenTask.account_id == account_id).delete()
            
            # 删除账号
            db.delete(account)
            db.commit()
            
            return response_success({'account_id': account_id}, 'Account deleted successfully')
    except Exception as e:
        return response_error(str(e), 500)


@accounts_bp.route('/<int:account_id>/cookies', methods=['GET', 'PUT'])
@login_required
def account_cookies(account_id):
    """
    获取或更新账号Cookies接口
    
    请求方法: GET / PUT
    路径: /api/accounts/{account_id}/cookies
    认证: 需要登录
    
    路径参数:
        account_id (int): 账号ID
    
    GET 请求:
        查询参数: 无
        
        返回数据:
            成功 (200):
            {
                "code": 200,
                "message": "success",
                "data": {
                    "account_id": int,
                    "cookies": "string",        # JSON 字符串或 null
                    "cookie_file_path": "string" # Cookie 文件路径或 null
                }
            }
    
    PUT 请求:
        请求体 (JSON):
        {
            "cookies": "string"  # 可选，Cookies 内容（JSON 字符串）
        }
        
        返回数据:
            成功 (200):
            {
                "code": 200,
                "message": "Cookies updated successfully",
                "data": {
                    "account_id": int,
                    "cookies": "string"
                }
            }
    
    说明:
        - GET: 获取账号的 Cookies 信息
        - PUT: 更新账号的 Cookies
        - 如果账号不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return response_error('Account not found', 404)
            
            if request.method == 'GET':
                return response_success({
                    'account_id': account.id,
                    'cookies': account.cookies,
                    'cookie_file_path': account.cookie_file_path
                })
            
            elif request.method == 'PUT':
                data = request.json
                cookies = data.get('cookies')
                
                if cookies is None:
                    return response_error('cookies is required', 400)
                
                # 验证和解析 cookies
                cookies_json = None
                try:
                    # 如果 cookies 是字符串，尝试解析为 JSON
                    if isinstance(cookies, str):
                        cookies_data = json.loads(cookies)
                        # 验证后重新序列化为字符串（确保格式统一）
                        cookies_json = json.dumps(cookies_data, ensure_ascii=False)
                    elif isinstance(cookies, dict):
                        # 如果已经是字典，直接序列化
                        cookies_json = json.dumps(cookies, ensure_ascii=False)
                    else:
                        return response_error('cookies must be a JSON string or object', 400)
                    
                    # 验证 storage_state 格式（Playwright 格式）
                    cookies_data = json.loads(cookies_json)
                    if not isinstance(cookies_data, dict):
                        return response_error('Cookies must be a dictionary (storage_state format)', 400)
                    
                    # 检查是否有 cookies 或 origins 字段（storage_state 的标准格式）
                    has_cookies = 'cookies' in cookies_data and isinstance(cookies_data.get('cookies'), list)
                    has_origins = 'origins' in cookies_data and isinstance(cookies_data.get('origins'), list)
                    
                    if not (has_cookies or has_origins):
                        # 警告但不阻止，因为可能是不完整的 cookies
                        pass
                    
                except json.JSONDecodeError as e:
                    return response_error(f'Invalid cookies JSON format: {str(e)}', 400)
                except Exception as e:
                    return response_error(f'Error processing cookies: {str(e)}', 400)
                
                # 更新 cookies
                account.cookies = cookies_json
                # 自动更新登录状态为已登录
                account.login_status = 'logged_in'
                # 更新最后登录时间
                account.last_login_time = datetime.now()
                account.updated_at = datetime.now()
                db.commit()
                
                return response_success({
                    'account_id': account.id,
                    'cookies': account.cookies,
                    'login_status': account.login_status,
                    'last_login_time': account.last_login_time.isoformat() if account.last_login_time else None
                }, 'Cookies updated successfully')
    except Exception as e:
        return response_error(str(e), 500)


@accounts_bp.route('/<int:account_id>/cookies/file', methods=['GET'])
@login_required
def get_cookies_file(account_id):
    """
    获取Cookies文件内容接口
    
    请求方法: GET
    路径: /api/accounts/{account_id}/cookies/file
    认证: 需要登录
    
    路径参数:
        account_id (int): 账号ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "account_id": int,
                "cookie_file_path": "string",
                "content": "string"  # 文件内容
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 读取账号关联的 Cookie 文件内容
        - 如果账号不存在、文件路径未设置或文件不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return response_error('Account not found', 404)
            
            if not account.cookie_file_path:
                return response_error('Cookie file path not set', 404)
            
            import os
            if not os.path.exists(account.cookie_file_path):
                return response_error('Cookie file not found', 404)
            
            with open(account.cookie_file_path, 'r', encoding='utf-8') as f:
                cookie_content = f.read()
            
            return response_success({
                'account_id': account.id,
                'cookie_file_path': account.cookie_file_path,
                'content': cookie_content
            })
    except Exception as e:
        return response_error(str(e), 500)

