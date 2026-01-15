"""
登录服务模块
使用Playwright实现扫码登录和自动获取cookies
"""
import asyncio
import json
import base64
import os
from typing import Optional, Dict
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
import threading

# 存储登录会话的字典 {account_id: {browser, context, page, qrcode, status}}
login_sessions: Dict[int, Dict] = {}

# 全局事件循环（用于在Flask中运行异步代码）
_async_loop = None
_loop_thread = None
_loop_lock = threading.Lock()

def get_or_create_loop():
    """获取或创建全局事件循环"""
    global _async_loop, _loop_thread
    
    with _loop_lock:
        if _async_loop is None or _async_loop.is_closed():
            def run_loop():
                global _async_loop
                _async_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_async_loop)
                _async_loop.run_forever()
            
            _loop_thread = threading.Thread(target=run_loop, daemon=True)
            _loop_thread.start()
            
            # 等待循环创建
            import time
            for _ in range(10):  # 最多等待1秒
                if _async_loop is not None and not _async_loop.is_closed():
                    break
                time.sleep(0.1)
    
    return _async_loop


async def start_login_session(account_id: int, platform: str = 'douyin') -> Dict:
    """
    启动登录会话，打开浏览器并获取二维码
    
    Args:
        account_id: 账号ID
        platform: 平台类型，默认'douyin'
    
    Returns:
        {
            'success': bool,
            'qrcode': str (base64编码的二维码图片),
            'message': str
        }
    """
    try:
        # 如果已有会话，先清理
        if account_id in login_sessions:
            await cleanup_login_session(account_id)
        
        # 启动浏览器（登录时强制使用非headless模式，让用户看到二维码）
        playwright = await async_playwright().start()
        browser_options = {
            'headless': False  # 登录时必须显示浏览器窗口，让用户扫码
        }
        if LOCAL_CHROME_PATH and os.path.exists(LOCAL_CHROME_PATH):
            browser_options['executable_path'] = LOCAL_CHROME_PATH
        
        browser = await playwright.chromium.launch(**browser_options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        
        # 根据平台选择登录URL
        if platform == 'douyin':
            login_url = 'https://creator.douyin.com/'
        else:
            login_url = 'https://creator.douyin.com/'  # 默认抖音
        
        await page.goto(login_url, wait_until='domcontentloaded', timeout=60000)
        
        # 等待页面加载
        try:
            await page.wait_for_load_state('networkidle', timeout=10000)
        except:
            # 如果networkidle超时，至少等待domcontentloaded
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=5000)
            except:
                pass
        
        # 额外等待页面渲染
        await asyncio.sleep(3)
        
        # 尝试点击"扫码登录"按钮
        try:
            # 查找扫码登录按钮，使用更安全的方式
            qr_button_selectors = [
                'text=扫码登录',
                'button:has-text("扫码登录")',
                '[class*="qr"]',
                '[class*="scan"]'
            ]
            
            clicked = False
            for selector in qr_button_selectors:
                try:
                    qr_button = page.locator(selector).first
                    count = await qr_button.count()
                    if count > 0:
                        await qr_button.click(timeout=5000)
                        await asyncio.sleep(2)
                        clicked = True
                        break
                except Exception as e:
                    print(f"尝试选择器 {selector} 失败: {e}")
                    continue
            
            if not clicked:
                print("未找到扫码登录按钮，可能已经在登录页面")
        except Exception as e:
            print(f"点击扫码登录按钮失败: {e}")
            # 继续尝试，可能已经在登录页面
        
        # 查找二维码图片
        qrcode_base64 = None
        max_retries = 10
        for i in range(max_retries):
            try:
                # 尝试多种选择器来查找二维码
                qr_selectors = [
                    'img[alt*="二维码"]',
                    'img[alt*="QR"]',
                    '.qrcode img',
                    '.qr-code img',
                    '[class*="qrcode"] img',
                    '[class*="qr-code"] img',
                    'canvas',
                ]
                
                for selector in qr_selectors:
                    qr_element = page.locator(selector).first
                    if await qr_element.count() > 0:
                        # 获取二维码图片的base64
                        qrcode_base64 = await qr_element.screenshot(type='png')
                        if qrcode_base64:
                            qrcode_base64 = base64.b64encode(qrcode_base64).decode('utf-8')
                            break
                
                if qrcode_base64:
                    break
                    
                await asyncio.sleep(1)
            except Exception as e:
                print(f"查找二维码失败 (尝试 {i+1}/{max_retries}): {e}")
                await asyncio.sleep(1)
        
        if not qrcode_base64:
            # 如果找不到二维码，尝试截图整个页面
            try:
                screenshot = await page.screenshot(type='png')
                qrcode_base64 = base64.b64encode(screenshot).decode('utf-8')
            except Exception as e:
                print(f"截图失败: {e}")
        
        # 保存会话信息
        login_sessions[account_id] = {
            'playwright': playwright,
            'browser': browser,
            'context': context,
            'page': page,
            'qrcode': qrcode_base64,
            'status': 'waiting',  # waiting, scanning, logged_in, failed
            'start_time': datetime.now(),
            'platform': platform
        }
        
        return {
            'success': True,
            'qrcode': qrcode_base64,
            'message': '二维码获取成功' if qrcode_base64 else '二维码获取失败，请查看页面截图'
        }
        
    except Exception as e:
        print(f"启动登录会话失败: {e}")
        return {
            'success': False,
            'qrcode': None,
            'message': f'启动登录会话失败: {str(e)}'
        }


