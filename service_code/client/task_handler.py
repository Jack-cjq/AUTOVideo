"""
任务处理器
处理从中心服务器拉取的任务
"""

import os
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Optional
from utils.log import douyin_logger
from uploader.douyin_uploader.main import DouYinVideo
from listener.douyin_listener.main import open_douyin_chat, _send_chat_message
from playwright.async_api import async_playwright
from conf import BASE_DIR, LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS

async def handle_video_task(task: Dict, client):
    """
    处理视频上传任务
    
    Args:
        task: 任务字典
        client: CenterClient实例
    """
    task_id = task.get('id')
    account_id = task.get('account_id')
    video_url = task.get('video_url')
    video_title = task.get('video_title', '')
    video_tags = task.get('video_tags')
    publish_date = task.get('publish_date')
    thumbnail_url = task.get('thumbnail_url')
    
    douyin_logger.info(f"Processing video task {task_id}: {video_title}")
    
    # 更新任务状态为处理中
    client.update_task_status(task_id, 'video', 'uploading', progress=0)
    
    try:
        # 获取账号信息（包括cookies）
        account_info = client.get_account_info(account_id)
        if not account_info:
            raise Exception(f"Account {account_id} not found")
        
        cookies_json = account_info.get('cookies')
        if not cookies_json:
            raise Exception(f"Account {account_id} has no cookies")
        
        # 解析cookies
        if isinstance(cookies_json, str):
            cookies_data = json.loads(cookies_json)
        else:
            cookies_data = cookies_json
        
        # 保存cookies到临时文件（同时保存到持久化目录用于调试）
        account_file = save_cookies_to_temp(cookies_data, account_id)
        
        # 下载视频文件
        video_path = download_video(video_url)
        
        # 下载缩略图（如果有）
        thumbnail_path = None
        if thumbnail_url:
            thumbnail_path = download_thumbnail(thumbnail_url)
        
        # 解析tags
        tags = []
        if video_tags:
            if isinstance(video_tags, str):
                try:
                    tags = json.loads(video_tags)
                except:
                    tags = [tag.strip() for tag in video_tags.split(',') if tag.strip()]
            elif isinstance(video_tags, list):
                tags = video_tags
        
        # 解析发布时间
        publish_datetime = 0
        if publish_date:
            try:
                from datetime import datetime
                publish_datetime = datetime.fromisoformat(publish_date)
            except:
                publish_datetime = 0
        
        # 执行上传
        douyin_logger.info(f"Starting upload: title={video_title}, tags={tags}")
        updated_cookies = await execute_upload(
            video_title, video_path, tags, publish_datetime, account_file, thumbnail_path
        )
        
        # 更新cookies到center
        if updated_cookies:
            client.update_account_cookies(account_id, updated_cookies)
        
        # 更新任务状态为完成
        client.update_task_status(task_id, 'video', 'completed', progress=100)
        douyin_logger.success(f"Video task {task_id} completed")
        
        # 清理临时文件
        cleanup_temp_files([video_path, account_file, thumbnail_path])
        
    except Exception as e:
        douyin_logger.error(f"Video task {task_id} failed: {e}")
        client.update_task_status(task_id, 'video', 'failed', error_message=str(e))
        raise

async def handle_chat_task(task: Dict, client):
    """
    处理对话任务
    
    Args:
        task: 任务字典
        client: CenterClient实例
    """
    task_id = task.get('id')
    account_id = task.get('account_id')
    target_user = task.get('target_user')
    message = task.get('message')
    
    douyin_logger.info(f"Processing chat task {task_id}: send message to {target_user}")
    
    # 更新任务状态为处理中
    client.update_task_status(task_id, 'chat', 'running')
    
    try:
        # 获取账号信息（包括cookies）
        account_info = client.get_account_info(account_id)
        if not account_info:
            raise Exception(f"Account {account_id} not found")
        
        cookies_json = account_info.get('cookies')
        if not cookies_json:
            raise Exception(f"Account {account_id} has no cookies")
        
        # 解析cookies
        if isinstance(cookies_json, str):
            cookies_data = json.loads(cookies_json)
        else:
            cookies_data = cookies_json
        
        # 保存cookies到临时文件（同时保存到持久化目录用于调试）
        account_file = save_cookies_to_temp(cookies_data, account_id)
        
        # 执行发送消息
        success = await execute_send_message(account_file, target_user, message)
        
        if success:
            # 更新任务状态为完成
            client.update_task_status(task_id, 'chat', 'completed')
            douyin_logger.success(f"Chat task {task_id} completed")
        else:
            raise Exception("Failed to send message")
        
        # 清理临时文件
        cleanup_temp_files([account_file])
        
    except Exception as e:
        douyin_logger.error(f"Chat task {task_id} failed: {e}")
        client.update_task_status(task_id, 'chat', 'failed', error_message=str(e))
        raise

