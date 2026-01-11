"""
任务执行服务
在后端直接执行视频上传、消息监听、消息回复等任务
所有数据从数据库获取
"""
import os
import json
import asyncio
import tempfile
import threading
import requests
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from models import Account, VideoTask, ChatTask, ListenTask, Message
from db import get_db
from services.config import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS, BASE_DIR

# 导入本地的上传器和监听器（已迁移到backend目录）
try:
    from uploader.douyin_uploader.main import DouYinVideo
    from listener.douyin_listener.main import (
        open_douyin_chat, 
        _send_chat_message, 
        _get_first_dialog_snapshot, 
        _wait_conversation_switched
    )
    from utils.base_social_media import set_init_script
    from utils.log import douyin_logger
except ImportError as e:
    import logging
    logging.warning(f"无法导入模块: {e}")
    logging.warning("请确保uploader、listener和utils目录存在")
    # 创建一个简单的logger作为fallback
    douyin_logger = logging.getLogger('douyin')
    douyin_logger.setLevel(logging.INFO)
    DouYinVideo = None
    open_douyin_chat = None
    _send_chat_message = None
    _get_first_dialog_snapshot = None
    _wait_conversation_switched = None
    set_init_script = None

# 全局变量：存储监听任务状态
# 格式: {account_id: {'thread': thread, 'playwright': playwright, 'browser': browser, 'context': context, 'page': page, 'stop_event': event}}
_listening_tasks = {}


def get_account_from_db(account_id: int, db: Session) -> Optional[Dict]:
    """
    从数据库获取账号信息（包括cookies）
    
    Args:
        account_id: 账号ID
        db: 数据库会话
        
    Returns:
        Optional[Dict]: 账号信息字典
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        return None
    
    return {
        'id': account.id,
        'device_id': account.device_id,
        'account_name': account.account_name,
        'platform': account.platform,
        'login_status': account.login_status,
        'last_login_time': account.last_login_time.isoformat() if account.last_login_time else None,
        'cookies': account.cookies  # JSON字符串
    }


def save_cookies_to_db(account_id: int, cookies: Dict, db: Session):
    """
    保存cookies到数据库
    
    Args:
        account_id: 账号ID
        cookies: cookies数据（字典或JSON字符串）
        db: 数据库会话
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        return
    
    # 转换为JSON字符串
    if isinstance(cookies, dict):
        cookies_json = json.dumps(cookies, ensure_ascii=False)
    else:
        cookies_json = cookies
    
    account.cookies = cookies_json
    account.login_status = 'logged_in'
    account.last_login_time = datetime.now()
    account.updated_at = datetime.now()
    db.commit()


def save_cookies_to_temp(cookies_data: Dict, account_id: Optional[int] = None) -> str:
    """
    保存cookies到临时文件
    
    Args:
        cookies_data: cookies 数据字典
        account_id: 账号ID
        
    Returns:
        str: 保存的文件路径
    """
    # 修复storageState格式问题
    if isinstance(cookies_data, dict):
        # 确保cookies是列表
        if 'cookies' not in cookies_data:
            cookies_data['cookies'] = []
        elif not isinstance(cookies_data['cookies'], list):
            if isinstance(cookies_data['cookies'], dict):
                cookies_data['cookies'] = []
            elif cookies_data['cookies'] is None:
                cookies_data['cookies'] = []
        
        # 确保origins是列表
        if 'origins' not in cookies_data:
            cookies_data['origins'] = []
        elif not isinstance(cookies_data['origins'], list):
            cookies_data['origins'] = []
        
        # 处理origins中的localStorage格式
        for origin in cookies_data['origins']:
            if isinstance(origin, dict):
                # 确保有origin字段
                if 'origin' not in origin:
                    continue
                
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
                else:
                    # 如果没有localStorage字段，添加空数组
                    origin['localStorage'] = []
        
        # 如果origins为空，但cookies不为空，尝试从cookies推断origins
        if not cookies_data['origins'] and cookies_data['cookies']:
            # 从cookies中提取域名
            domains = set()
            for cookie in cookies_data['cookies']:
                if isinstance(cookie, dict) and 'domain' in cookie:
                    domain = cookie['domain']
                    # 移除前导点
                    if domain.startswith('.'):
                        domain = domain[1:]
                    # 构建完整的origin URL
                    if 'douyin.com' in domain:
                        domains.add(f"https://{domain}")
                        domains.add(f"https://creator.{domain}")
            
            # 为每个域名创建origin条目
            for domain in domains:
                cookies_data['origins'].append({
                    'origin': domain,
                    'localStorage': []
                })
        
        # 确保cookies中的每个cookie都有必要的字段
        for cookie in cookies_data['cookies']:
            if isinstance(cookie, dict):
                # 确保有domain字段
                if 'domain' not in cookie:
                    # 如果没有domain，尝试从name推断（某些cookie可能没有domain）
                    pass
                # 确保path字段存在
                if 'path' not in cookie:
                    cookie['path'] = '/'
                # 确保name和value存在
                if 'name' not in cookie or 'value' not in cookie:
                    continue
    
    cookies_json = json.dumps(cookies_data, ensure_ascii=False)
    
    # 保存到临时文件
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
    temp_file.write(cookies_json)
    temp_file.close()
    
    if douyin_logger:
        douyin_logger.debug(f"Cookies saved to temp file: {temp_file.name}")
        douyin_logger.debug(f"Cookies format: has_cookies={bool(cookies_data.get('cookies'))}, has_origins={bool(cookies_data.get('origins'))}")
    
    return temp_file.name