async def check_login_status(account_id: int) -> Dict:
    """
    检查登录状态
    
    Args:
        account_id: 账号ID
    
    Returns:
        {
            'status': str,  # waiting, scanning, logged_in, failed
            'cookies': dict or None,
            'message': str
        }
    """
    if account_id not in login_sessions:
        return {
            'status': 'failed',
            'cookies': None,
            'message': '登录会话不存在，请重新启动登录'
        }
    
    session = login_sessions[account_id]
    page = session.get('page')
    context = session.get('context')
    
    if not page or not context:
        return {
            'status': 'failed',
            'cookies': None,
            'message': '登录会话无效，请重新启动登录'
        }
    
    try:
        # 首先尝试获取cookies并检查是否已登录
        try:
            storage_state = await context.storage_state()
            cookies = storage_state.get('cookies', [])
            
            # 检查是否有抖音的关键cookie
            if cookies:
                cookie_names = [c.get('name', '') for c in cookies]
                key_cookies = ['sessionid', 'passport_auth', 'sid_guard', 'passport_csrf_token', 'sid_tt']
                has_key_cookie = any(name in cookie_names for name in key_cookies)
                
                if has_key_cookie:
                    # 检查当前URL，确认不在登录页面
                    try:
                        current_url = page.url
                        # 如果URL不包含login或passport，且包含creator.douyin.com，说明已登录
                        if 'creator.douyin.com' in current_url and 'login' not in current_url.lower() and 'passport' not in current_url.lower():
                            session['status'] = 'logged_in'
                            session['cookies'] = storage_state
                            
                            return {
                                'status': 'logged_in',
                                'cookies': storage_state,
                                'message': '登录成功'
                            }
                    except Exception as e:
                        print(f"检查URL失败: {e}")
                        # 即使URL检查失败，如果有关键cookie，也认为已登录
                        session['status'] = 'logged_in'
                        session['cookies'] = storage_state
                        
                        return {
                            'status': 'logged_in',
                            'cookies': storage_state,
                            'message': '登录成功（通过cookies检测）'
                        }
        except Exception as e:
            print(f"获取cookies失败: {e}")
            # 继续检查页面状态
        
        # 确保页面已经加载
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=3000)
        except:
            pass  # 如果超时，继续执行
        
        # 检查当前URL
        try:
            current_url = page.url
            
            # 如果URL包含上传页面，说明已登录
            if 'creator.douyin.com/creator-micro/content/upload' in current_url:
                # 已登录，获取cookies
                try:
                    storage_state = await context.storage_state()
                    session['status'] = 'logged_in'
                    session['cookies'] = storage_state
                    
                    return {
                        'status': 'logged_in',
                        'cookies': storage_state,
                        'message': '登录成功'
                    }
                except Exception as e:
                    print(f"获取cookies失败: {e}")
            
            # 如果URL不包含login或passport，且包含creator.douyin.com，可能已登录
            if 'creator.douyin.com' in current_url and 'login' not in current_url.lower() and 'passport' not in current_url.lower():
                # 尝试获取cookies验证
                try:
                    storage_state = await context.storage_state()
                    cookies = storage_state.get('cookies', [])
                    if cookies:
                        cookie_names = [c.get('name', '') for c in cookies]
                        key_cookies = ['sessionid', 'passport_auth', 'sid_guard']
                        if any(name in cookie_names for name in key_cookies):
                            session['status'] = 'logged_in'
                            session['cookies'] = storage_state
                            
                            return {
                                'status': 'logged_in',
                                'cookies': storage_state,
                                'message': '登录成功'
                            }
                except Exception as e:
                    print(f"验证cookies失败: {e}")
        except Exception as e:
            print(f"检查URL失败: {e}")
        
        # 安全地检查页面是否有登录元素
        login_text_count = 0
        try:
            phone_login_locator = page.get_by_text('手机号登录')
            if phone_login_locator:
                login_text_count += await phone_login_locator.count()
        except Exception as e:
            print(f"检查'手机号登录'文本失败: {e}")
        
        try:
            qr_login_locator = page.get_by_text('扫码登录')
            if qr_login_locator:
                login_text_count += await qr_login_locator.count()
        except Exception as e:
            print(f"检查'扫码登录'文本失败: {e}")
        
        if login_text_count > 0:
            # 还在登录页面
            # 检查二维码是否过期
            try:
                expired_locator = page.get_by_text('二维码已过期')
                if expired_locator:
                    expired_count = await expired_locator.count()
                    if expired_count > 0:
                        session['status'] = 'failed'
                        return {
                            'status': 'failed',
                            'cookies': None,
                            'message': '二维码已过期，请重新获取'
                        }
            except Exception as e:
                print(f"检查二维码过期状态失败: {e}")
            
            # 检查是否正在扫描
            try:
                scanning_count = 0
                scanning_locator = page.get_by_text('扫描中')
                if scanning_locator:
                    scanning_count += await scanning_locator.count()
                
                confirm_locator = page.get_by_text('请确认')
                if confirm_locator:
                    scanning_count += await confirm_locator.count()
                
                if scanning_count > 0:
                    session['status'] = 'scanning'
                    return {
                        'status': 'scanning',
                        'cookies': None,
                        'message': '等待用户确认登录'
                    }
            except Exception as e:
                print(f"检查扫描状态失败: {e}")
            
            return {
                'status': 'waiting',
                'cookies': None,
                'message': '等待扫码登录'
            }
        else:
            # 没有登录元素，可能已登录，再次尝试获取cookies
            try:
                storage_state = await context.storage_state()
                cookies = storage_state.get('cookies', [])
                if cookies:
                    cookie_names = [c.get('name', '') for c in cookies]
                    key_cookies = ['sessionid', 'passport_auth', 'sid_guard', 'passport_csrf_token', 'sid_tt']
                    if any(name in cookie_names for name in key_cookies):
                        session['status'] = 'logged_in'
                        session['cookies'] = storage_state
                        
                        return {
                            'status': 'logged_in',
                            'cookies': storage_state,
                            'message': '登录成功'
                        }
            except Exception as e:
                print(f"获取cookies失败: {e}")
            
            return {
                'status': 'waiting',
                'cookies': None,
                'message': '等待登录完成'
            }
            
    except Exception as e:
        print(f"检查登录状态失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'failed',
            'cookies': None,
            'message': f'检查登录状态失败: {str(e)}'
        }