# 全局变量：存储监听任务状态
# 格式: {account_id: {'thread': thread, 'playwright': playwright, 'browser': browser, 'context': context, 'page': page, 'stop_event': event}}
_listening_tasks = {}

async def handle_listen_task(task: Dict, client):
    """
    处理监听任务
    
    Args:
        task: 任务字典
        client: CenterClient实例
    """
    task_id = task.get('id')
    account_id = task.get('account_id')
    action = task.get('action')  # 'start' 或 'stop'
    
    douyin_logger.info(f"Processing listen task {task_id}: action={action}, account_id={account_id}")
    
    try:
        if action == 'start':
            # 启动监听
            # 检查是否已经在监听
            if account_id in _listening_tasks:
                douyin_logger.warning(f"Listen service already running for account {account_id}, stopping it first")
                # 先停止旧的监听（在后台线程中）
                def stop_old_listen():
                    try:
                        asyncio.run(stop_listen_service(account_id))
                    except Exception as e:
                        douyin_logger.error(f"Error stopping old listen service: {e}")
                
                import threading
                stop_thread = threading.Thread(target=stop_old_listen, daemon=True)
                stop_thread.start()
                stop_thread.join(timeout=3)  # 等待最多3秒
            
            # 获取账号信息（包括cookies）
            account_info = client.get_account_info(account_id)
            if not account_info:
                raise Exception(f"Account {account_id} not found")
            
            cookies_json = account_info.get('cookies')
            if not cookies_json:
                raise Exception(f"Account {account_id} has no cookies")
            
            # 解析cookies
            if isinstance(cookies_json, str):
                cookies_data = json.loads(cookies_json)
            else:
                cookies_data = cookies_json
            
            # 保存cookies到临时文件（同时保存到持久化目录用于调试）
            account_file = save_cookies_to_temp(cookies_data, account_id)
            
            # 创建停止事件
            import threading
            stop_event = threading.Event()
            
            # 在后台启动监听
            def run_listen():
                try:
                    asyncio.run(execute_listen(account_id, account_file, client, stop_event))
                except Exception as e:
                    douyin_logger.error(f"Listen error for account {account_id}: {e}")
                    if account_id in _listening_tasks:
                        del _listening_tasks[account_id]
            
            listen_thread = threading.Thread(target=run_listen, daemon=True)
            listen_thread.start()
            _listening_tasks[account_id] = {
                'thread': listen_thread,
                'stop_event': stop_event
            }
            
            # 更新任务状态为运行中
            client.update_task_status(task_id, 'listen', 'running')
            douyin_logger.success(f"Listen task {task_id} started for account {account_id}")
            
        elif action == 'stop':
            # 停止监听 - 立即执行，不在后台线程
            if account_id in _listening_tasks:
                # 直接在主线程中停止监听服务，确保立即关闭浏览器
                try:
                    await stop_listen_service(account_id)
                    douyin_logger.success(f"Listen task {task_id} stopped for account {account_id}, browser closed")
                except Exception as e:
                    douyin_logger.error(f"Error stopping listen service: {e}")
                    # 即使出错也更新任务状态
                
                client.update_task_status(task_id, 'listen', 'stopped')
            else:
                douyin_logger.warning(f"No listening service found for account {account_id}")
                client.update_task_status(task_id, 'listen', 'stopped')
        else:
            raise Exception(f"Unknown listen action: {action}")
            
    except Exception as e:
        douyin_logger.error(f"Listen task {task_id} failed: {e}")
        client.update_task_status(task_id, 'listen', 'failed', error_message=str(e))
        if account_id in _listening_tasks:
            await stop_listen_service(account_id)
        raise

