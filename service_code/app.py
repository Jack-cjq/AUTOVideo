"""
Social Auto Upload Flask 应用
提供视频上传、消息监听和回复功能
"""

import os
import json
import asyncio
import tempfile
import threading
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from contextlib import contextmanager

from conf import BASE_DIR, LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from uploader.douyin_uploader.main import DouYinVideo
from listener.douyin_listener.main import douyin_chat_main, open_douyin_chat, _send_chat_message
from utils.log import douyin_logger
from playwright.async_api import async_playwright

app = Flask(__name__)
CORS(app)

# 配置
UPLOAD_FOLDER = BASE_DIR / 'videoFile'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 数据库配置（使用center_code的数据库）
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'center_code', 'platform.db')

# 存储监听任务的状态
listening_tasks = {}

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

def save_message_to_db(account_id, user_name, text, is_me, message_time):
    """保存消息到数据库"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # 检查是否已存在相同的消息（避免重复）
            cursor.execute('''
                SELECT id FROM messages 
                WHERE account_id = ? AND user_name = ? AND text = ? AND message_time = ?
            ''', (account_id, user_name, text, message_time))
            
            if cursor.fetchone():
                return False  # 消息已存在
            
            # 插入新消息
            cursor.execute('''
                INSERT INTO messages (account_id, user_name, text, is_me, message_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (account_id, user_name, text, 1 if is_me else 0, message_time, datetime.now().isoformat()))
            return True
    except Exception as e:
        douyin_logger.error(f"Failed to save message to database: {e}")
        return False

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_cookies_to_temp(cookies_json):
    """将cookies JSON保存到临时文件"""
    try:
        # 如果cookies_json是字符串，先验证是否为有效JSON
        if isinstance(cookies_json, str):
            # 验证JSON格式
            try:
                cookies_data = json.loads(cookies_json)
                # 重新序列化确保格式正确
                cookies_json = json.dumps(cookies_data, ensure_ascii=False)
            except json.JSONDecodeError as e:
                douyin_logger.error(f"Invalid JSON format in cookies: {e}")
                raise ValueError(f"Invalid JSON format: {e}")
        else:
            # 如果是字典，直接序列化
            cookies_json = json.dumps(cookies_json, ensure_ascii=False)
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        temp_file.write(cookies_json)
        temp_file.close()
        
        douyin_logger.info(f"Saved cookies to temp file: {temp_file.name}")
        return temp_file.name
    except Exception as e:
        douyin_logger.error(f"Error saving cookies to temp file: {e}")
        raise

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

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return response_success({'status': 'healthy'})

@app.route('/api/upload/video', methods=['POST'])
def upload_video():
    """
    视频上传接口
    接收文件而不是URL，使用传递的cookies
    """
    try:
        # 检查是否有文件
        if 'video' not in request.files:
            return response_error('No video file provided', 400)
        
        file = request.files['video']
        if file.filename == '':
            return response_error('No file selected', 400)
        
        if not allowed_file(file.filename):
            return response_error('File type not allowed', 400)
        
        # 获取参数
        cookies_json = request.form.get('cookies')  # cookies JSON字符串
        account_id = request.form.get('account_id', type=int)  # 账号ID，用于更新cookie
        task_id = request.form.get('task_id', type=int)  # 任务ID，用于更新任务状态
        title = request.form.get('title', '').strip()  # 去除首尾空格
        tags_str = request.form.get('tags', '').strip()  # 去除首尾空格
        publish_date = request.form.get('publish_date')
        thumbnail = request.files.get('thumbnail')
        
        if not cookies_json:
            return response_error('cookies is required', 400)
        
        # 解析tags - 确保正确分割
        tags = []
        if tags_str:
            # 按逗号分割，去除每个标签的首尾空格，过滤空标签
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        
        # 记录接收到的参数
        douyin_logger.info(f"Received upload request - title: '{title}', tags_str: '{tags_str}', parsed tags: {tags}")
        
        # 保存上传的文件
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(file_path)
        
        # 保存cookies到临时文件
        account_file = save_cookies_to_temp(cookies_json)
        
        # 保存缩略图（如果有）
        thumbnail_path = None
        if thumbnail and thumbnail.filename:
            thumbnail_filename = secure_filename(thumbnail.filename)
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename)
            thumbnail.save(thumbnail_path)
        
        # 解析发布时间
        publish_datetime = 0
        if publish_date:
            try:
                from datetime import datetime
                publish_datetime = datetime.fromisoformat(publish_date)
            except:
                publish_datetime = 0
        
        # 如果没有标题，尝试从文件名获取
        if not title:
            title = Path(filename).stem
        
        # 记录日志，确保title和tags正确传递
        douyin_logger.info(f"Upload parameters - title: '{title}', tags: {tags}, tags_str: '{tags_str}'")
        
        # 在后台线程中执行上传
        def run_upload():
            try:
                douyin_logger.info(f"Starting upload - title: '{title}', tags: {tags}")
                updated_cookies = asyncio.run(execute_upload(
                    title, file_path, tags, publish_datetime, account_file, thumbnail_path, account_id
                ))
                # 如果上传成功且返回了更新的cookie，调用center接口更新cookie和任务状态
                if updated_cookies and account_id:
                    update_cookie_to_center(account_id, updated_cookies, task_id)
                elif task_id:
                    # 即使没有cookie更新，如果上传成功也应该更新任务状态
                    # 但通常cookie更新表示上传完成
                    pass
            except Exception as e:
                douyin_logger.error(f"Upload error: {e}")
                # 如果上传失败，更新任务状态为失败
                if task_id:
                    update_task_status_to_center(task_id, 'failed', str(e))
        
        thread = threading.Thread(target=run_upload, daemon=True)
        thread.start()
        
        return response_success({
            'filename': filename,
            'title': title,
            'tags': tags
        }, 'Upload started', 201)
        
    except Exception as e:
        douyin_logger.error(f"Upload video error: {e}")
        return response_error(str(e), 500)

async def execute_upload(title, file_path, tags, publish_date, account_file, thumbnail_path, account_id=None):
    """执行视频上传，返回更新后的cookie"""
    try:
        app = DouYinVideo(
            title=title,
            file_path=file_path,
            tags=tags,
            publish_date=publish_date,
            account_file=account_file,
            thumbnail_path=thumbnail_path
        )
        await app.main()
        douyin_logger.success(f"Video uploaded successfully: {title}")
        
        # 读取更新后的cookie
        try:
            if os.path.exists(account_file):
                with open(account_file, 'r', encoding='utf-8') as f:
                    updated_cookies = json.load(f)
                douyin_logger.info(f"Read updated cookies from {account_file}")
                return updated_cookies
        except Exception as e:
            douyin_logger.error(f"Failed to read updated cookies: {e}")
        
        return None
    except Exception as e:
        douyin_logger.error(f"Upload execution error: {e}")
        raise

def update_cookie_to_center(account_id, cookies_json, task_id=None):
    """将更新后的cookie发送到center更新数据库，并更新任务状态"""
    try:
        # 使用统一的中心服务器地址配置
        center_base_url = os.getenv('CENTER_BASE_URL', 'http://8.148.29.194:8080')
        
        # 如果cookies_json是字典，转换为JSON字符串
        if isinstance(cookies_json, dict):
            cookies_json = json.dumps(cookies_json, ensure_ascii=False)
        
        # 更新cookie
        response = requests.put(
            f'{center_base_url}/api/accounts/{account_id}/cookies',
            json={'cookies': cookies_json},
            timeout=10
        )
        
        if response.status_code == 200:
            douyin_logger.success(f"Cookie updated to center for account {account_id}")
        else:
            douyin_logger.error(f"Failed to update cookie to center: {response.text}")
        
        # 如果有task_id，更新任务状态为已完成
        if task_id:
            update_task_status_to_center(task_id, 'completed', None)
            
    except Exception as e:
        douyin_logger.error(f"Error updating cookie to center: {e}")
        # 如果更新cookie失败，但任务已完成，仍然更新任务状态
        if task_id:
            update_task_status_to_center(task_id, 'completed', None)

def update_task_status_to_center(task_id, status, error_message=None):
    """更新center中的任务状态"""
    try:
        # 使用统一的中心服务器地址配置
        center_base_url = os.getenv('CENTER_BASE_URL', 'http://8.148.29.194:8080')
        
        data = {
            'task_id': task_id,
            'status': status
        }
        if error_message:
            data['error_message'] = error_message
        if status == 'completed':
            data['progress'] = 100
        
        response = requests.post(
            f'{center_base_url}/api/video/callback',
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            douyin_logger.success(f"Task {task_id} status updated to {status}")
        else:
            douyin_logger.error(f"Failed to update task status: {response.text}")
    except Exception as e:
        douyin_logger.error(f"Error updating task status to center: {e}")

@app.route('/api/listen/start', methods=['POST'])
def start_listen():
    """
    启动消息监听接口
    返回消息信息
    """
    try:
        data = request.json
        cookies_json = data.get('cookies')
        account_id = data.get('account_id')
        
        if not cookies_json:
            return response_error('cookies is required', 400)
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 如果已经在监听，先停止
        if account_id in listening_tasks:
            stop_listen_internal(account_id)
        
        # 消息现在直接保存到数据库，不需要内存存储
        
        # 验证cookies格式（应该是Playwright的storage_state格式）
        try:
            if isinstance(cookies_json, str):
                cookies_data = json.loads(cookies_json)
            else:
                cookies_data = cookies_json
            
            # 验证storage_state格式
            if not isinstance(cookies_data, dict):
                raise ValueError("Cookies must be a dictionary (storage_state format)")
            
            # 检查是否有cookies或origins字段（storage_state的标准格式）
            has_cookies = 'cookies' in cookies_data and isinstance(cookies_data.get('cookies'), list)
            has_origins = 'origins' in cookies_data and isinstance(cookies_data.get('origins'), list)
            
            if not (has_cookies or has_origins):
                douyin_logger.warning(f"Cookies format may be invalid for account {account_id}, missing cookies/origins")
            
            douyin_logger.info(f"Cookies format valid for account {account_id}, has_cookies: {has_cookies}, has_origins: {has_origins}, keys: {list(cookies_data.keys())}")
            
            # 确保cookies_json是字符串格式
            if not isinstance(cookies_json, str):
                cookies_json = json.dumps(cookies_data, ensure_ascii=False)
                
        except json.JSONDecodeError as e:
            douyin_logger.error(f"Invalid JSON format for account {account_id}: {e}")
            return response_error(f'Invalid cookies JSON format: {str(e)}', 400)
        except Exception as e:
            douyin_logger.error(f"Invalid cookies format for account {account_id}: {e}")
            return response_error(f'Invalid cookies format: {str(e)}', 400)
        
        # 保存cookies到临时文件
        try:
            account_file = save_cookies_to_temp(cookies_json)
            douyin_logger.info(f"Account file created: {account_file} for account {account_id}")
            
            # 验证文件是否存在且可读
            if not os.path.exists(account_file):
                raise FileNotFoundError(f"Temp file not created: {account_file}")
            
            # 验证文件内容
            with open(account_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                try:
                    json.loads(file_content)
                    douyin_logger.info(f"Temp file content validated for account {account_id}")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Temp file contains invalid JSON: {e}")
                    
        except Exception as e:
            douyin_logger.error(f"Failed to save cookies to temp file for account {account_id}: {e}", exc_info=True)
            return response_error(f'Failed to save cookies: {str(e)}', 500)
        
        # 在后台线程中启动监听
        def run_listen():
            try:
                douyin_logger.info(f"Starting listen thread for account {account_id}, using file: {account_file}")
                asyncio.run(execute_listen(account_id, account_file))
            except Exception as e:
                douyin_logger.error(f"Listen error: {e}", exc_info=True)
        
        thread = threading.Thread(target=run_listen, daemon=True)
        thread.start()
        listening_tasks[account_id] = thread
        
        return response_success({
            'account_id': account_id,
            'status': 'listening'
        }, 'Listening started', 201)
        
    except Exception as e:
        douyin_logger.error(f"Start listen error: {e}")
        return response_error(str(e), 500)

async def execute_listen(account_id, account_file):
    """执行消息监听 - 完全复刻原始逻辑"""
    try:
        from listener.douyin_listener.main import open_douyin_chat
        from playwright.async_api import async_playwright
        
        # 验证account_file是否存在
        if not os.path.exists(account_file):
            douyin_logger.error(f"Account file not found: {account_file} for account {account_id}")
            if account_id in listening_tasks:
                del listening_tasks[account_id]
            return
        
        douyin_logger.info(f"[LISTEN] Starting listen for account {account_id}, using file: {account_file}")
        
        async with async_playwright() as playwright:
            try:
                page = await open_douyin_chat(playwright, account_file)
                douyin_logger.info(f"[LISTEN] Browser opened successfully for account {account_id}")
            except Exception as e:
                douyin_logger.error(f"[LISTEN] Failed to open browser for account {account_id}: {e}", exc_info=True)
                if account_id in listening_tasks:
                    del listening_tasks[account_id]
                return
            
            douyin_logger.info(f"[LISTEN] Started listening for account {account_id}")
            
            # 持续监听消息 - 定期解析所有会话的消息
            while account_id in listening_tasks:
                try:
                    # 解析消息（完全复刻原始逻辑，遍历所有会话）
                    await parse_messages(page, account_id)
                    await asyncio.sleep(10)  # 每10秒检查一次，避免过于频繁
                except Exception as e:
                    douyin_logger.error(f"Parse messages error for account {account_id}: {e}", exc_info=True)
                    await asyncio.sleep(10)
                    
    except Exception as e:
        douyin_logger.error(f"Listen execution error for account {account_id}: {e}", exc_info=True)
        if account_id in listening_tasks:
            del listening_tasks[account_id]

async def _get_first_dialog_snapshot(page):
    """获取当前对话面板中第一条消息块的文本快照"""
    try:
        first_block = await page.query_selector("div.box-item-dSA1TJ")
        if not first_block:
            return ""
        text = await first_block.inner_text()
        return (text or "").strip()
    except Exception:
        return ""

async def _wait_conversation_switched(page, user_name, prev_first_snapshot, timeout=10.0, poll_interval=0.3):
    """等待会话切换成功"""
    import time
    start = time.monotonic()
    active_li_locator = page.locator(
        "div.chat-content.semi-tabs-pane-active li.semi-list-item.active-vBCZvL span.item-header-name-vL_79m"
    )
    header_locator = page.locator("div.box-header-Qq0ZO_ strong.box-header-name-YOrIxz")

    while True:
        elapsed = time.monotonic() - start
        if elapsed > timeout:
            return False

        # 条件 1：左侧激活 li 是否为当前用户
        try:
            active_count = await active_li_locator.filter(has_text=user_name).count()
        except Exception:
            active_count = 0

        # 条件 2：右侧标题是否包含用户名
        try:
            header_count = await header_locator.filter(has_text=user_name).count()
        except Exception:
            header_count = 0

        # 条件 3：第一条消息块内容是否发生变化
        try:
            first_snapshot = await _get_first_dialog_snapshot(page)
        except Exception:
            first_snapshot = ""

        content_changed = bool(first_snapshot and first_snapshot != prev_first_snapshot)

        if active_count > 0 or header_count > 0 or content_changed:
            return True

        await asyncio.sleep(poll_interval)

async def parse_messages(page, account_id):
    """解析消息并存储 - 完全复刻原始逻辑"""
    try:
        from datetime import datetime
        
        # 只取"当前激活"的聊天面板里的会话列表
        active_list_selector = "div.chat-content.semi-tabs-pane-active li.semi-list-item"
        try:
            await page.wait_for_selector(active_list_selector, timeout=20000)
        except:
            douyin_logger.warning("等待会话列表超时")
            return
        
        # 初始时记录一份稳定的会话句柄列表
        conv_items = await page.query_selector_all(active_list_selector)
        total = len(conv_items)
        douyin_logger.info(f"[*] 当前消息会话条数: {total}")
        
        for idx, item in enumerate(conv_items):
            try:
                # 先拿到用户名用于日志，再做点击
                name_el = await item.query_selector("span.item-header-name-vL_79m")
                if not name_el:
                    # 某些占位/不可点击项没有用户名，直接跳过
                    continue
                user_name = (await name_el.inner_text()).strip()
                if not user_name:
                    # 用户名为空的一般是系统提示/空白占位，也跳过
                    continue
                
                douyin_logger.debug(f"[CHAT_LIST] 第 {idx + 1} 条会话，用户名: {user_name}")

                # 点击前记录当前第一条消息快照，用于判断对话内容是否发生切换
                prev_snapshot = await _get_first_dialog_snapshot(page)

                # 对单条会话的点击 + 切换检测增加重试，避免被弹窗/动画打断
                switched = False
                for attempt in range(3):
                    try:
                        await item.scroll_into_view_if_needed()
                        await item.click(force=True, timeout=8000)
                    except Exception as click_e:
                        douyin_logger.debug(f"[!] 第 {idx + 1} 条会话（{user_name}）第 {attempt + 1} 次点击失败: {click_e}")
                        await asyncio.sleep(0.5)
                        continue

                    # 等待会话真正切换成功（激活态 / 标题 / 内容任意一项发生变化）
                    switched = await _wait_conversation_switched(
                        page, user_name, prev_snapshot, timeout=8.0
                    )
                    if switched:
                        break
                    douyin_logger.debug(f"[!] 第 {idx + 1} 条会话（{user_name}）第 {attempt + 1} 次点击后未检测到切换，重试...")
                    await asyncio.sleep(0.5)

                if not switched:
                    douyin_logger.warning(f"[!] 会话 '{user_name}' 在多次重试后仍未成功切换，跳过该会话。")
                    continue

                await asyncio.sleep(0.5)

                # 解析右侧对话框中的聊天记录
                try:
                    await page.locator("div.box-item-dSA1TJ").first.wait_for(state="attached", timeout=10000)
                except Exception as wait_e:
                    douyin_logger.error(f"[!] 等待对话内容出现失败（会话: {user_name}）: {wait_e}")
                    continue

                message_blocks = await page.query_selector_all("div.box-item-dSA1TJ")
                current_time = ""
                
                for block in message_blocks:
                    class_attr = await block.get_attribute("class") or ""

                    # 时间行：只记录当前时间上下文
                    if "time-Za5gKL" in class_attr:
                        current_time = (await block.inner_text()).strip()
                        continue

                    # 消息行：包含真实对话内容
                    text_el = await block.query_selector("pre.text-X2d7fS.text-item-message-YBtflz")
                    if not text_el:
                        continue

                    text = (await text_el.inner_text()).strip()
                    if not text:
                        continue

                    # 判断是自己还是对方发的消息
                    is_me = "is-me-TJHr4A" in class_attr
                    
                    # 保存消息到数据库
                    saved = save_message_to_db(account_id, user_name, text, is_me, current_time)
                    if saved:
                        douyin_logger.debug(f"[DIALOG] 会话用户: {user_name} | 方向: {'我' if is_me else '对方'} | 时间: {current_time} | 文本: {text}")

                # 为避免触发风控，可在会话之间稍微停顿
                await asyncio.sleep(2)

            except Exception as sub_e:
                douyin_logger.error(f"[!] 处理第 {idx + 1} 条会话时出错: {sub_e}")
                # 出错后继续处理下一条
                continue
                
    except Exception as e:
        douyin_logger.error(f"[!] 无法解析消息列表区域或对话内容: {e}")

@app.route('/api/listen/messages', methods=['GET'])
def get_messages():
    """获取监听到的消息（从数据库）"""
    try:
        account_id = request.args.get('account_id', type=int)
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # 从数据库获取消息
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
        
        # 检查是否正在监听
        is_listening = account_id in listening_tasks
        
        douyin_logger.info(f"Get messages for account {account_id}: {len(messages)} messages (total: {total}), listening: {is_listening}")
        
        return response_success({
            'account_id': account_id,
            'messages': messages,
            'count': len(messages),
            'total': total,
            'is_listening': is_listening
        })
        
    except Exception as e:
        douyin_logger.error(f"Get messages error: {e}")
        return response_error(str(e), 500)

@app.route('/api/listen/stop', methods=['POST'])
def stop_listen():
    """停止消息监听"""
    try:
        data = request.json
        account_id = data.get('account_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        stop_listen_internal(account_id)
        
        return response_success({
            'account_id': account_id,
            'status': 'stopped'
        }, 'Listening stopped')
        
    except Exception as e:
        douyin_logger.error(f"Stop listen error: {e}")
        return response_error(str(e), 500)

def stop_listen_internal(account_id):
    """内部停止监听函数"""
    if account_id in listening_tasks:
        del listening_tasks[account_id]

@app.route('/api/chat/reply', methods=['POST'])
def reply_message():
    """
    回复消息接口
    等待消息传递完成
    """
    try:
        data = request.json
        cookies_json = data.get('cookies')
        target_user = data.get('target_user')
        message = data.get('message')
        
        if not cookies_json:
            return response_error('cookies is required', 400)
        if not target_user:
            return response_error('target_user is required', 400)
        if not message:
            return response_error('message is required', 400)
        
        # 保存cookies到临时文件
        account_file = save_cookies_to_temp(cookies_json)
        
        # 在后台线程中执行回复
        result = {'success': False, 'error': None}
        
        def run_reply():
            try:
                asyncio.run(execute_reply(account_file, target_user, message, result))
            except Exception as e:
                douyin_logger.error(f"Reply error: {e}")
                result['error'] = str(e)
        
        thread = threading.Thread(target=run_reply, daemon=False)  # 等待完成
        thread.start()
        thread.join(timeout=60)  # 最多等待60秒
        
        if result['success']:
            return response_success({
                'target_user': target_user,
                'message': message,
                'status': 'sent'
            }, 'Message sent')
        else:
            return response_error(result.get('error', 'Reply timeout'), 500)
        
    except Exception as e:
        douyin_logger.error(f"Reply message error: {e}")
        return response_error(str(e), 500)

async def execute_reply(account_file, target_user, message, result):
    """执行消息回复"""
    try:
        from listener.douyin_listener.main import open_douyin_chat, _send_chat_message
        from playwright.async_api import async_playwright
        
        async with async_playwright() as playwright:
            page = await open_douyin_chat(playwright, account_file)
            
            # 查找目标用户并发送消息
            active_list_selector = "div.chat-content.semi-tabs-pane-active li.semi-list-item"
            conv_items = await page.query_selector_all(active_list_selector)
            
            for item in conv_items:
                try:
                    name_el = await item.query_selector("span.item-header-name-vL_79m")
                    if not name_el:
                        continue
                    user_name = (await name_el.inner_text()).strip()
                    
                    if user_name == target_user:
                        # 点击会话
                        await item.scroll_into_view_if_needed()
                        await item.click(force=True, timeout=5000)
                        await asyncio.sleep(1)
                        
                        # 发送消息
                        success = await _send_chat_message(page, target_user, message)
                        result['success'] = success
                        if success:
                            douyin_logger.success(f"Message sent to {target_user}: {message}")
                        else:
                            result['error'] = 'Failed to send message'
                        return
                        
                except Exception as e:
                    douyin_logger.debug(f"Find user error: {e}")
                    continue
            
            result['error'] = f'User {target_user} not found'
            
    except Exception as e:
        douyin_logger.error(f"Reply execution error: {e}")
        result['error'] = str(e)

if __name__ == '__main__':
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 从环境变量获取端口，默认8081
    port = int(os.getenv('PORT', 8081))
    app.run(debug=True, host='0.0.0.0', port=port)