async def get_cookies_from_session(account_id: int) -> Optional[Dict]:
    """
    从登录会话获取cookies
    
    Args:
        account_id: 账号ID
    
    Returns:
        cookies字典（Playwright storage_state格式）或None
    """
    if account_id not in login_sessions:
        return None
    
    session = login_sessions[account_id]
    
    try:
        context = session['context']
        storage_state = await context.storage_state()
        return storage_state
    except Exception as e:
        print(f"获取cookies失败: {e}")
        return None


async def cleanup_login_session(account_id: int):
    """
    清理登录会话
    
    Args:
        account_id: 账号ID
    """
    if account_id not in login_sessions:
        return
    
    session = login_sessions[account_id]
    
    try:
        if 'page' in session and session['page']:
            await session['page'].close()
        if 'context' in session and session['context']:
            await session['context'].close()
        if 'browser' in session and session['browser']:
            await session['browser'].close()
        if 'playwright' in session and session['playwright']:
            await session['playwright'].stop()
    except Exception as e:
        print(f"清理登录会话失败: {e}")
    
    if account_id in login_sessions:
        del login_sessions[account_id]


# 同步包装函数，用于在Flask中使用
def start_login_session_sync(account_id: int, platform: str = 'douyin') -> Dict:
    """同步包装函数 - 使用全局事件循环"""
    try:
        loop = get_or_create_loop()
        if loop is None or loop.is_closed():
            # 如果循环不可用，使用 asyncio.run
            return asyncio.run(start_login_session(account_id, platform))
        
        future = asyncio.run_coroutine_threadsafe(
            start_login_session(account_id, platform),
            loop
        )
        result = future.result(timeout=120)  # 2分钟超时
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'qrcode': None,
            'message': f'启动登录会话失败: {str(e)}'
        }