async def stop_listen_service(account_id: int):
    """停止监听服务 - 立即关闭浏览器"""
    if account_id not in _listening_tasks:
        return
    
    task_info = _listening_tasks[account_id]
    
    # 设置停止事件，让监听循环知道要停止
    if 'stop_event' in task_info:
        task_info['stop_event'].set()
    
    # 立即关闭浏览器资源，不等待监听循环结束
    try:
        # 先关闭页面
        if 'page' in task_info and task_info['page']:
            try:
                await asyncio.wait_for(task_info['page'].close(), timeout=2.0)
            except (asyncio.TimeoutError, Exception) as e:
                douyin_logger.warning(f"Timeout or error closing page for account {account_id}: {e}")
        
        # 关闭上下文
        if 'context' in task_info and task_info['context']:
            try:
                await asyncio.wait_for(task_info['context'].close(), timeout=2.0)
            except (asyncio.TimeoutError, Exception) as e:
                douyin_logger.warning(f"Timeout or error closing context for account {account_id}: {e}")
        
        # 关闭浏览器
        if 'browser' in task_info and task_info['browser']:
            try:
                await asyncio.wait_for(task_info['browser'].close(), timeout=2.0)
            except (asyncio.TimeoutError, Exception) as e:
                douyin_logger.warning(f"Timeout or error closing browser for account {account_id}: {e}")
        
        # 停止playwright
        if 'playwright' in task_info and task_info['playwright']:
            try:
                await asyncio.wait_for(task_info['playwright'].stop(), timeout=2.0)
            except (asyncio.TimeoutError, Exception) as e:
                douyin_logger.warning(f"Timeout or error stopping playwright for account {account_id}: {e}")
    except Exception as e:
        douyin_logger.error(f"Error closing browser resources for account {account_id}: {e}")
    
    # 从字典中删除
    if account_id in _listening_tasks:
        del _listening_tasks[account_id]
    douyin_logger.info(f"Listen service stopped for account {account_id}, browser closed")

async def execute_listen(account_id: int, account_file: str, client, stop_event):
    """执行消息监听"""
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        from listener.douyin_listener.main import open_douyin_chat
        from playwright.async_api import async_playwright
        
        # 验证account_file是否存在
        if not os.path.exists(account_file):
            douyin_logger.error(f"Account file not found: {account_file} for account {account_id}")
            if account_id in _listening_tasks:
                del _listening_tasks[account_id]
            return
        
        douyin_logger.info(f"[LISTEN] Starting listen for account {account_id}, using file: {account_file}")
        
        playwright = await async_playwright().start()
        
        try:
            page = await open_douyin_chat(playwright, account_file)
            douyin_logger.info(f"[LISTEN] Browser opened successfully for account {account_id}")
            
            # 获取浏览器和上下文对象
            if account_id in _listening_tasks:
                context = page.context
                browser = context.browser
                _listening_tasks[account_id].update({
                    'playwright': playwright,
                    'browser': browser,
                    'context': context,
                    'page': page
                })
        except Exception as e:
            douyin_logger.error(f"[LISTEN] Failed to open browser for account {account_id}: {e}", exc_info=True)
            if account_id in _listening_tasks:
                del _listening_tasks[account_id]
            if playwright:
                await playwright.stop()
            return
        
        douyin_logger.info(f"[LISTEN] Started listening for account {account_id}")
        
        # 持续监听消息 - 定期解析所有会话的消息
        while account_id in _listening_tasks and not stop_event.is_set():
            try:
                # 检查停止事件
                if stop_event.is_set():
                    douyin_logger.info(f"[LISTEN] Stop event received for account {account_id}")
                    break
                
                # 解析消息（完全复刻原始逻辑，遍历所有会话）
                await parse_messages(page, account_id)
                
                # 等待时检查停止事件（缩短检查间隔，更快响应停止）
                for _ in range(20):  # 10秒，每0.5秒检查一次，更快响应停止
                    if stop_event.is_set() or account_id not in _listening_tasks:
                        break
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                douyin_logger.error(f"Parse messages error for account {account_id}: {e}", exc_info=True)
                # 等待时检查停止事件（缩短检查间隔，更快响应停止）
                for _ in range(20):  # 10秒，每0.5秒检查一次，更快响应停止
                    if stop_event.is_set() or account_id not in _listening_tasks:
                        break
                    await asyncio.sleep(0.5)
        
        douyin_logger.info(f"[LISTEN] Stopping listen for account {account_id}")
                    
    except Exception as e:
        douyin_logger.error(f"Listen execution error for account {account_id}: {e}", exc_info=True)
    finally:
        # 清理资源
        try:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
        except Exception as e:
            douyin_logger.error(f"Error cleaning up browser resources for account {account_id}: {e}")
        
        if account_id in _listening_tasks:
            del _listening_tasks[account_id]

