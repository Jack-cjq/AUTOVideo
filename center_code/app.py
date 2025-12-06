"""
抖音中心管理平台 - Flask应用主文件
轻量级设计，支持设备管理、账号绑定、登录、视频上传和对话功能
"""

import os
import json
import asyncio
import threading
import requests
from datetime import datetime
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3
from contextlib import contextmanager
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')  # 生产环境请修改
CORS(app, supports_credentials=True)  # 支持跨域携带cookie

# 数据库配置
DB_PATH = os.path.join(os.path.dirname(__file__), 'platform.db')

# 注意：不再使用直接HTTP调用模式，统一使用任务队列模式

@contextmanager
def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """初始化数据库"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 设备表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                device_name TEXT,
                ip_address TEXT,
                status TEXT DEFAULT 'offline',
                last_heartbeat DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 账号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                account_name TEXT NOT NULL,
                platform TEXT DEFAULT 'douyin',
                cookie_file_path TEXT,
                cookies TEXT,
                login_status TEXT DEFAULT 'logged_out',
                last_login_time DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
        ''')
        
        # 如果表已存在但没有cookies字段，则添加该字段
        try:
            cursor.execute('ALTER TABLE accounts ADD COLUMN cookies TEXT')
        except sqlite3.OperationalError:
            pass  # 字段已存在，忽略错误
        
        # 视频任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                device_id INTEGER NOT NULL,
                video_url TEXT NOT NULL,
                video_title TEXT,
                video_tags TEXT,
                publish_date DATETIME,
                thumbnail_url TEXT,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
        ''')
        
        # 对话任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                device_id INTEGER NOT NULL,
                target_user TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
        ''')
        
        # 监听任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listen_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                device_id INTEGER NOT NULL,
                action TEXT NOT NULL DEFAULT 'start',
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
        ''')
        
        # 消息表（存储监听到的消息）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                text TEXT NOT NULL,
                is_me INTEGER DEFAULT 0,
                message_time TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        ''')
        
        # 创建索引以提高查询性能
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_account_id ON messages(account_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_name ON messages(user_name)')
        except sqlite3.OperationalError:
            pass  # 索引可能已存在

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

# ==================== 登录验证装饰器 ====================

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return response_error('请先登录', 401)
        return f(*args, **kwargs)
    return decorated_function

# ==================== 前端页面路由 ====================

@app.route('/')
def index():
    """提供前端页面"""
    return send_from_directory('.', 'index.html')

@app.route('/login-helper')
def login_helper():
    """提供登录助手页面"""
    return send_from_directory('.', 'login_helper.html')

@app.route('/api/video/download/<filename>')
def download_video_file(filename):
    """下载视频文件（客户端通过此接口下载）"""
    try:
        # 安全检查：只允许下载uploads目录下的文件
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        file_path = os.path.join(upload_dir, filename)
        
        # 检查文件是否在uploads目录内（防止路径遍历攻击）
        if not os.path.abspath(file_path).startswith(os.path.abspath(upload_dir)):
            return response_error('Invalid file path', 403)
        
        if not os.path.exists(file_path):
            return response_error('File not found', 404)
        
        # 使用send_from_directory安全地发送文件
        return send_from_directory(upload_dir, filename, as_attachment=False)
    except Exception as e:
        return response_error(str(e), 500)

# ==================== 认证API ====================

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """用户登录"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        # 验证账号密码
        if username == 'hbut' and password == 'dydy?123':
            session['logged_in'] = True
            session['username'] = username
            return response_success({'username': username}, '登录成功')
        else:
            return response_error('用户名或密码错误', 401)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """用户登出"""
    try:
        session.clear()
        return response_success(None, '登出成功')
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/auth/check', methods=['GET'])
def auth_check():
    """检查登录状态"""
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

# ==================== 设备管理API ====================