def check_login_status_sync(account_id: int) -> Dict:
    """同步包装函数 - 使用全局事件循环"""
    try:
        loop = get_or_create_loop()
        if loop is None or loop.is_closed():
            # 如果循环不可用，使用 asyncio.run
            return asyncio.run(check_login_status(account_id))
        
        future = asyncio.run_coroutine_threadsafe(
            check_login_status(account_id),
            loop
        )
        result = future.result(timeout=10)  # 10秒超时
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'status': 'failed',
            'cookies': None,
            'message': f'检查登录状态失败: {str(e)}'
        }


def get_cookies_from_session_sync(account_id: int) -> Optional[Dict]:
    """同步包装函数 - 使用全局事件循环"""
    try:
        loop = get_or_create_loop()
        if loop is None or loop.is_closed():
            # 如果循环不可用，使用 asyncio.run
            return asyncio.run(get_cookies_from_session(account_id))
        
        future = asyncio.run_coroutine_threadsafe(
            get_cookies_from_session(account_id),
            loop
        )
        result = future.result(timeout=10)  # 10秒超时
        return result
    except Exception as e:
        print(f"获取cookies失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def cleanup_login_session_sync(account_id: int):
    """同步包装函数 - 使用全局事件循环"""
    try:
        loop = get_or_create_loop()
        if loop is None or loop.is_closed():
            # 如果循环不可用，使用 asyncio.run
            asyncio.run(cleanup_login_session(account_id))
            return
        
        future = asyncio.run_coroutine_threadsafe(
            cleanup_login_session(account_id),
            loop
        )
        future.result(timeout=10)  # 10秒超时
    except Exception as e:
        print(f"清理登录会话失败: {e}")
        import traceback
        traceback.print_exc()