async def execute_video_upload(task_id: int):
    """
    执行视频上传任务
    
    Args:
        task_id: 任务ID
    """
    # 使用独立的数据库会话来更新状态，避免长时间执行导致连接超时
    with get_db() as db:
        task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
        if not task:
            if douyin_logger:
                douyin_logger.error(f"Video task {task_id} not found")
            return
        
        # 更新任务状态为处理中
        task.status = 'uploading'
        task.started_at = datetime.now()
        task.progress = 0
        db.commit()
        if douyin_logger:
            douyin_logger.info(f"Video task {task_id} status updated to 'uploading'")
        
        try:
            # 获取账号信息（包括cookies）
            account_info = get_account_from_db(task.account_id, db)
            if not account_info:
                raise Exception(f"Account {task.account_id} not found")
            
            cookies_json = account_info.get('cookies')
            if not cookies_json:
                raise Exception(f"Account {task.account_id} has no cookies")
            
            # 输出cookies摘要（用于调试）
            cookies_preview = str(cookies_json)[:200] + "..." if len(str(cookies_json)) > 200 else str(cookies_json)
            preview_msg = f"Account {task.account_id} cookies preview: {cookies_preview}"
            print(f"[COOKIES] {preview_msg}")
            if douyin_logger:
                douyin_logger.info(f"[COOKIES] {preview_msg}")
            
            # 解析cookies
            if isinstance(cookies_json, str):
                try:
                    cookies_data = json.loads(cookies_json)
                except json.JSONDecodeError as e:
                    raise Exception(f"Invalid cookies JSON format: {e}")
            else:
                cookies_data = cookies_json
            
            # 验证cookies格式
            if not isinstance(cookies_data, dict):
                raise Exception("Cookies must be a dictionary (storage_state format)")
            
            # 检查cookies是否为空
            cookies_list = cookies_data.get('cookies', [])
            origins_list = cookies_data.get('origins', [])
            has_cookies = isinstance(cookies_list, list) and len(cookies_list) > 0
            has_origins = isinstance(origins_list, list) and len(origins_list) > 0
            
            if not has_cookies and not has_origins:
                raise Exception("Cookies data is empty or invalid format")
            
            # 检查关键cookies是否存在
            cookie_names = [c.get('name', '') for c in cookies_list if isinstance(c, dict)]
            important_cookies = ['sessionid', 'passport_auth', 'passport_csrf_token', 'sid_guard', 'uid_tt', 'sid_tt']
            missing_important = [name for name in important_cookies if name not in cookie_names]
            
            # 输出cookies诊断信息（同时使用logger和print确保能看到）
            cookies_info_msg = f"📦 Loaded cookies for account {task.account_id}: {len(cookies_list)} cookies, {len(origins_list)} origins"
            print(f"[COOKIES] {cookies_info_msg}")
            if douyin_logger:
                douyin_logger.info(cookies_info_msg)
            
            if missing_important:
                warning_msg = f"⚠️ Missing important cookies: {missing_important}. This may cause login failure."
                print(f"[COOKIES WARNING] {warning_msg}")
                if douyin_logger:
                    douyin_logger.warning(warning_msg)
                    douyin_logger.warning("⚠️ 建议：使用Network标签页获取完整的HttpOnly cookies")
                    douyin_logger.warning("⚠️ 当前cookies可能不完整，发布视频时可能会失败")
            
            # 检查cookies的domain
            domains = set()
            for cookie in cookies_list:
                if isinstance(cookie, dict) and 'domain' in cookie:
                    domains.add(cookie['domain'])
            if domains:
                domains_msg = f"Cookie domains: {list(domains)[:5]}..."
                print(f"[COOKIES] {domains_msg}")
                if douyin_logger:
                    douyin_logger.info(domains_msg)  # 改为info级别确保输出
            
            # 显示cookies名称（用于调试）
            if cookies_list:
                cookie_names_preview = [c.get('name', '') for c in cookies_list[:10] if isinstance(c, dict)]
                names_msg = f"Cookie names (first 10): {cookie_names_preview}"
                print(f"[COOKIES] {names_msg}")
                if douyin_logger:
                    douyin_logger.info(names_msg)  # 改为info级别确保输出
            
            # 保存cookies到临时文件（会自动修复格式）
            account_file = save_cookies_to_temp(cookies_data, task.account_id)
            
            # 验证临时文件内容
            try:
                with open(account_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    if douyin_logger:
                        douyin_logger.debug(f"Verified temp file: {len(saved_data.get('cookies', []))} cookies, {len(saved_data.get('origins', []))} origins")
            except Exception as e:
                if douyin_logger:
                    douyin_logger.error(f"Failed to verify temp file: {e}")
            
            # 预验证cookies有效性（可选，如果cookies可能失效）
            # 注意：这会增加执行时间，但可以提前发现问题
            # 如果cookies经常失效，可以启用这个检查
            # try:
            #     from uploader.douyin_uploader.main import cookie_auth
            #     is_valid = await cookie_auth(account_file)
            #     if not is_valid:
            #         raise Exception("Cookies验证失败，请重新登录获取新的cookies")
            # except Exception as e:
            #     if douyin_logger:
            #         douyin_logger.warning(f"Cookies pre-validation failed: {e}")
            #     # 不阻止执行，让上传器自己验证
            
            # 解析tags
            tags = []
            if task.video_tags:
                if isinstance(task.video_tags, str):
                    try:
                        tags = json.loads(task.video_tags)
                    except:
                        tags = [tag.strip() for tag in task.video_tags.split(',') if tag.strip()]
                elif isinstance(task.video_tags, list):
                    tags = task.video_tags
            
            # 处理视频URL（可能是file://路径、http URL或本地路径）
            video_path = task.video_url
            temp_video_file = None
            
            if video_path.startswith('file://'):
                video_path = video_path[7:]  # 移除 'file://' 前缀
            elif video_path.startswith('http://') or video_path.startswith('https://'):
                # HTTP URL，需要下载到临时文件
                import requests
                if douyin_logger:
                    douyin_logger.info(f"Downloading video from URL: {video_path}")
                
                response = requests.get(video_path, stream=True, timeout=300)
                response.raise_for_status()
                
                # 保存到临时文件
                temp_video_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                for chunk in response.iter_content(chunk_size=8192):
                    temp_video_file.write(chunk)
                temp_video_file.close()
                
                video_path = temp_video_file.name
                if douyin_logger:
                    douyin_logger.info(f"Video downloaded to: {video_path}")
            elif video_path.startswith('/'):
                # 相对路径，可能是 /uploads/videos/xxx 格式
                # 转换为绝对路径
                backend_dir = Path(__file__).parent.parent
                if video_path.startswith('/uploads/'):
                    video_path = str(backend_dir.parent / video_path.lstrip('/'))
                else:
                    video_path = str(backend_dir / video_path.lstrip('/'))
            
            # 检查视频文件是否存在
            if not os.path.exists(video_path):
                raise Exception(f"视频文件不存在: {video_path}")
            
            # 执行上传
            if douyin_logger:
                douyin_logger.info(f"Starting upload: title={task.video_title}, video_path={video_path}, tags={tags}")
            
            # 执行上传
            if douyin_logger:
                douyin_logger.info(f"开始执行视频上传任务 {task_id}...")
            
            updated_cookies = await execute_upload(
                task.video_title or '',
                video_path,  # 使用处理后的路径
                tags,
                task.publish_date,
                account_file,
                task.thumbnail_url,
                task.account_id
            )
            
            # 明确记录从 uploader 返回的结果
            print(f"[TASK STATUS] 任务 {task_id} 的视频上传已完成，收到返回结果: {type(updated_cookies).__name__}")
            if douyin_logger:
                douyin_logger.info(f"视频上传任务 {task_id} 执行完成，收到 uploader 返回结果，开始更新任务状态...")
                if updated_cookies:
                    if isinstance(updated_cookies, dict) and ('cookies' in updated_cookies or 'origins' in updated_cookies):
                        douyin_logger.info(f"收到有效的 cookies 数据，将更新到数据库")
                    elif isinstance(updated_cookies, dict) and updated_cookies.get('upload_success'):
                        douyin_logger.info(f"收到上传成功标记，视频已成功发布")
                    else:
                        douyin_logger.info(f"收到其他格式的返回数据: {updated_cookies}")
                else:
                    douyin_logger.warning(f"未收到返回数据，但将继续更新任务状态")
            
            # 重新查询任务，确保获取最新的对象（因为 execute_upload 可能执行时间较长）
            # 使用新的查询确保获取最新的任务对象
            db.expire_all()  # 清除所有对象的缓存
            task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
            if not task:
                if douyin_logger:
                    douyin_logger.error(f"Video task {task_id} not found after upload")
                return
            
            # 更新cookies到数据库
            # updated_cookies 可能是 cookies 字典，也可能是 {"upload_success": True} 标记
            if updated_cookies:
                # 检查是否是有效的cookies格式（包含cookies或origins字段）
                if isinstance(updated_cookies, dict):
                    if 'cookies' in updated_cookies or 'origins' in updated_cookies:
                        # 这是有效的cookies格式
                        if douyin_logger:
                            douyin_logger.info(f"更新账号 {task.account_id} 的 cookies 到数据库...")
                        save_cookies_to_db(task.account_id, updated_cookies, db)
                        if douyin_logger:
                            douyin_logger.success(f"账号 {task.account_id} 的 cookies 已更新到数据库")
                    elif updated_cookies.get('upload_success'):
                        # 这是上传成功的标记，但cookies读取失败
                        if douyin_logger:
                            douyin_logger.warning(f"Upload successful but cookies not updated for account {task.account_id}")
                else:
                    # 其他格式，尝试保存
                    save_cookies_to_db(task.account_id, updated_cookies, db)
            
            # 无论cookies是否更新成功，都要更新任务状态为完成
            # 因为视频已经发布成功了（execute_upload 正常返回表示上传成功）
            print(f"[TASK STATUS] 视频发布成功，更新任务 {task_id} 状态为 completed...")
            if douyin_logger:
                douyin_logger.info(f"视频发布成功，更新任务 {task_id} 状态为 completed...")
            
            # 更新任务状态
            task.status = 'completed'
            task.progress = 100
            task.completed_at = datetime.now()
            
            # 确保提交到数据库
            try:
                db.commit()
                db.flush()  # 强制刷新到数据库
                print(f"[TASK STATUS] 任务 {task_id} 状态已提交到数据库: status=completed, progress=100")
                if douyin_logger:
                    douyin_logger.info(f"任务 {task_id} 状态已提交到数据库: status=completed, progress=100")
            except Exception as commit_error:
                print(f"[TASK STATUS] 提交任务状态到数据库失败: {commit_error}")
                if douyin_logger:
                    douyin_logger.error(f"提交任务状态到数据库失败: {commit_error}")
                # 尝试回滚后重新提交
                db.rollback()
                task.status = 'completed'
                task.progress = 100
                task.completed_at = datetime.now()
                db.commit()
                db.flush()
                print(f"[TASK STATUS] 任务 {task_id} 状态已重新提交到数据库")
            
            # 再次刷新，确保状态已保存
            db.refresh(task)
            
            print(f"[TASK STATUS] ✅ 任务 {task_id} 状态更新成功: status={task.status}, progress={task.progress}, completed_at={task.completed_at}")
            if douyin_logger:
                douyin_logger.success(f"Video task {task_id} completed successfully")
                douyin_logger.info(f"Task {task_id} final status: {task.status}, progress: {task.progress}, completed_at: {task.completed_at}")
            
            # 验证状态是否真的更新成功
            if task.status != 'completed':
                if douyin_logger:
                    douyin_logger.error(f"Warning: Task {task_id} status update may have failed. Current status: {task.status}")
                # 尝试再次更新
                task.status = 'completed'
                task.progress = 100
                task.completed_at = datetime.now()
                db.commit()
                db.flush()
                db.refresh(task)
                
                # 最终验证
                if task.status != 'completed':
                    if douyin_logger:
                        douyin_logger.error(f"ERROR: Failed to update task {task_id} status to completed after retry. Current status: {task.status}")
                else:
                    if douyin_logger:
                        douyin_logger.success(f"Task {task_id} status updated to completed after retry")
            
            # 清理临时文件
            try:
                if os.path.exists(account_file):
                    os.remove(account_file)
                if temp_video_file and os.path.exists(temp_video_file.name):
                    os.remove(temp_video_file.name)
            except:
                pass
                
        except Exception as e:
            if douyin_logger:
                douyin_logger.error(f"Video task {task_id} failed: {e}")
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.now()
            db.commit()
            
            # 清理临时文件（即使失败也要清理）
            try:
                if 'account_file' in locals() and os.path.exists(account_file):
                    os.remove(account_file)
                if 'temp_video_file' in locals() and temp_video_file and os.path.exists(temp_video_file.name):
                    os.remove(temp_video_file.name)
            except:
                pass
            
            # 清理临时文件（即使失败也要清理）
            try:
                if 'account_file' in locals() and os.path.exists(account_file):
                    os.remove(account_file)
                if 'temp_video_file' in locals() and temp_video_file and os.path.exists(temp_video_file.name):
                    os.remove(temp_video_file.name)
            except:
                pass


async def execute_upload(title: str, file_path: str, tags: list, publish_date, account_file: str, thumbnail_path: str = None, account_id: int = None):
    """执行视频上传"""
    try:
        app = DouYinVideo(
            title=title,
            file_path=file_path,
            tags=tags,
            publish_date=publish_date,
            account_file=account_file,
            thumbnail_path=thumbnail_path,
            account_id=account_id  # 传递 account_id，用于自动登录时更新数据库
        )
        # 执行上传，upload 方法现在会返回更新后的cookies
        print(f"[UPLOAD] 开始调用 DouYinVideo.main() 执行视频上传...")
        if douyin_logger:
            douyin_logger.info(f"开始调用 DouYinVideo.main() 执行视频上传: {title}")
        
        updated_cookies = await app.main()
        
        print(f"[UPLOAD] DouYinVideo.main() 执行完成，返回结果类型: {type(updated_cookies).__name__}")
        if douyin_logger:
            douyin_logger.success(f"Video uploaded successfully: {title}")
            if updated_cookies:
                if isinstance(updated_cookies, dict) and ('cookies' in updated_cookies or 'origins' in updated_cookies):
                    douyin_logger.info(f"收到有效的 cookies 数据，包含 {len(updated_cookies.get('cookies', []))} 个 cookies")
                elif isinstance(updated_cookies, dict) and updated_cookies.get('upload_success'):
                    douyin_logger.info(f"收到上传成功标记")
                else:
                    douyin_logger.info(f"收到其他格式的返回数据")
            else:
                douyin_logger.warning(f"未收到返回数据，将尝试从文件读取")
        
        # 如果 upload 方法返回了cookies，直接返回
        if updated_cookies:
            print(f"[UPLOAD] 返回 uploader 的返回结果给 task_executor")
            return updated_cookies
        
        # 如果 upload 方法没有返回cookies，尝试从文件读取
        print(f"[UPLOAD] uploader 未返回数据，尝试从文件读取 cookies...")
        try:
            if os.path.exists(account_file):
                with open(account_file, 'r', encoding='utf-8') as f:
                    updated_cookies = json.load(f)
                print(f"[UPLOAD] 成功从文件读取 cookies，返回给 task_executor")
                if douyin_logger:
                    douyin_logger.info(f"成功从文件读取 cookies")
                return updated_cookies
        except Exception as e:
            if douyin_logger:
                douyin_logger.warning(f"Failed to read updated cookies: {e}, but upload was successful")
        
        # 即使读取cookies失败，也返回一个标记表示上传成功
        # 这样调用方可以知道上传已完成
        print(f"[UPLOAD] cookies 读取失败，返回成功标记给 task_executor")
        if douyin_logger:
            douyin_logger.info(f"返回上传成功标记给 task_executor，任务状态将被更新为 completed")
        return {"upload_success": True}
    except Exception as e:
        if douyin_logger:
            douyin_logger.error(f"Video upload failed: {e}")
        raise  # 重新抛出异常，让调用方处理


async def execute_chat_send(task_id: int):
    """
    执行消息发送任务
    
    Args:
        task_id: 任务ID
    """
    with get_db() as db:
        task = db.query(ChatTask).filter(ChatTask.id == task_id).first()
        if not task:
            if douyin_logger:
                douyin_logger.error(f"Chat task {task_id} not found")
            return
        
        # 更新任务状态为处理中
        task.status = 'sending'
        task.started_at = datetime.now()
        db.commit()
        
        try:
            # 获取账号信息（包括cookies）
            account_info = get_account_from_db(task.account_id, db)
            if not account_info:
                raise Exception(f"Account {task.account_id} not found")
            
            cookies_json = account_info.get('cookies')
            if not cookies_json:
                raise Exception(f"Account {task.account_id} has no cookies")
            
            # 解析cookies
            if isinstance(cookies_json, str):
                cookies_data = json.loads(cookies_json)
            else:
                cookies_data = cookies_json
            
            # 保存cookies到临时文件
            account_file = save_cookies_to_temp(cookies_data, task.account_id)
            
            # 执行发送消息
            success = await execute_send_message(account_file, task.target_user, task.message)
            
            if success:
                # 更新任务状态为完成
                task.status = 'completed'
                task.completed_at = datetime.now()
                db.commit()
                
                if douyin_logger:
                    douyin_logger.success(f"Chat task {task_id} completed")
            else:
                raise Exception("Failed to send message")
            
            # 清理临时文件
            try:
                if os.path.exists(account_file):
                    os.remove(account_file)
            except:
                pass
                
        except Exception as e:
            if douyin_logger:
                douyin_logger.error(f"Chat task {task_id} failed: {e}")
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.now()
            db.commit()


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
                    if success and douyin_logger:
                        douyin_logger.success(f"Message sent to {target_user}: {message}")
                    return success
                    
            except Exception as e:
                if douyin_logger:
                    douyin_logger.debug(f"Find user error: {e}")
                continue
        
        if douyin_logger:
            douyin_logger.error(f"User {target_user} not found")
        return False


async def execute_listen_start(task_id: int):
    """
    启动消息监听任务
    
    Args:
        task_id: 任务ID
    """
    with get_db() as db:
        task = db.query(ListenTask).filter(ListenTask.id == task_id).first()
        if not task:
            if douyin_logger:
                douyin_logger.error(f"Listen task {task_id} not found")
            return
        
        # 检查是否已经在监听
        if task.account_id in _listening_tasks:
            if douyin_logger:
                douyin_logger.warning(f"Listen service already running for account {task.account_id}, stopping it first")
            # 先停止旧的监听
            await stop_listen_service(task.account_id)
        
        # 更新任务状态为运行中
        task.status = 'running'
        task.started_at = datetime.now()
        db.commit()
        
        try:
            # 获取账号信息（包括cookies）
            account_info = get_account_from_db(task.account_id, db)
            if not account_info:
                raise Exception(f"Account {task.account_id} not found")
            
            cookies_json = account_info.get('cookies')
            if not cookies_json:
                raise Exception(f"Account {task.account_id} has no cookies")
            
            # 解析cookies
            if isinstance(cookies_json, str):
                cookies_data = json.loads(cookies_json)
            else:
                cookies_data = cookies_json
            
            # 保存cookies到临时文件
            account_file = save_cookies_to_temp(cookies_data, task.account_id)
            
            # 创建停止事件
            stop_event = threading.Event()
            
            # 在后台启动监听
            def run_listen():
                try:
                    asyncio.run(execute_listen(task.account_id, account_file, stop_event))
                except Exception as e:
                    if douyin_logger:
                        douyin_logger.error(f"Listen error for account {task.account_id}: {e}")
                    if task.account_id in _listening_tasks:
                        del _listening_tasks[task.account_id]
            
            listen_thread = threading.Thread(target=run_listen, daemon=True)
            listen_thread.start()
            _listening_tasks[task.account_id] = {
                'thread': listen_thread,
                'stop_event': stop_event,
                'task_id': task_id
            }
            
            if douyin_logger:
                douyin_logger.success(f"Listen task {task_id} started for account {task.account_id}")
                
        except Exception as e:
            if douyin_logger:
                douyin_logger.error(f"Listen task {task_id} failed: {e}")
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.now()
            db.commit()
            if task.account_id in _listening_tasks:
                await stop_listen_service(task.account_id)


async def execute_listen_stop(task_id: int):
    """
    停止消息监听任务
    
    Args:
        task_id: 任务ID
    """
    with get_db() as db:
        task = db.query(ListenTask).filter(ListenTask.id == task_id).first()
        if not task:
            if douyin_logger:
                douyin_logger.error(f"Listen task {task_id} not found")
            return
        
        if task.account_id in _listening_tasks:
            try:
                await stop_listen_service(task.account_id)
                if douyin_logger:
                    douyin_logger.success(f"Listen task {task_id} stopped for account {task.account_id}")
            except Exception as e:
                if douyin_logger:
                    douyin_logger.error(f"Error stopping listen service: {e}")
            
            task.status = 'stopped'
            task.completed_at = datetime.now()
            db.commit()
        else:
            if douyin_logger:
                douyin_logger.warning(f"No listening service found for account {task.account_id}")
            task.status = 'stopped'
            task.completed_at = datetime.now()
            db.commit()


async def stop_listen_service(account_id: int):
    """停止监听服务"""
    if account_id not in _listening_tasks:
        return
    
    task_info = _listening_tasks[account_id]
    
    # 设置停止事件
    if 'stop_event' in task_info:
        task_info['stop_event'].set()
    
    # 立即关闭浏览器资源
    try:
        if 'page' in task_info and task_info['page']:
            try:
                await asyncio.wait_for(task_info['page'].close(), timeout=2.0)
            except:
                pass
        
        if 'context' in task_info and task_info['context']:
            try:
                await asyncio.wait_for(task_info['context'].close(), timeout=2.0)
            except:
                pass
        
        if 'browser' in task_info and task_info['browser']:
            try:
                await asyncio.wait_for(task_info['browser'].close(), timeout=2.0)
            except:
                pass
        
        if 'playwright' in task_info and task_info['playwright']:
            try:
                await asyncio.wait_for(task_info['playwright'].stop(), timeout=2.0)
            except:
                pass
    except Exception as e:
        if douyin_logger:
            douyin_logger.error(f"Error closing browser resources for account {account_id}: {e}")
    
    # 从字典中删除
    if account_id in _listening_tasks:
        del _listening_tasks[account_id]
    
    if douyin_logger:
        douyin_logger.info(f"Listen service stopped for account {account_id}")


async def execute_listen(account_id: int, account_file: str, stop_event: threading.Event):
    """执行消息监听"""
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        # 验证account_file是否存在
        if not os.path.exists(account_file):
            if douyin_logger:
                douyin_logger.error(f"Account file not found: {account_file} for account {account_id}")
            if account_id in _listening_tasks:
                del _listening_tasks[account_id]
            return
        
        if douyin_logger:
            douyin_logger.info(f"[LISTEN] Starting listen for account {account_id}, using file: {account_file}")
        
        playwright = await async_playwright().start()
        
        try:
            page = await open_douyin_chat(playwright, account_file)
            if douyin_logger:
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
            if douyin_logger:
                douyin_logger.error(f"[LISTEN] Failed to open browser for account {account_id}: {e}")
            if account_id in _listening_tasks:
                del _listening_tasks[account_id]
            if playwright:
                await playwright.stop()
            return
        
        if douyin_logger:
            douyin_logger.info(f"[LISTEN] Started listening for account {account_id}")
        
        # 持续监听消息
        while account_id in _listening_tasks and not stop_event.is_set():
            try:
                # 检查停止事件
                if stop_event.is_set():
                    if douyin_logger:
                        douyin_logger.info(f"[LISTEN] Stop event received for account {account_id}")
                    break
                
                # 解析消息
                await parse_messages(page, account_id)
                
                # 等待时检查停止事件
                for _ in range(20):  # 10秒，每0.5秒检查一次
                    if stop_event.is_set() or account_id not in _listening_tasks:
                        break
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                if douyin_logger:
                    douyin_logger.error(f"Parse messages error for account {account_id}: {e}")
                # 等待时检查停止事件
                for _ in range(20):
                    if stop_event.is_set() or account_id not in _listening_tasks:
                        break
                    await asyncio.sleep(0.5)
        
        if douyin_logger:
            douyin_logger.info(f"[LISTEN] Stopping listen for account {account_id}")
                    
    except Exception as e:
        if douyin_logger:
            douyin_logger.error(f"Listen execution error for account {account_id}: {e}")
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
            if douyin_logger:
                douyin_logger.error(f"Error cleaning up browser resources for account {account_id}: {e}")
        
        if account_id in _listening_tasks:
            del _listening_tasks[account_id]


async def parse_messages(page, account_id: int):
    """解析消息并存储到数据库"""
    try:
        # 只取"当前激活"的聊天面板里的会话列表
        active_list_selector = "div.chat-content.semi-tabs-pane-active li.semi-list-item"
        try:
            await page.wait_for_selector(active_list_selector, timeout=20000)
        except:
            if douyin_logger:
                douyin_logger.warning("等待会话列表超时")
            return
        
        # 初始时记录一份稳定的会话句柄列表
        conv_items = await page.query_selector_all(active_list_selector)
        total = len(conv_items)
        if douyin_logger:
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
                        if douyin_logger:
                            douyin_logger.debug(f"[!] 第 {idx + 1} 条会话（{user_name}）第 {attempt + 1} 次点击失败: {click_e}")
                        await asyncio.sleep(0.5)
                        continue
                    
                    # 等待会话真正切换成功
                    switched = await _wait_conversation_switched(page, user_name, prev_snapshot, timeout=8.0)
                    if switched:
                        break
                    await asyncio.sleep(0.5)
                
                if not switched:
                    if douyin_logger:
                        douyin_logger.warning(f"[!] 会话 '{user_name}' 在多次重试后仍未成功切换，跳过该会话。")
                    continue
                
                await asyncio.sleep(0.5)
                
                # 解析右侧对话框中的聊天记录
                try:
                    await page.locator("div.box-item-dSA1TJ").first.wait_for(state="attached", timeout=10000)
                except Exception as wait_e:
                    if douyin_logger:
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
                    if saved and douyin_logger:
                        douyin_logger.info(f"[DIALOG] 会话用户: {user_name} | 方向: {'我' if is_me else '对方'} | 时间: {current_time} | 文本: {text}")
                
                # 为避免触发风控，可在会话之间稍微停顿
                await asyncio.sleep(2)
                
            except Exception as sub_e:
                if douyin_logger:
                    douyin_logger.error(f"[!] 处理第 {idx + 1} 条会话时出错: {sub_e}")
                continue
                
    except Exception as e:
        if douyin_logger:
            douyin_logger.error(f"[!] 无法解析消息列表区域或对话内容: {e}")


def save_message_to_db(account_id: int, user_name: str, text: str, is_me: bool, message_time: str):
    """保存消息到数据库"""
    try:
        with get_db() as db:
            # 检查是否已存在相同的消息（避免重复）
            existing = db.query(Message).filter(
                Message.account_id == account_id,
                Message.user_name == user_name,
                Message.text == text,
                Message.message_time == message_time
            ).first()
            
            if existing:
                return False  # 消息已存在
            
            # 插入新消息
            message = Message(
                account_id=account_id,
                user_name=user_name,
                text=text,
                is_me=1 if is_me else 0,
                message_time=message_time,
                timestamp=datetime.now()
            )
            db.add(message)
            db.commit()
            return True
    except Exception as e:
        if douyin_logger:
            douyin_logger.error(f"Failed to save message to database: {e}")
        return False