async def parse_messages(page, account_id: int):
    """解析消息并存储到数据库"""
    try:
        from listener.douyin_listener.main import _get_first_dialog_snapshot, _wait_conversation_switched
        
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
        douyin_logger.debug(f"[*] 当前消息会话条数: {total}")
        
        for idx, item in enumerate(conv_items):
            try:
                # 先拿到用户名用于日志，再做点击
                name_el = await item.query_selector("span.item-header-name-vL_79m")
                if not name_el:
                    continue
                user_name = (await name_el.inner_text()).strip()
                if not user_name:
                    continue
                
                # 点击前记录当前第一条消息快照
                prev_snapshot = await _get_first_dialog_snapshot(page)
                
                # 对单条会话的点击 + 切换检测增加重试
                switched = False
                for attempt in range(3):
                    try:
                        await item.scroll_into_view_if_needed()
                        await item.click(force=True, timeout=8000)
                    except Exception as click_e:
                        douyin_logger.debug(f"[!] 第 {idx + 1} 条会话（{user_name}）第 {attempt + 1} 次点击失败: {click_e}")
                        await asyncio.sleep(0.5)
                        continue
                    
                    # 等待会话真正切换成功
                    switched = await _wait_conversation_switched(page, user_name, prev_snapshot, timeout=8.0)
                    if switched:
                        break
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
                    
                    # 保存消息到数据库（通过center API）
                    saved = save_message_to_center(account_id, user_name, text, is_me, current_time)
                    if saved:
                        douyin_logger.info(f"[DIALOG] 会话用户: {user_name} | 方向: {'我' if is_me else '对方'} | 时间: {current_time} | 文本: {text}")
                
                # 为避免触发风控，可在会话之间稍微停顿
                await asyncio.sleep(2)
                
            except Exception as sub_e:
                douyin_logger.error(f"[!] 处理第 {idx + 1} 条会话时出错: {sub_e}")
                continue
                
    except Exception as e:
        douyin_logger.error(f"[!] 无法解析消息列表区域或对话内容: {e}")