@app.route('/api/devices/register', methods=['POST'])
def register_device():
    """设备注册（如果设备已存在，则更新信息并返回成功）"""
    try:
        data = request.json
        device_id = data.get('device_id')
        device_name = data.get('device_name')
        ip_address = data.get('ip_address')
        
        if not device_id:
            return response_error('device_id is required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 检查设备是否已存在
            cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
            existing_device = cursor.fetchone()
            
            if existing_device:
                # 设备已存在，更新设备信息（名称、IP、状态、心跳时间）
                cursor.execute('''
                    UPDATE devices 
                    SET device_name = ?, 
                        ip_address = ?, 
                        status = 'online', 
                        last_heartbeat = datetime('now', 'localtime'),
                        updated_at = datetime('now', 'localtime')
                    WHERE device_id = ?
                ''', (device_name, ip_address, device_id))
                
                cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
                device = dict(cursor.fetchone())
                
                return response_success(device, 'Device already exists, information updated', 200)
            else:
                # 设备不存在，创建新设备
                cursor.execute('''
                    INSERT INTO devices (device_id, device_name, ip_address, status, last_heartbeat)
                    VALUES (?, ?, ?, 'online', datetime('now', 'localtime'))
                ''', (device_id, device_name, ip_address))
                
                cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
                device = dict(cursor.fetchone())
                
                return response_success(device, 'Device registered successfully', 201)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """获取设备列表（自动检测离线设备）"""
    try:
        from datetime import datetime, timedelta
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM devices ORDER BY created_at DESC')
            devices = []
            
            # 心跳超时时间（秒），超过60秒未收到心跳则认为离线
            HEARTBEAT_TIMEOUT = 60
            
            for row in cursor.fetchall():
                device = dict(row)
                
                # 检查设备是否在线
                if device.get('last_heartbeat'):
                    try:
                        # SQLite返回的时间格式可能是字符串，需要解析
                        heartbeat_str = device['last_heartbeat']
                        if isinstance(heartbeat_str, str):
                            # 尝试多种时间格式
                            try:
                                # ISO格式: 2024-01-01T10:00:00 或 2024-01-01T10:00:00.000000
                                if 'T' in heartbeat_str:
                                    last_heartbeat = datetime.fromisoformat(heartbeat_str.replace('Z', '+00:00'))
                                    if last_heartbeat.tzinfo:
                                        # 转换为本地时间
                                        last_heartbeat = last_heartbeat.replace(tzinfo=None)
                                else:
                                    # SQLite格式: 2024-01-01 10:00:00
                                    last_heartbeat = datetime.strptime(heartbeat_str, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                # 尝试带微秒的格式
                                try:
                                    last_heartbeat = datetime.strptime(heartbeat_str, '%Y-%m-%d %H:%M:%S.%f')
                                except ValueError:
                                    # 如果都失败，使用当前时间减去超时时间（强制离线）
                                    last_heartbeat = datetime.now() - timedelta(seconds=HEARTBEAT_TIMEOUT + 1)
                        else:
                            last_heartbeat = datetime.now() - timedelta(seconds=HEARTBEAT_TIMEOUT + 1)
                        
                        now = datetime.now()
                        time_diff = (now - last_heartbeat).total_seconds()
                        
                        # 调试日志（可选）
                        # print(f"Device {device['device_id']}: last_heartbeat={last_heartbeat}, now={now}, diff={time_diff}s")
                        
                        # 如果超过超时时间未收到心跳，自动设置为离线
                        if time_diff > HEARTBEAT_TIMEOUT:
                            if device['status'] != 'offline':
                                cursor.execute('''
                                    UPDATE devices 
                                    SET status = 'offline', updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (device['id'],))
                                device['status'] = 'offline'
                        elif time_diff <= HEARTBEAT_TIMEOUT:
                            # 如果时间差在超时范围内，确保状态是在线
                            if device['status'] != 'online':
                                cursor.execute('''
                                    UPDATE devices 
                                    SET status = 'online', updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (device['id'],))
                                device['status'] = 'online'
                    except Exception as e:
                        # 解析时间失败，设置为离线
                        if device['status'] != 'offline':
                            cursor.execute('''
                                UPDATE devices 
                                SET status = 'offline', updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (device['id'],))
                            device['status'] = 'offline'
                else:
                    # 没有心跳记录，设置为离线
                    if device['status'] != 'offline':
                        cursor.execute('''
                            UPDATE devices 
                            SET status = 'offline', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (device['id'],))
                        device['status'] = 'offline'
                
                devices.append(device)
            
            conn.commit()
        
        return response_success(devices)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    """获取设备详情"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
            device = cursor.fetchone()
            
            if not device:
                return response_error('Device not found', 404)
            
            device = dict(device)
        
        return response_success(device)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/devices/<device_id>/heartbeat', methods=['POST'])
def device_heartbeat(device_id):
    """设备心跳（device_id是字符串标识）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE devices 
                SET status = 'online', last_heartbeat = datetime('now', 'localtime'), updated_at = datetime('now', 'localtime')
                WHERE device_id = ?
            ''', (device_id,))
            
            if cursor.rowcount == 0:
                return response_error('Device not found', 404)
            
            cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
            device = dict(cursor.fetchone())
        
        return response_success(device)
    except Exception as e:
        return response_error(str(e), 500)

# ==================== 账号管理API ====================

@app.route('/api/accounts', methods=['POST'])
def create_account():
    """创建账号绑定（通过device_id字符串自动关联到客户端）"""
    try:
        data = request.json
        device_id_str = data.get('device_id')  # 设备的字符串ID
        account_name = data.get('account_name')
        platform = data.get('platform', 'douyin')
        
        if not device_id_str or not account_name:
            return response_error('device_id and account_name are required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 通过device_id（字符串）查找设备
            cursor.execute('SELECT id FROM devices WHERE device_id = ?', (device_id_str,))
            device_row = cursor.fetchone()
            if not device_row:
                return response_error('Device not found. Please register device first.', 404)
            
            device_db_id = device_row[0]
            
            # 检查该设备是否已经有账号（一对一关系）
            cursor.execute('SELECT id FROM accounts WHERE device_id = ?', (device_db_id,))
            existing_account = cursor.fetchone()
            if existing_account:
                return response_error('This device already has an account. One device can only have one account.', 400)
            
            # 检查账号名称是否已存在
            cursor.execute('SELECT id FROM accounts WHERE account_name = ?', (account_name,))
            if cursor.fetchone():
                return response_error('Account name already exists', 400)
            
            cursor.execute('''
                INSERT INTO accounts (device_id, account_name, platform)
                VALUES (?, ?, ?)
            ''', (device_db_id, account_name, platform))
            
            account_id = cursor.lastrowid
            cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
            account = dict(cursor.fetchone())
        
        return response_success(account, 'Account created successfully', 201)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """获取账号列表"""
    try:
        device_id = request.args.get('device_id')  # 设备的字符串ID
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            if device_id:
                # 通过device_id（字符串）查找账号
                cursor.execute('''
                    SELECT a.* FROM accounts a
                    JOIN devices d ON a.device_id = d.id
                    WHERE d.device_id = ?
                    ORDER BY a.created_at DESC
                ''', (device_id,))
            else:
                cursor.execute('SELECT * FROM accounts ORDER BY created_at DESC')
            
            accounts = [dict(row) for row in cursor.fetchall()]
        
        return response_success(accounts)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/accounts/<int:account_id>', methods=['GET'])
def get_account(account_id):
    """获取账号详情"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
            account = cursor.fetchone()
            
            if not account:
                return response_error('Account not found', 404)
            
            account = dict(account)
        
        return response_success(account)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/accounts/<int:account_id>/status', methods=['PUT'])
def update_account_status(account_id):
    """更新账号状态"""
    try:
        data = request.json
        login_status = data.get('login_status')
        
        if not login_status:
            return response_error('login_status is required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE accounts 
                SET login_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (login_status, account_id))
            
            if cursor.rowcount == 0:
                return response_error('Account not found', 404)
            
            cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
            account = dict(cursor.fetchone())
        
        return response_success(account)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
@login_required
def delete_account(account_id):
    """删除账号（级联删除相关数据）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 检查账号是否存在
            cursor.execute('SELECT id FROM accounts WHERE id = ?', (account_id,))
            account = cursor.fetchone()
            if not account:
                return response_error('Account not found', 404)
            
            # 删除相关数据（级联删除）
            # 1. 删除消息
            cursor.execute('DELETE FROM messages WHERE account_id = ?', (account_id,))
            
            # 2. 删除视频任务
            cursor.execute('DELETE FROM video_tasks WHERE account_id = ?', (account_id,))
            
            # 3. 删除对话任务
            cursor.execute('DELETE FROM chat_tasks WHERE account_id = ?', (account_id,))
            
            # 4. 删除账号
            cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
            
            if cursor.rowcount == 0:
                return response_error('Account not found', 404)
        
        return response_success({'account_id': account_id}, 'Account deleted successfully')
    except Exception as e:
        return response_error(str(e), 500)

# ==================== 登录API ====================

@app.route('/api/login/start', methods=['POST'])
@login_required
def start_login():
    """启动登录流程（返回登录助手页面URL）"""
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 检查账号是否存在
            cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
            account = cursor.fetchone()
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

# 注意：服务器端登录功能已移除，改为客户端浏览器登录
# 登录流程现在通过 login_helper.html 页面在客户端浏览器中完成

# ==================== 登录二维码API ====================

@app.route('/api/login/qrcode', methods=['GET'])
@login_required
def get_login_qrcode():
    """获取抖音登录二维码（使用Playwright）"""
    import traceback
    try:
        account_id = request.args.get('account_id', type=int)
        print(f"[QRCODE] 收到获取二维码请求，account_id={account_id}")
        
        if not account_id:
            print("[QRCODE] 错误: account_id 缺失")
            return response_error('account_id is required', 400)
        
        # 检查账号是否存在
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
            account = cursor.fetchone()
            if not account:
                print(f"[QRCODE] 错误: 账号 {account_id} 不存在")
                return response_error('Account not found', 404)
        
        print(f"[QRCODE] 开始获取二维码，账号ID={account_id}")
        
        # 在后台线程中运行 Playwright，避免触发 Flask 重载器
        import queue
        result_queue = queue.Queue()
        error_queue = queue.Queue()
        
        def run_playwright():
            """在后台线程中运行 Playwright"""
            try:
                print("[QRCODE] 启动 Playwright...")
                # 在新的事件循环中运行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    qrcode_data = loop.run_until_complete(asyncio.wait_for(_get_douyin_qrcode(account_id), timeout=60.0))
                    result_queue.put(qrcode_data)
                finally:
                    loop.close()
            except Exception as e:
                error_queue.put(e)
        
        # 启动后台线程
        playwright_thread = threading.Thread(target=run_playwright, daemon=True)
        playwright_thread.start()
        
        # 等待结果（最多60秒）
        try:
            # 等待线程完成或超时
            playwright_thread.join(timeout=65.0)
            
            if not error_queue.empty():
                e = error_queue.get()
                raise e
            
            if not result_queue.empty():
                qrcode_data = result_queue.get()
                print(f"[QRCODE] 获取二维码完成，结果: {'成功' if qrcode_data else '失败'}")
                
                if qrcode_data:
                    return response_success({
                        'account_id': account_id,
                        'qrcode': qrcode_data,
                        'message': '请使用抖音APP扫码登录'
                    })
                else:
                    print("[QRCODE] 错误: 无法获取二维码数据")
                    return response_error('无法获取二维码，请稍后重试', 500)
            else:
                print("[QRCODE] 错误: 获取二维码超时或线程未完成")
                return response_error('获取二维码超时（60秒），请检查网络连接或稍后重试', 500)
                
        except asyncio.TimeoutError:
            print("[QRCODE] 错误: 获取二维码超时")
            return response_error('获取二维码超时（60秒），请检查网络连接或稍后重试', 500)
        except ImportError as e:
            print(f"[QRCODE] 错误: ImportError - {e}")
            if 'playwright' in str(e).lower():
                return response_error('Playwright未安装，请运行: pip install playwright && playwright install chromium', 500)
            raise
        except Exception as e:
            error_msg = str(e)
            print(f"[QRCODE] 错误: {error_msg}")
            print(f"[QRCODE] 错误堆栈: {traceback.format_exc()}")
            if 'Playwright' in error_msg or 'chromium' in error_msg.lower() or 'executable' in error_msg.lower():
                return response_error('Playwright或Chrome配置错误，请检查：1) Playwright已安装 2) Chrome浏览器路径正确', 500)
            return response_error(f'获取二维码失败: {error_msg}', 500)
            
    except Exception as e:
        print(f"[QRCODE] 最外层异常: {e}")
        print(f"[QRCODE] 最外层异常堆栈: {traceback.format_exc()}")
        return response_error(str(e), 500)

# 全局变量：存储每个账号的登录会话（用于等待登录完成）
_login_sessions = {}
_login_sessions_lock = threading.Lock()

async def _get_douyin_qrcode(account_id=None):
    """
    使用Playwright获取抖音登录二维码
    返回base64格式的二维码图片
    如果提供了account_id，会保持浏览器打开，等待登录完成
    """
    try:
        from playwright.async_api import async_playwright
        import base64
        
        # Chrome配置（从环境变量或使用默认值）
        chrome_path = os.getenv('LOCAL_CHROME_PATH', None)
        headless = os.getenv('LOCAL_CHROME_HEADLESS', 'False').lower() == 'true'
        
        browser_options = {
            'headless': headless
        }
        if chrome_path and os.path.exists(chrome_path):
            browser_options['executable_path'] = chrome_path
        
        async with async_playwright() as playwright:
            # 启动浏览器
            browser = await playwright.chromium.launch(**browser_options)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # 访问抖音创作者中心登录页面
                await page.goto("https://creator.douyin.com/", wait_until="domcontentloaded", timeout=30000)
                
                # 等待页面加载完成
                await page.wait_for_load_state("networkidle", timeout=15000)
                
                # 等待一下，确保登录弹窗或二维码已加载
                await asyncio.sleep(2)
                
                # 尝试多种方式获取二维码
                qrcode_base64 = None
                
                # 先尝试等待二维码元素出现（最多等待10秒）
                try:
                    # 优先等待抖音的二维码容器或图片
                    await page.wait_for_selector('div[class*="qrcode"] img, img[class*="qrcode"], img[alt*="二维码"], img[aria-label*="二维码"]', timeout=10000)
                    print("[QRCODE] 二维码元素已出现")
                except:
                    print("[QRCODE] 等待二维码元素超时，继续尝试查找...")
                    pass
                
                # 方式1: 查找二维码图片元素（img标签）
                # 抖音登录页面的二维码选择器（根据实际HTML结构优化）
                qrcode_selectors = [
                    # 最精确的选择器（根据你提供的HTML结构）
                    'div.qrcode-vz0gH7 img',
                    'div[class*="qrcode-vz0gH7"] img',
                    'img.qrcode_img-NPVTJs',
                    'img[class*="qrcode_img"]',
                    # 通用二维码选择器
                    'img[alt*="二维码"]',
                    'img[alt*="QR"]',
                    'img[aria-label*="二维码"]',
                    'img[aria-label*="QR"]',
                    'img.qrcode',
                    '.qrcode img',
                    'canvas.qrcode',
                    'img[src*="qrcode"]',
                    'img[src*="QR"]',
                    # 抖音可能的二维码选择器
                    'div[class*="qrcode"] img',
                    'div[class*="QR"] img',
                    'img[class*="qrcode"]',
                    'img[class*="QR"]',
                    # 抖音登录弹窗中的二维码
                    '.login-modal img',
                    '.login-dialog img',
                    '[class*="login"] [class*="qrcode"] img',
                    '[class*="scan"] img',
                    # 更通用的选择器
                    'img[width="200"]',  # 二维码通常是200x200
                    'img[height="200"]',
                ]
                
                for selector in qrcode_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            # 如果是img标签，获取src
                            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                            if tag_name == 'img':
                                src = await element.get_attribute('src')
                                print(f"[QRCODE] 找到图片元素，src类型: {src[:50] if src else 'None'}...")
                                if src and src.startswith('data:image'):
                                    # 已经是base64格式，直接使用
                                    qrcode_base64 = src
                                    print("[QRCODE] 成功获取base64格式的二维码")
                                    break
                                elif src and (src.startswith('http') or src.startswith('//')):
                                    # 是URL，需要截图
                                    print("[QRCODE] 二维码是URL格式，进行截图...")
                                    screenshot = await element.screenshot()
                                    qrcode_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode('utf-8')}"
                                    print("[QRCODE] 截图完成，转换为base64")
                                    break
                                elif not src:
                                    # 没有src，尝试截图元素本身
                                    print("[QRCODE] 图片没有src，尝试截图元素...")
                                    screenshot = await element.screenshot()
                                    qrcode_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode('utf-8')}"
                                    print("[QRCODE] 元素截图完成")
                                    break
                            elif tag_name == 'canvas':
                                # canvas元素，转换为base64
                                print("[QRCODE] 找到canvas元素，转换为base64...")
                                canvas_data = await element.evaluate('''
                                    (canvas) => {
                                        return canvas.toDataURL('image/png');
                                    }
                                ''')
                                if canvas_data:
                                    qrcode_base64 = canvas_data
                                    print("[QRCODE] Canvas转换完成")
                                    break
                    except Exception as e:
                        print(f"[QRCODE] 选择器 {selector} 失败: {e}")
                        continue
                
                # 方式2: 如果没找到，尝试查找包含二维码的容器并截图
                if not qrcode_base64:
                    try:
                        # 查找可能的二维码容器
                        container_selectors = [
                            'div[class*="qrcode"]',
                            'div[class*="QR"]',
                            'div[class*="login"]',
                            'div[class*="scan"]',
                        ]
                        
                        for selector in container_selectors:
                            try:
                                container = await page.query_selector(selector)
                                if container:
                                    # 截图容器
                                    screenshot = await container.screenshot()
                                    qrcode_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode('utf-8')}"
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass
                
                # 方式3: 如果还是没找到，尝试执行JavaScript获取二维码
                if not qrcode_base64:
                    try:
                        # 尝试在页面中查找二维码相关的元素
                        qrcode_data = await page.evaluate('''
                            () => {
                                // 查找所有img标签
                                const imgs = document.querySelectorAll('img');
                                for (let img of imgs) {
                                    const src = img.src || img.getAttribute('src');
                                    const alt = img.alt || '';
                                    if (src && (src.includes('qrcode') || src.includes('QR') || 
                                        alt.includes('二维码') || alt.includes('QR'))) {
                                        if (src.startsWith('data:')) {
                                            return src;
                                        }
                                    }
                                }
                                
                                // 查找canvas
                                const canvases = document.querySelectorAll('canvas');
                                for (let canvas of canvases) {
                                    try {
                                        return canvas.toDataURL('image/png');
                                    } catch(e) {}
                                }
                                
                                return null;
                            }
                        ''')
                        
                        if qrcode_data:
                            qrcode_base64 = qrcode_data
                    except Exception:
                        pass
                
                # 如果提供了account_id，保持浏览器打开，等待登录完成
                if account_id:
                    print(f"[QRCODE] 保持浏览器打开，等待账号 {account_id} 登录完成...")
                    try:
                        # 等待登录成功（检测URL变化或特定元素出现）
                        # 登录成功后，URL会变化或出现创作者中心的内容
                        import time
                        login_success = False
                        max_wait_time = 300  # 最多等待5分钟
                        start_time = time.time()
                        
                        while (time.time() - start_time) < max_wait_time:
                            current_url = page.url
                            print(f"[QRCODE] 当前URL: {current_url}")
                            
                            # 检查是否已经登录成功（URL包含creator.douyin.com且不是登录页）
                            if 'creator.douyin.com' in current_url and 'login' not in current_url.lower():
                                # 检查是否有登录成功的标志（比如创作者中心的内容）
                                try:
                                    # 等待页面加载完成
                                    await page.wait_for_load_state("networkidle", timeout=5000)
                                    
                                    # 检查是否有创作者中心的内容（比如"内容管理"、"数据"等）
                                    page_content = await page.content()
                                    if '内容管理' in page_content or '数据' in page_content or 'creator-micro' in current_url:
                                        print("[QRCODE] 检测到登录成功！")
                                        login_success = True
                                        break
                                except:
                                    pass
                            
                            # 等待1秒后再次检查
                            await asyncio.sleep(1)
                        
                        if login_success:
                            print(f"[QRCODE] 登录成功，开始保存cookies...")
                            # 获取cookies
                            cookies = await context.cookies()
                            
                            # 获取localStorage和sessionStorage
                            storage_state = await context.storage_state()
                            
                            # 构建cookies JSON（Playwright格式）
                            cookies_data = {
                                'cookies': storage_state.get('cookies', []),
                                'origins': storage_state.get('origins', [])
                            }
                            
                            # 保存cookies到数据库
                            cookies_json = json.dumps(cookies_data, ensure_ascii=False)
                            with get_db() as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    UPDATE accounts 
                                    SET cookies = ?, 
                                        login_status = 'logged_in',
                                        last_login_time = CURRENT_TIMESTAMP,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (cookies_json, account_id))
                                conn.commit()
                            
                            print(f"[QRCODE] Cookies已保存到数据库，账号ID={account_id}")
                        else:
                            print(f"[QRCODE] 等待登录超时（{max_wait_time}秒）")
                    except Exception as e:
                        print(f"[QRCODE] 等待登录过程中出错: {e}")
                        import traceback
                        traceback.print_exc()
                
                return qrcode_base64
                
            finally:
                # 关闭浏览器
                await context.close()
                await browser.close()
                
    except ImportError:
        # Playwright未安装
        raise Exception("Playwright未安装，请运行: pip install playwright && playwright install chromium")
    except Exception as e:
        raise Exception(f"获取二维码时出错: {str(e)}")

# ==================== 视频上传API ====================

@app.route('/api/video/upload', methods=['POST'])
def create_video_task():
    """创建视频上传任务（通过account_id自动获取device_id）"""
    try:
        data = request.json
        account_id = data.get('account_id')
        video_url = data.get('video_url')
        video_title = data.get('video_title')
        video_tags = data.get('video_tags')
        publish_date = data.get('publish_date')
        thumbnail_url = data.get('thumbnail_url')
        
        if not account_id or not video_url:
            return response_error('account_id and video_url are required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 检查账号是否存在，并获取关联的device_id
            cursor.execute('SELECT id, device_id FROM accounts WHERE id = ?', (account_id,))
            account_row = cursor.fetchone()
            if not account_row:
                return response_error('Account not found', 404)
            
            device_db_id = account_row[1]  # 从账号获取device_id
            
            video_tags_json = json.dumps(video_tags) if video_tags else None
            
            cursor.execute('''
                INSERT INTO video_tasks 
                (account_id, device_id, video_url, video_title, video_tags, publish_date, thumbnail_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (account_id, device_db_id, video_url, video_title, video_tags_json, publish_date, thumbnail_url))
            
            task_id = cursor.lastrowid
            cursor.execute('SELECT * FROM video_tasks WHERE id = ?', (task_id,))
            task = dict(cursor.fetchone())
        
        return response_success(task, 'Video task created', 201)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/video/tasks', methods=['GET'])
def get_video_tasks():
    """获取视频任务列表（通过account_id查询）"""
    try:
        account_id = request.args.get('account_id', type=int)
        status = request.args.get('status')
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM video_tasks WHERE 1=1'
            params = []
            
            if account_id:
                # 通过account_id查询任务
                query += ' AND account_id = ?'
                params.append(account_id)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC'
            cursor.execute(query, params)
            tasks = [dict(row) for row in cursor.fetchall()]
        
        return response_success(tasks)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/video/tasks/<int:task_id>', methods=['GET', 'DELETE'])
@login_required
def video_task_detail(task_id):
    """获取或删除视频任务"""
    if request.method == 'GET':
        """获取视频任务详情"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM video_tasks WHERE id = ?', (task_id,))
                task = cursor.fetchone()
                
                if not task:
                    return response_error('Task not found', 404)
                
                task = dict(task)
            
            return response_success(task)
        except Exception as e:
            return response_error(str(e), 500)
    
    elif request.method == 'DELETE':
        """删除视频任务"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # 检查任务是否存在
                cursor.execute('SELECT * FROM video_tasks WHERE id = ?', (task_id,))
                task = cursor.fetchone()
                
                if not task:
                    return response_error('Task not found', 404)
                
                task_dict = dict(task)
                
                # 删除任务
                cursor.execute('DELETE FROM video_tasks WHERE id = ?', (task_id,))
                
            return response_success({
                'task_id': task_id,
                'video_title': task_dict.get('video_title'),
                'status': task_dict.get('status')
            }, 'Task deleted successfully')
        except Exception as e:
            return response_error(str(e), 500)

@app.route('/api/video/callback', methods=['POST'])
def video_callback():
    """视频上传回调（由social-auto-upload服务调用）"""
    try:
        data = request.json
        task_id = data.get('task_id')
        status = data.get('status')
        progress = data.get('progress', 0)
        error_message = data.get('error_message')
        
        if not task_id or not status:
            return response_error('task_id and status are required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 根据状态设置不同的时间戳
            if status == 'completed':
                cursor.execute('''
                    UPDATE video_tasks 
                    SET status = ?, progress = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, progress, error_message, task_id))
            elif status == 'failed':
                cursor.execute('''
                    UPDATE video_tasks 
                    SET status = ?, progress = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, progress, error_message, task_id))
            else:
                # 其他状态（如uploading）
                cursor.execute('''
                    UPDATE video_tasks 
                    SET status = ?, progress = ?, error_message = ?, started_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, progress, error_message, task_id))
            
            if cursor.rowcount == 0:
                return response_error('Task not found', 404)
            
            cursor.execute('SELECT * FROM video_tasks WHERE id = ?', (task_id,))
            task = dict(cursor.fetchone())
        
        return response_success(task)
    except Exception as e:
        return response_error(str(e), 500)

# ==================== 对话功能API ====================

@app.route('/api/chat/send', methods=['POST'])
def create_chat_task():
    """创建对话发送任务（通过account_id自动获取device_id）"""
    try:
        data = request.json
        account_id = data.get('account_id')
        target_user = data.get('target_user')
        message = data.get('message')
        
        if not account_id or not target_user or not message:
            return response_error('account_id, target_user and message are required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 检查账号是否存在，并获取关联的device_id
            cursor.execute('SELECT id, device_id FROM accounts WHERE id = ?', (account_id,))
            account_row = cursor.fetchone()
            if not account_row:
                return response_error('Account not found', 404)
            
            device_db_id = account_row[1]  # 从账号获取device_id
            
            cursor.execute('''
                INSERT INTO chat_tasks (account_id, device_id, target_user, message, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (account_id, device_db_id, target_user, message))
            
            task_id = cursor.lastrowid
            cursor.execute('SELECT * FROM chat_tasks WHERE id = ?', (task_id,))
            task = dict(cursor.fetchone())
        
        return response_success(task, 'Chat task created', 201)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/chat/tasks', methods=['GET'])
def get_chat_tasks():
    """获取对话任务列表（通过account_id查询）"""
    try:
        account_id = request.args.get('account_id', type=int)
        status = request.args.get('status')
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM chat_tasks WHERE 1=1'
            params = []
            
            if account_id:
                # 通过account_id查询任务
                query += ' AND account_id = ?'
                params.append(account_id)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC'
            cursor.execute(query, params)
            tasks = [dict(row) for row in cursor.fetchall()]
        
        return response_success(tasks)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/chat/tasks/<int:task_id>', methods=['GET'])
def get_chat_task(task_id):
    """获取对话任务详情"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chat_tasks WHERE id = ?', (task_id,))
            task = cursor.fetchone()
            
            if not task:
                return response_error('Task not found', 404)
            
            task = dict(task)
        
        return response_success(task)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/chat/callback', methods=['POST'])
def chat_callback():
    """对话回调"""
    try:
        data = request.json
        task_id = data.get('task_id')
        status = data.get('status')
        error_message = data.get('error_message')
        
        if not task_id or not status:
            return response_error('task_id and status are required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chat_tasks 
                SET status = ?, error_message = ?, started_at = CURRENT_TIMESTAMP, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, error_message, task_id))
            
            if cursor.rowcount == 0:
                return response_error('Task not found', 404)
            
            cursor.execute('SELECT * FROM chat_tasks WHERE id = ?', (task_id,))
            task = dict(cursor.fetchone())
        
        return response_success(task)
    except Exception as e:
        return response_error(str(e), 500)

# ==================== 监听任务API ====================

@app.route('/api/listen/tasks', methods=['GET'])
def get_listen_tasks():
    """获取监听任务列表（通过account_id查询）"""
    try:
        account_id = request.args.get('account_id', type=int)
        status = request.args.get('status')
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM listen_tasks WHERE 1=1'
            params = []
            
            if account_id:
                # 通过account_id查询任务
                query += ' AND account_id = ?'
                params.append(account_id)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC'
            cursor.execute(query, params)
            tasks = [dict(row) for row in cursor.fetchall()]
        
        return response_success(tasks)
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/listen/tasks/<int:task_id>', methods=['GET', 'DELETE'])
@login_required
def listen_task_detail(task_id):
    """获取或删除监听任务"""
    if request.method == 'GET':
        """获取监听任务详情"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM listen_tasks WHERE id = ?', (task_id,))
                task = cursor.fetchone()
                
                if not task:
                    return response_error('Task not found', 404)
                
                task = dict(task)
            
            return response_success(task)
        except Exception as e:
            return response_error(str(e), 500)
    
    elif request.method == 'DELETE':
        """删除监听任务"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # 检查任务是否存在
                cursor.execute('SELECT * FROM listen_tasks WHERE id = ?', (task_id,))
                task = cursor.fetchone()
                
                if not task:
                    return response_error('Task not found', 404)
                
                task_dict = dict(task)
                
                # 删除任务
                cursor.execute('DELETE FROM listen_tasks WHERE id = ?', (task_id,))
                
            return response_success({
                'task_id': task_id,
                'action': task_dict.get('action'),
                'status': task_dict.get('status')
            }, 'Task deleted successfully')
        except Exception as e:
            return response_error(str(e), 500)

@app.route('/api/listen/callback', methods=['POST'])
def listen_callback():
    """监听任务回调"""
    try:
        data = request.json
        if not data:
            return response_error('Request body is required', 400)
        
        task_id = data.get('task_id')
        status = data.get('status')
        error_message = data.get('error_message')
        
        # 添加日志记录
        import logging
        logging.info(f"Listen callback received: task_id={task_id}, status={status}, error_message={error_message}")
        
        if not task_id or not status:
            return response_error('task_id and status are required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 根据状态设置不同的时间戳
            if status == 'running':
                # 监听启动成功，设置为运行中
                cursor.execute('''
                    UPDATE listen_tasks 
                    SET status = ?, error_message = ?, started_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, error_message, task_id))
            elif status in ('completed', 'stopped'):
                # 监听停止
                cursor.execute('''
                    UPDATE listen_tasks 
                    SET status = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, error_message, task_id))
            else:
                # 其他状态（如failed）
                cursor.execute('''
                    UPDATE listen_tasks 
                    SET status = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, error_message, task_id))
            
            if cursor.rowcount == 0:
                logging.warning(f"Listen task {task_id} not found in database")
                return response_error('Task not found', 404)
            
            cursor.execute('SELECT * FROM listen_tasks WHERE id = ?', (task_id,))
            task = dict(cursor.fetchone())
            
            logging.info(f"Listen task {task_id} status updated to {status}")
        
        return response_success(task)
    except Exception as e:
        import logging
        logging.error(f"Listen callback error: {e}", exc_info=True)
        return response_error(str(e), 500)

# ==================== 健康检查和统计API ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM devices')
            device_count = cursor.fetchone()[0]
        
        return response_success({
            'status': 'healthy',
            'devices': device_count
        })
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/accounts/<int:account_id>/cookies', methods=['GET', 'PUT'])
def account_cookies(account_id):
    """获取或更新账号的cookies"""
    if request.method == 'GET':
        """获取账号的cookies（用于其他模块）"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT cookies FROM accounts WHERE id = ?', (account_id,))
                account = cursor.fetchone()
                
                if not account:
                    return response_error('Account not found', 404)
                
                cookies_json = account[0]
                if not cookies_json:
                    return response_error('No cookies found for this account', 404)
                
                cookies_data = json.loads(cookies_json)
                return response_success(cookies_data)
        except Exception as e:
            return response_error(str(e), 500)
    
    elif request.method == 'PUT':
        """更新账号的cookies（用于social-auto-upload服务更新cookie）"""
        try:
            data = request.json
            cookies_json = data.get('cookies')
            
            if not cookies_json:
                return response_error('cookies is required', 400)
            
            # 如果cookies_json是字典，转换为JSON字符串
            if isinstance(cookies_json, dict):
                cookies_json = json.dumps(cookies_json, ensure_ascii=False)
            elif isinstance(cookies_json, str):
                # 验证JSON格式
                try:
                    json.loads(cookies_json)
                except json.JSONDecodeError:
                    return response_error('Invalid cookies JSON format', 400)
            
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE accounts 
                    SET cookies = ?, 
                        login_status = 'logged_in',
                        last_login_time = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (cookies_json, account_id))
                
                if cursor.rowcount == 0:
                    return response_error('Account not found', 404)
            
            return response_success({'account_id': account_id}, 'Cookies updated successfully')
        except Exception as e:
            return response_error(str(e), 500)

@app.route('/api/accounts/<int:account_id>/cookies/file', methods=['GET'])
def get_account_cookies_file(account_id):
    """获取账号的cookies并转换为文件格式（兼容现有代码）"""
    try:
        import tempfile
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT cookies FROM accounts WHERE id = ?', (account_id,))
            account = cursor.fetchone()
            
            if not account:
                return response_error('Account not found', 404)
            
            cookies_json = account[0]
            if not cookies_json:
                return response_error('No cookies found for this account', 404)
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            temp_file.write(cookies_json)
            temp_file.close()
            
            return response_success({
                'file_path': temp_file.name,
                'cookies': json.loads(cookies_json)
            })
    except Exception as e:
        return response_error(str(e), 500)

# ==================== Social Auto Upload 服务调用API ====================

@app.route('/api/social/upload', methods=['POST'])
def social_upload_video():
    """上传视频（使用任务队列模式）"""
    try:
        # 检查是否有文件
        if 'video' not in request.files:
            return response_error('No video file provided', 400)
        
        file = request.files['video']
        account_id = request.form.get('account_id', type=int)
        title = request.form.get('title', '').strip()  # 去除首尾空格
        tags = request.form.get('tags', '').strip()  # 去除首尾空格
        publish_date = request.form.get('publish_date')
        thumbnail = request.files.get('thumbnail')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 任务队列模式：保存文件并创建任务
        from werkzeug.utils import secure_filename
        
        # 创建临时目录保存上传的文件
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存视频文件
        filename = secure_filename(file.filename)
        video_path = os.path.join(upload_dir, f"{account_id}_{int(datetime.now().timestamp())}_{filename}")
        file.save(video_path)
        
        # 保存缩略图（如果有）
        thumbnail_path = None
        if thumbnail and thumbnail.filename:
            thumbnail_filename = secure_filename(thumbnail.filename)
            thumbnail_path = os.path.join(upload_dir, f"{account_id}_{int(datetime.now().timestamp())}_{thumbnail_filename}")
            thumbnail.save(thumbnail_path)
        
        # 获取账号信息和device_id
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT device_id FROM accounts WHERE id = ?', (account_id,))
            account = cursor.fetchone()
            
            if not account:
                return response_error('Account not found', 404)
            
            device_db_id = account[0]
            
            # 创建任务记录（使用HTTP URL作为video_url，客户端可以通过HTTP下载）
            video_tags_json = json.dumps(tags.split(',') if tags else []) if tags else None
            # 使用HTTP URL，客户端可以通过这个URL下载文件
            import urllib.parse
            filename_only = os.path.basename(video_path)
            filename_encoded = urllib.parse.quote(filename_only)
            # 获取当前请求的host和scheme
            scheme = request.scheme
            host = request.host
            video_url = f"{scheme}://{host}/api/video/download/{filename_encoded}"
            
            # 缩略图也使用HTTP URL（如果有）
            thumbnail_url_http = None
            if thumbnail_path:
                thumbnail_filename_only = os.path.basename(thumbnail_path)
                thumbnail_filename_encoded = urllib.parse.quote(thumbnail_filename_only)
                thumbnail_url_http = f"{scheme}://{host}/api/video/download/{thumbnail_filename_encoded}"
            
            cursor.execute('''
                INSERT INTO video_tasks 
                (account_id, device_id, video_url, video_title, video_tags, publish_date, thumbnail_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (account_id, device_db_id, video_url, title, video_tags_json, publish_date, thumbnail_url_http))
            
            task_id = cursor.lastrowid
            conn.commit()
        
        # 返回任务信息
        return response_success({
            'task_id': task_id,
            'account_id': account_id,
            'title': title,
            'status': 'pending',
            'message': 'Task created. Client will process it via task queue.'
        }, 'Task created', 201)
    
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/social/listen/start', methods=['POST'])
def social_start_listen():
    """启动消息监听（使用任务队列模式）"""
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 检查账号是否存在，并获取关联的device_id
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, device_id FROM accounts WHERE id = ?', (account_id,))
            account_row = cursor.fetchone()
            if not account_row:
                return response_error('Account not found', 404)
            
            device_db_id = account_row[1]
            
            # 检查是否有running状态的start任务
            cursor.execute('''
                SELECT id FROM listen_tasks 
                WHERE account_id = ? AND action = 'start' AND status = 'running'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (account_id,))
            running_task = cursor.fetchone()
            
            # 如果有running的任务，直接返回成功（已经在运行，不需要重新创建）
            if running_task:
                cursor.execute('SELECT * FROM listen_tasks WHERE id = ?', (running_task[0],))
                task = dict(cursor.fetchone())
                return response_success(task, 'Listen task is already running.', 200)
            
            # 检查是否有pending状态的start任务
            cursor.execute('''
                SELECT id FROM listen_tasks 
                WHERE account_id = ? AND action = 'start' AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (account_id,))
            pending_task = cursor.fetchone()
            
            if pending_task:
                # 如果有pending的任务，更新它（重新设置创建时间，让客户端重新处理）
                task_id = pending_task[0]
                cursor.execute('''
                    UPDATE listen_tasks 
                    SET created_at = CURRENT_TIMESTAMP, 
                        status = 'pending',
                        error_message = NULL
                    WHERE id = ?
                ''', (task_id,))
                cursor.execute('SELECT * FROM listen_tasks WHERE id = ?', (task_id,))
                task = dict(cursor.fetchone())
            else:
                # 创建新的监听任务
                cursor.execute('''
                    INSERT INTO listen_tasks (account_id, device_id, action, status)
                    VALUES (?, ?, 'start', 'pending')
                ''', (account_id, device_db_id))
                
                task_id = cursor.lastrowid
                cursor.execute('SELECT * FROM listen_tasks WHERE id = ?', (task_id,))
                task = dict(cursor.fetchone())
        
        return response_success(task, 'Listen task created. Client will process it via task queue.', 201)
    
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/social/listen/messages', methods=['GET'])
def social_get_messages():
    """获取监听到的消息（从数据库）"""
    try:
        account_id = request.args.get('account_id', type=int)
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 获取消息总数
            cursor.execute('SELECT COUNT(*) FROM messages WHERE account_id = ?', (account_id,))
            total = cursor.fetchone()[0]
            
            # 获取消息列表（按时间倒序）
            cursor.execute('''
                SELECT id, user_name, text, is_me, message_time, timestamp, created_at
                FROM messages
                WHERE account_id = ?
                ORDER BY timestamp DESC, created_at DESC
                LIMIT ? OFFSET ?
            ''', (account_id, limit, offset))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'user_name': row[1],
                    'text': row[2],
                    'is_me': bool(row[3]),
                    'time': row[4],
                    'timestamp': row[5],
                    'created_at': row[6]
                })
        
        return response_success({
            'account_id': account_id,
            'messages': messages,
            'count': len(messages),
            'total': total
        })
    
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/messages', methods=['GET', 'POST'])
def messages():
    """获取或创建消息"""
    if request.method == 'GET':
        return get_messages()
    elif request.method == 'POST':
        return create_message()

def get_messages():
    """获取消息列表（支持分页和筛选）"""
    try:
        account_id = request.args.get('account_id', type=int)
        user_name = request.args.get('user_name')
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if account_id:
                conditions.append('account_id = ?')
                params.append(account_id)
            
            if user_name:
                conditions.append('user_name = ?')
                params.append(user_name)
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            
            # 获取总数
            cursor.execute(f'SELECT COUNT(*) FROM messages WHERE {where_clause}', params)
            total = cursor.fetchone()[0]
            
            # 获取消息列表
            params.extend([limit, offset])
            cursor.execute(f'''
                SELECT id, account_id, user_name, text, is_me, message_time, timestamp, created_at
                FROM messages
                WHERE {where_clause}
                ORDER BY timestamp DESC, created_at DESC
                LIMIT ? OFFSET ?
            ''', params)
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'account_id': row[1],
                    'user_name': row[2],
                    'text': row[3],
                    'is_me': bool(row[4]),
                    'time': row[5],
                    'timestamp': row[6],
                    'created_at': row[7]
                })
        
        return response_success({
            'messages': messages,
            'count': len(messages),
            'total': total
        })
    
    except Exception as e:
        return response_error(str(e), 500)

def create_message():
    """创建消息（由客户端调用）"""
    try:
        data = request.json
        account_id = data.get('account_id')
        user_name = data.get('user_name')
        text = data.get('text')
        is_me = data.get('is_me', False)
        message_time = data.get('message_time', '')
        
        if not account_id or not user_name or not text:
            return response_error('account_id, user_name and text are required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在相同的消息（避免重复）
            cursor.execute('''
                SELECT id FROM messages 
                WHERE account_id = ? AND user_name = ? AND text = ? AND message_time = ?
            ''', (account_id, user_name, text, message_time))
            
            if cursor.fetchone():
                return response_success({'duplicate': True}, 'Message already exists', 200)
            
            # 插入新消息
            cursor.execute('''
                INSERT INTO messages (account_id, user_name, text, is_me, message_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (account_id, user_name, text, 1 if is_me else 0, message_time, datetime.now().isoformat()))
            
            message_id = cursor.lastrowid
            cursor.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
            message = dict(cursor.fetchone())
        
        return response_success(message, 'Message created', 201)
    except Exception as e:
        import logging
        logging.error(f"Error creating message: {e}", exc_info=True)
        return response_error(str(e), 500)

@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    """删除单条消息"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
            
            if cursor.rowcount == 0:
                return response_error('Message not found', 404)
        
        return response_success({'message_id': message_id}, 'Message deleted')
    
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/messages/clear', methods=['POST'])
def clear_messages():
    """清空指定账号的消息"""
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE account_id = ?', (account_id,))
            deleted_count = cursor.rowcount
        
        return response_success({
            'account_id': account_id,
            'deleted_count': deleted_count
        }, f'Cleared {deleted_count} messages')
    
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/social/listen/stop', methods=['POST'])
def social_stop_listen():
    """停止消息监听（使用任务队列模式）"""
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 检查账号是否存在，并获取关联的device_id
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, device_id FROM accounts WHERE id = ?', (account_id,))
            account_row = cursor.fetchone()
            if not account_row:
                return response_error('Account not found', 404)
            
            device_db_id = account_row[1]
            
            # 检查是否有pending状态的stop任务
            cursor.execute('''
                SELECT id FROM listen_tasks 
                WHERE account_id = ? AND action = 'stop' AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (account_id,))
            pending_stop_task = cursor.fetchone()
            
            if pending_stop_task:
                # 如果有pending的stop任务，更新它（重新设置创建时间）
                task_id = pending_stop_task[0]
                cursor.execute('''
                    UPDATE listen_tasks 
                    SET created_at = CURRENT_TIMESTAMP, 
                        status = 'pending',
                        error_message = NULL
                    WHERE id = ?
                ''', (task_id,))
                cursor.execute('SELECT * FROM listen_tasks WHERE id = ?', (task_id,))
                task = dict(cursor.fetchone())
            else:
                # 创建新的停止监听任务
                cursor.execute('''
                    INSERT INTO listen_tasks (account_id, device_id, action, status)
                    VALUES (?, ?, 'stop', 'pending')
                ''', (account_id, device_db_id))
                
                task_id = cursor.lastrowid
                cursor.execute('SELECT * FROM listen_tasks WHERE id = ?', (task_id,))
                task = dict(cursor.fetchone())
        
        return response_success(task, 'Stop listen task created. Client will process it via task queue.', 201)
    
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/social/chat/reply', methods=['POST'])
def social_reply_message():
    """回复消息（使用任务队列模式）"""
    try:
        data = request.json
        account_id = data.get('account_id')
        target_user = data.get('target_user')
        message = data.get('message')
        
        if not account_id or not target_user or not message:
            return response_error('account_id, target_user and message are required', 400)
        
        # 任务队列模式：创建对话任务
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 检查账号是否存在，并获取关联的device_id
            cursor.execute('SELECT id, device_id FROM accounts WHERE id = ?', (account_id,))
            account_row = cursor.fetchone()
            if not account_row:
                return response_error('Account not found', 404)
            
            device_db_id = account_row[1]
            
            # 创建对话任务
            cursor.execute('''
                INSERT INTO chat_tasks (account_id, device_id, target_user, message, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (account_id, device_db_id, target_user, message))
            
            task_id = cursor.lastrowid
            cursor.execute('SELECT * FROM chat_tasks WHERE id = ?', (task_id,))
            task = dict(cursor.fetchone())
        
        return response_success(task, 'Chat task created. Client will process it via task queue.', 201)
    
    except Exception as e:
        return response_error(str(e), 500)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM devices WHERE status = "online"')
            online_devices = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) as count FROM accounts WHERE login_status = "logged_in"')
            logged_in_accounts = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) as count FROM video_tasks WHERE status = "pending"')
            pending_video_tasks = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) as count FROM chat_tasks WHERE status = "pending"')
            pending_chat_tasks = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) as count FROM listen_tasks WHERE status = "pending"')
            pending_listen_tasks = cursor.fetchone()[0]
        
        return response_success({
            'online_devices': online_devices,
            'logged_in_accounts': logged_in_accounts,
            'pending_video_tasks': pending_video_tasks,
            'pending_chat_tasks': pending_chat_tasks,
            'pending_listen_tasks': pending_listen_tasks
        })
    except Exception as e:
        return response_error(str(e), 500)

if __name__ == '__main__':
    import sys
    init_db()
    
    # 从环境变量或命令行参数获取端口，默认5000
    port = int(os.getenv('PORT', 5000))
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"警告: 无效的端口号 '{sys.argv[1]}', 使用默认端口 {port}")
    
    # 尝试启动服务器，如果端口被占用则尝试其他端口
    import socket
    def is_port_available(port):
        """检查端口是否可用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return True
            except OSError:
                return False
    
    # 如果默认端口被占用，尝试其他端口
    original_port = port
    if not is_port_available(port):
        print(f"警告: 端口 {port} 已被占用，尝试其他端口...")
        for alt_port in range(5001, 5010):
            if is_port_available(alt_port):
                port = alt_port
                print(f"使用端口 {port} 启动服务器")
                break
        else:
            print(f"错误: 无法找到可用端口（尝试了 {original_port}-5009）")
            print("请关闭占用端口的程序，或手动指定其他端口：")
            print(f"  python app.py <端口号>")
            print(f"  例如: python app.py 8080")
            sys.exit(1)
    
    try:
        print(f"正在启动服务器...")
        print(f"访问地址: http://localhost:{port}")
        print(f"按 Ctrl+C 停止服务器")
        # 启用热重载功能
        # debug=True 会自动启用 use_reloader 和 use_debugger
        # extra_files 参数可以让 Flask 监听 HTML 等静态文件的变化
        # 设置环境变量，减少重载器对第三方库的监听
        # 注意：Flask 的重载器会监听所有导入的模块，包括 Playwright
        # 如果频繁重载，可以临时禁用 use_reloader
        # 检查环境变量，如果设置了 DISABLE_RELOADER，则禁用自动重载
        # 这样可以避免 Playwright 等第三方库触发重载
        use_reloader = os.getenv('DISABLE_RELOADER', '').lower() != 'true'
        
        app.run(
            debug=True,
            host='0.0.0.0',
            port=port,
            use_reloader=use_reloader,  # 可通过环境变量禁用
            use_debugger=True,  # 启用调试器
            extra_files=[  # 监听这些文件的变化，变化时自动重载
                os.path.join(os.path.dirname(__file__), 'index.html'),
                os.path.join(os.path.dirname(__file__), 'login_helper.html'),
            ]
        )
    except OSError as e:
        if "以一种访问权限不允许的方式做了一个访问套接字的尝试" in str(e) or "permission denied" in str(e).lower():
            print(f"错误: 端口 {port} 访问被拒绝")
            print("可能的原因：")
            print("1. 端口被其他程序占用")
            print("2. 需要管理员权限")
            print("3. 防火墙阻止")
            print("\n解决方案：")
            print(f"1. 关闭占用端口 {port} 的程序")
            print(f"2. 使用其他端口: python app.py <端口号>")
            print(f"3. 以管理员身份运行")
        else:
            print(f"启动服务器时出错: {e}")
        sys.exit(1)