def save_message_to_center(account_id: int, user_name: str, text: str, is_me: bool, message_time: str):
    """保存消息到center服务器（通过HTTP API）"""
    try:
        import requests
        # 默认连接本机中心服务，如需连接远程中心，可设置环境变量 CENTER_BASE_URL
        center_base_url = os.getenv('CENTER_BASE_URL', 'http://127.0.0.1:8080')
        
        # 通过HTTP API保存消息
        response = requests.post(
            f'{center_base_url}/api/messages',
            json={
                'account_id': account_id,
                'user_name': user_name,
                'text': text,
                'is_me': is_me,
                'message_time': message_time
            },
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            if data.get('code') in [200, 201]:
                # 如果是重复消息，也返回True（表示已处理）
                if data.get('data', {}).get('duplicate'):
                    return True
                return True
            else:
                douyin_logger.warning(f"Failed to save message: {data.get('message')}")
                return False
        else:
            douyin_logger.warning(f"Failed to save message: HTTP {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        douyin_logger.error(f"Failed to save message to center (network error): {e}")
        return False
    except Exception as e:
        douyin_logger.error(f"Failed to save message to center: {e}")
        return False

def save_cookies_to_temp(cookies_data: Dict, account_id: Optional[int] = None) -> str:
    """
    保存cookies到临时文件，并修复格式问题
    
    Args:
        cookies_data: cookies 数据字典
        account_id: 账号ID，如果提供则保存到持久化目录，否则保存到临时文件
        
    Returns:
        str: 保存的文件路径
    """
    # 修复storageState格式问题
    if isinstance(cookies_data, dict):
        # 确保origins是列表
        if 'origins' in cookies_data and isinstance(cookies_data['origins'], list):
            for origin in cookies_data['origins']:
                if isinstance(origin, dict):
                    # 修复localStorage格式：确保是数组而不是对象
                    if 'localStorage' in origin:
                        if isinstance(origin['localStorage'], dict):
                            # 如果是对象，转换为数组格式
                            localStorage_list = []
                            for key, value in origin['localStorage'].items():
                                localStorage_list.append({"name": key, "value": str(value)})
                            origin['localStorage'] = localStorage_list
                        elif not isinstance(origin['localStorage'], list):
                            # 如果不是数组也不是对象，设为空数组
                            origin['localStorage'] = []
        
        # 确保cookies是列表
        if 'cookies' in cookies_data and not isinstance(cookies_data['cookies'], list):
            if isinstance(cookies_data['cookies'], dict):
                # 如果是对象，尝试转换（但通常cookies应该是列表）
                cookies_data['cookies'] = []
            elif cookies_data['cookies'] is None:
                cookies_data['cookies'] = []
    
    cookies_json = json.dumps(cookies_data, ensure_ascii=False)
    
    # 如果提供了 account_id，保存到持久化目录（用于调试和检查）
    if account_id:
        from pathlib import Path
        from conf import BASE_DIR
        cookies_dir = Path(BASE_DIR) / "cookies" / "douyin_uploader"
        cookies_dir.mkdir(parents=True, exist_ok=True)
        account_file = cookies_dir / f"account_{account_id}.json"
        # 确保保存为格式化的 JSON（便于调试）
        import json as json_module
        with open(account_file, 'w', encoding='utf-8') as f:
            json_module.dump(cookies_data, f, ensure_ascii=False, indent=2)
        douyin_logger.info(f"Cookies saved to persistent file: {account_file}")
        # 验证文件是否保存成功
        if not account_file.exists() or account_file.stat().st_size == 0:
            douyin_logger.error(f"Failed to save cookies to {account_file}")
            raise Exception(f"Failed to save cookies file: {account_file}")
        return str(account_file)
    else:
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        temp_file.write(cookies_json)
        temp_file.close()
        return temp_file.name

def download_video(video_url: str) -> str:
    """
    下载视频文件
    
    Args:
        video_url: 视频URL（可以是http/https URL或file://路径）
        
    Returns:
        str: 本地文件路径
    """
    if video_url.startswith('file://'):
        # 本地文件路径
        file_path = video_url[7:]  # 移除 'file://' 前缀
        if os.path.exists(file_path):
            return file_path
        else:
            raise FileNotFoundError(f"Video file not found: {file_path}")
    elif video_url.startswith('http://') or video_url.startswith('https://'):
        # HTTP URL，需要下载
        import requests
        response = requests.get(video_url, stream=True, timeout=300)
        response.raise_for_status()
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        temp_file.close()
        
        douyin_logger.info(f"Video downloaded to: {temp_file.name}")
        return temp_file.name
    else:
        # 假设是本地路径
        if os.path.exists(video_url):
            return video_url
        else:
            raise FileNotFoundError(f"Video file not found: {video_url}")

def download_thumbnail(thumbnail_url: str) -> str:
    """
    下载缩略图
    
    Args:
        thumbnail_url: 缩略图URL
        
    Returns:
        str: 本地文件路径
    """
    if thumbnail_url.startswith('http://') or thumbnail_url.startswith('https://'):
        import requests
        response = requests.get(thumbnail_url, timeout=30)
        response.raise_for_status()
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        temp_file.write(response.content)
        temp_file.close()
        
        return temp_file.name
    else:
        # 假设是本地路径
        if os.path.exists(thumbnail_url):
            return thumbnail_url
        else:
            raise FileNotFoundError(f"Thumbnail file not found: {thumbnail_url}")

async def execute_upload(title: str, file_path: str, tags: list, publish_date, account_file: str, thumbnail_path: str = None):
    """执行视频上传"""
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
            return updated_cookies
    except Exception as e:
        douyin_logger.error(f"Failed to read updated cookies: {e}")
    
    return None

async def execute_send_message(account_file: str, target_user: str, message: str) -> bool:
    """执行发送消息"""
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
                    if success:
                        douyin_logger.success(f"Message sent to {target_user}: {message}")
                    return success
                    
            except Exception as e:
                douyin_logger.debug(f"Find user error: {e}")
                continue
        
        douyin_logger.error(f"User {target_user} not found")
        return False

def cleanup_temp_files(file_paths: list):
    """清理临时文件"""
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                douyin_logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                douyin_logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

def create_task_handler(client):
    """
    创建任务处理函数
    
    Args:
        client: CenterClient实例
        
    Returns:
        function: 任务处理函数
    """
    def handle_task(task: Dict, client_instance):
        """处理任务"""
        task_type = task.get('type')
        
        if task_type == 'video':
            asyncio.run(handle_video_task(task, client_instance))
        elif task_type == 'chat':
            asyncio.run(handle_chat_task(task, client_instance))
        elif task_type == 'listen':
            asyncio.run(handle_listen_task(task, client_instance))
        else:
            douyin_logger.error(f"Unknown task type: {task_type}")
    
    return handle_task

